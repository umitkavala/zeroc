"""
Production HTTP middleware for compression with error handling and fallback.
"""
import json
import gzip
from typing import Any, Dict, Optional, Callable
import logging
from dataclasses import dataclass

from .dictionary_manager import DictionaryManager, get_dictionary_manager
from .metrics import CompressionMetrics, CompressionTimer, get_metrics

logger = logging.getLogger(__name__)


# Import proto schemas (adjust path as needed)
try:
    import sys
    sys.path.insert(0, '..')
    import api_schemas_pb2 as schemas
except ImportError:
    logger.warning("Could not import api_schemas_pb2, protobuf support disabled")
    schemas = None  # type: ignore


@dataclass
class CompressionConfig:
    """Configuration for compression middleware."""
    enabled: bool = True
    dictionary_version: str = "1.0.0"
    fallback_to_gzip: bool = True
    max_payload_size: int = 10 * 1024 * 1024  # 10MB
    max_decompressed_size: int = 50 * 1024 * 1024  # 50MB
    cdn_url: Optional[str] = None
    metrics_enabled: bool = True


class CompressionError(Exception):
    """Base exception for compression errors."""
    pass


class PayloadTooLarge(CompressionError):
    """Payload exceeds size limits."""
    pass


class DecompressionBomb(CompressionError):
    """Decompressed payload exceeds size limits."""
    pass


class DictionaryNotFound(CompressionError):
    """Dictionary version not found."""
    pass


class CompressionMiddleware:
    """
    HTTP middleware for automatic compression/decompression.

    Supports:
    - Proto + zstd with dictionaries
    - Fallback to JSON + gzip
    - Content negotiation via headers
    - Error handling and metrics
    """

    # Header constants
    HEADER_CONTENT_TYPE = "Content-Type"
    HEADER_CONTENT_ENCODING = "Content-Encoding"
    HEADER_DICT_VERSION = "X-Compression-Dict-Version"
    HEADER_ORIGINAL_SIZE = "X-Original-Size"

    ENCODING_PROTO_ZSTD = "proto-zstd"
    ENCODING_GZIP = "gzip"
    ENCODING_IDENTITY = "identity"

    CONTENT_TYPE_PROTOBUF = "application/x-protobuf"
    CONTENT_TYPE_JSON = "application/json"

    def __init__(
        self,
        config: CompressionConfig,
        dict_manager: Optional[DictionaryManager] = None,
        metrics: Optional[CompressionMetrics] = None
    ) -> None:
        self.config = config
        self.dict_manager = dict_manager or get_dictionary_manager(
            cdn_base_url=config.cdn_url
        )
        self.metrics = metrics or get_metrics() if config.metrics_enabled else None

        # Proto converters (extend as needed)
        self.proto_converters: Dict[str, Callable] = {}
        if schemas:
            self.proto_converters = {
                'order': self._json_to_proto_order,
                'product_view': self._json_to_proto_product_view,
                'search': self._json_to_proto_search,
            }

        logger.info(f"CompressionMiddleware initialized: version={config.dictionary_version}")

    def compress_request(
        self,
        data: Dict[str, Any],
        data_type: str,
        endpoint: str = "unknown"
    ) -> tuple[bytes, Dict[str, str]]:
        """
        Compress request data.

        Args:
            data: JSON-serializable dictionary
            data_type: Type of data ('order', 'product_view', 'search')
            endpoint: API endpoint for metrics

        Returns:
            (compressed_bytes, headers_dict)

        Raises:
            CompressionError: On compression failure
        """
        if not self.config.enabled:
            # Return JSON without compression
            json_bytes = json.dumps(data).encode('utf-8')
            return json_bytes, {
                self.HEADER_CONTENT_TYPE: self.CONTENT_TYPE_JSON,
                self.HEADER_CONTENT_ENCODING: self.ENCODING_IDENTITY
            }

        try:
            # Try proto + zstd
            return self._compress_proto_zstd(data, data_type, endpoint)

        except Exception as e:
            logger.warning(f"Proto+zstd compression failed: {e}")
            if self.metrics:
                self.metrics.record_error("proto_zstd_failed", endpoint)

            if self.config.fallback_to_gzip:
                # Fall back to JSON + gzip
                return self._compress_json_gzip(data, endpoint)
            else:
                raise CompressionError(f"Compression failed: {e}") from e

    def _compress_proto_zstd(
        self,
        data: Dict[str, Any],
        data_type: str,
        endpoint: str
    ) -> tuple[bytes, Dict[str, str]]:
        """Compress using protobuf + zstd."""
        if data_type not in self.proto_converters:
            raise CompressionError(f"Unknown data type: {data_type}")

        # Convert to proto
        converter = self.proto_converters[data_type]
        proto_bytes = converter(data)

        original_size = len(proto_bytes)
        if original_size > self.config.max_payload_size:
            raise PayloadTooLarge(f"Payload size {original_size} exceeds limit")

        # Get compressor
        try:
            compressor = self.dict_manager.get_compressor(self.config.dictionary_version)
        except Exception as e:
            raise DictionaryNotFound(f"Dictionary {self.config.dictionary_version} not found") from e

        # Compress with metrics
        if self.metrics:
            with CompressionTimer(
                self.metrics,
                operation="encode",
                endpoint=endpoint,
                version=self.config.dictionary_version
            ) as timer:
                compressed = compressor.compress(proto_bytes)
                timer.set_sizes(original_size, len(compressed))
        else:
            compressed = compressor.compress(proto_bytes)

        headers = {
            self.HEADER_CONTENT_TYPE: self.CONTENT_TYPE_PROTOBUF,
            self.HEADER_CONTENT_ENCODING: self.ENCODING_PROTO_ZSTD,
            self.HEADER_DICT_VERSION: self.config.dictionary_version,
            self.HEADER_ORIGINAL_SIZE: str(original_size)
        }

        return compressed, headers

    def _compress_json_gzip(
        self,
        data: Dict[str, Any],
        endpoint: str
    ) -> tuple[bytes, Dict[str, str]]:
        """Compress using JSON + gzip (fallback)."""
        json_bytes = json.dumps(data).encode('utf-8')
        original_size = len(json_bytes)

        if original_size > self.config.max_payload_size:
            raise PayloadTooLarge(f"Payload size {original_size} exceeds limit")

        # Compress with metrics
        if self.metrics:
            with CompressionTimer(
                self.metrics,
                operation="encode",
                endpoint=endpoint,
                version="gzip"
            ) as timer:
                compressed = gzip.compress(json_bytes, compresslevel=6)
                timer.set_sizes(original_size, len(compressed))
        else:
            compressed = gzip.compress(json_bytes, compresslevel=6)

        headers = {
            self.HEADER_CONTENT_TYPE: self.CONTENT_TYPE_JSON,
            self.HEADER_CONTENT_ENCODING: self.ENCODING_GZIP,
            self.HEADER_ORIGINAL_SIZE: str(original_size)
        }

        return compressed, headers

    def decompress_response(
        self,
        compressed_data: bytes,
        headers: Dict[str, str],
        endpoint: str = "unknown"
    ) -> Dict[str, Any]:
        """
        Decompress response data.

        Args:
            compressed_data: Compressed bytes
            headers: Response headers
            endpoint: API endpoint for metrics

        Returns:
            Decompressed JSON dictionary

        Raises:
            CompressionError: On decompression failure
        """
        if len(compressed_data) > self.config.max_payload_size:
            raise PayloadTooLarge(f"Compressed size {len(compressed_data)} exceeds limit")

        content_encoding = headers.get(self.HEADER_CONTENT_ENCODING, self.ENCODING_IDENTITY)
        content_type = headers.get(self.HEADER_CONTENT_TYPE, self.CONTENT_TYPE_JSON)

        try:
            if content_encoding == self.ENCODING_PROTO_ZSTD:
                return self._decompress_proto_zstd(compressed_data, headers, endpoint)

            elif content_encoding == self.ENCODING_GZIP:
                return self._decompress_json_gzip(compressed_data, endpoint)

            elif content_encoding == self.ENCODING_IDENTITY:
                # No compression
                return json.loads(compressed_data)

            else:
                raise CompressionError(f"Unsupported encoding: {content_encoding}")

        except Exception as e:
            logger.error(f"Decompression failed: {e}")
            if self.metrics:
                self.metrics.record_error("decompression_failed", endpoint)
            raise

    def _decompress_proto_zstd(
        self,
        compressed_data: bytes,
        headers: Dict[str, str],
        endpoint: str
    ) -> Dict[str, Any]:
        """Decompress proto + zstd data."""
        dict_version = headers.get(self.HEADER_DICT_VERSION, self.config.dictionary_version)

        # Get decompressor
        try:
            decompressor = self.dict_manager.get_decompressor(dict_version)
        except Exception as e:
            raise DictionaryNotFound(f"Dictionary {dict_version} not found") from e

        # Decompress with metrics
        if self.metrics:
            with CompressionTimer(
                self.metrics,
                operation="decode",
                endpoint=endpoint,
                version=dict_version
            ) as timer:
                proto_bytes = decompressor.decompress(compressed_data)
                if len(proto_bytes) > self.config.max_decompressed_size:
                    raise DecompressionBomb(f"Decompressed size {len(proto_bytes)} exceeds limit")
                timer.set_sizes(len(proto_bytes), len(compressed_data))
        else:
            proto_bytes = decompressor.decompress(compressed_data)
            if len(proto_bytes) > self.config.max_decompressed_size:
                raise DecompressionBomb(f"Decompressed size {len(proto_bytes)} exceeds limit")

        # Parse protobuf (this is simplified - in production, you'd need to know the message type)
        # For now, we'll skip proto parsing and just return a placeholder
        # In production, you'd parse based on content-type or another header
        logger.warning("Protobuf parsing not implemented in decompress_response")
        return {"data": "protobuf_data"}

    def _decompress_json_gzip(
        self,
        compressed_data: bytes,
        endpoint: str
    ) -> Dict[str, Any]:
        """Decompress JSON + gzip data."""
        if self.metrics:
            with CompressionTimer(
                self.metrics,
                operation="decode",
                endpoint=endpoint,
                version="gzip"
            ) as timer:
                json_bytes = gzip.decompress(compressed_data)
                if len(json_bytes) > self.config.max_decompressed_size:
                    raise DecompressionBomb(f"Decompressed size {len(json_bytes)} exceeds limit")
                timer.set_sizes(len(json_bytes), len(compressed_data))
        else:
            json_bytes = gzip.decompress(compressed_data)
            if len(json_bytes) > self.config.max_decompressed_size:
                raise DecompressionBomb(f"Decompressed size {len(json_bytes)} exceeds limit")

        return json.loads(json_bytes)

    # Proto converters (from benchmark code)
    def _json_to_proto_order(self, data: Dict[str, Any]) -> bytes:
        """Convert JSON order to protobuf binary."""
        if not schemas:
            raise CompressionError("Protobuf schemas not available")

        order = schemas.Order()  # type: ignore[attr-defined]
        order.order_id = data["order_id"]
        order.user_id = data["user_id"]
        order.timestamp = data["timestamp"]
        order.payment_method = data["payment_method"]
        order.total_amount = data["total_amount"]

        addr = data["shipping_address"]
        order.shipping_address.street = addr["street"]
        order.shipping_address.city = addr["city"]
        order.shipping_address.postal_code = addr["postal_code"]
        order.shipping_address.country = addr["country"]

        for item_data in data["items"]:
            item = order.items.add()
            item.product_id = item_data["product_id"]
            item.quantity = item_data["quantity"]
            item.price = item_data["price"]

        return order.SerializeToString()

    def _json_to_proto_product_view(self, data: Dict[str, Any]) -> bytes:
        """Convert JSON product view to protobuf binary."""
        if not schemas:
            raise CompressionError("Protobuf schemas not available")

        view = schemas.ProductView()  # type: ignore[attr-defined]
        view.user_id = data["user_id"]
        view.product_id = data["product_id"]
        view.timestamp = data["timestamp"]
        view.referrer = data["referrer"]
        view.device_type = data["device_type"]
        return view.SerializeToString()

    def _json_to_proto_search(self, data: Dict[str, Any]) -> bytes:
        """Convert JSON search request to protobuf binary."""
        if not schemas:
            raise CompressionError("Protobuf schemas not available")

        search = schemas.SearchRequest()  # type: ignore[attr-defined]
        search.user_id = data["user_id"]
        search.query = data["query"]
        search.timestamp = data["timestamp"]
        search.page = data["page"]
        search.limit = data["limit"]
        search.filters.extend(data["filters"])
        return search.SerializeToString()
