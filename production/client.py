"""
Production client SDK with automatic compression.
"""
import requests
from typing import Any, Dict, Optional
import logging

from .middleware import CompressionMiddleware, CompressionConfig, CompressionError
from .metrics import MetricsBackend

logger = logging.getLogger(__name__)


class CompressedAPIClient:
    """
    HTTP client with automatic compression/decompression.

    Example:
        client = CompressedAPIClient(
            base_url="https://api.example.com",
            compression_config=CompressionConfig(
                dictionary_version="1.0.0",
                cdn_url="https://cdn.example.com/dicts"
            )
        )

        # Automatically compresses request
        response = client.post("/orders", data=order_data, data_type="order")
    """

    def __init__(
        self,
        base_url: str,
        compression_config: Optional[CompressionConfig] = None,
        session: Optional[requests.Session] = None,
        metrics_backend: MetricsBackend = MetricsBackend.NOOP,
        **metrics_config: Any
    ) -> None:
        self.base_url = base_url.rstrip('/')
        self.session = session or requests.Session()

        # Initialize compression
        self.config = compression_config or CompressionConfig()
        self.config.metrics_enabled = metrics_backend != MetricsBackend.NOOP

        # Import metrics here to avoid circular import
        from .metrics import get_metrics
        metrics = get_metrics(backend=metrics_backend, **metrics_config) if self.config.metrics_enabled else None

        self.middleware = CompressionMiddleware(
            config=self.config,
            metrics=metrics
        )

        logger.info(f"CompressedAPIClient initialized: base_url={base_url}")

    def post(
        self,
        endpoint: str,
        data: Dict[str, Any],
        data_type: str,
        timeout: int = 30,
        **kwargs: Any
    ) -> Dict[str, Any]:
        """
        POST request with automatic compression.

        Args:
            endpoint: API endpoint (e.g., "/orders")
            data: JSON-serializable data
            data_type: Type of data ('order', 'product_view', 'search')
            timeout: Request timeout in seconds
            **kwargs: Additional arguments to pass to requests.post

        Returns:
            Response data as dictionary

        Raises:
            CompressionError: On compression/decompression failure
            requests.HTTPError: On HTTP errors
        """
        url = f"{self.base_url}{endpoint}"

        try:
            # Compress request
            compressed_data, headers = self.middleware.compress_request(
                data=data,
                data_type=data_type,
                endpoint=endpoint
            )

            # Merge headers
            request_headers = kwargs.pop('headers', {})
            request_headers.update(headers)

            # Make request
            logger.debug(f"POST {url} (compressed: {len(compressed_data)} bytes)")
            response = self.session.post(
                url,
                data=compressed_data,
                headers=request_headers,
                timeout=timeout,
                **kwargs
            )
            response.raise_for_status()

            # Decompress response if compressed
            response_headers = dict(response.headers)
            if response.content:
                return self.middleware.decompress_response(
                    compressed_data=response.content,
                    headers=response_headers,
                    endpoint=endpoint
                )
            else:
                return {}

        except CompressionError:
            logger.error(f"Compression error for {endpoint}")
            raise
        except requests.HTTPError as e:
            logger.error(f"HTTP error for {endpoint}: {e}")
            raise

    def get(
        self,
        endpoint: str,
        timeout: int = 30,
        **kwargs: Any
    ) -> Dict[str, Any]:
        """
        GET request with automatic decompression.

        Args:
            endpoint: API endpoint
            timeout: Request timeout in seconds
            **kwargs: Additional arguments to pass to requests.get

        Returns:
            Response data as dictionary
        """
        url = f"{self.base_url}{endpoint}"

        # Add Accept-Encoding header
        headers = kwargs.pop('headers', {})
        headers.setdefault('Accept-Encoding', 'proto-zstd, gzip')

        logger.debug(f"GET {url}")
        response = self.session.get(
            url,
            headers=headers,
            timeout=timeout,
            **kwargs
        )
        response.raise_for_status()

        # Decompress response if compressed
        response_headers = dict(response.headers)
        if response.content:
            return self.middleware.decompress_response(
                compressed_data=response.content,
                headers=response_headers,
                endpoint=endpoint
            )
        else:
            return {}

    def close(self) -> None:
        """Close the HTTP session."""
        self.session.close()

    def __enter__(self) -> 'CompressedAPIClient':
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:  # type: ignore
        self.close()


# Example usage
if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)

    # Create client
    config = CompressionConfig(
        enabled=True,
        dictionary_version="1.0.0",
        cdn_url="https://cdn.example.com/dicts",
        fallback_to_gzip=True
    )

    with CompressedAPIClient(
        base_url="https://api.example.com",
        compression_config=config,
        metrics_backend=MetricsBackend.PROMETHEUS
    ) as client:
        # Create an order
        order_data = {
            "order_id": "ORD-12345",
            "user_id": 1001,
            "timestamp": 1704067200,
            "items": [
                {"product_id": 42, "quantity": 2, "price": 29.99}
            ],
            "shipping_address": {
                "street": "123 Main St",
                "city": "New York",
                "postal_code": "10001",
                "country": "USA"
            },
            "payment_method": "credit_card",
            "total_amount": 59.98
        }

        try:
            response = client.post(
                endpoint="/orders",
                data=order_data,
                data_type="order"
            )
            print(f"Order created: {response}")

        except Exception as e:
            print(f"Error: {e}")
