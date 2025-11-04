"""
Metrics and monitoring for compression operations.
Supports Prometheus, StatsD, and CloudWatch.
"""
import time
from typing import Optional, Dict, Any
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class MetricsBackend(Enum):
    """Supported metrics backends."""
    PROMETHEUS = "prometheus"
    STATSD = "statsd"
    CLOUDWATCH = "cloudwatch"
    NOOP = "noop"  # For testing


class CompressionMetrics:
    """
    Tracks compression metrics with support for multiple backends.

    Metrics tracked:
    - compression_ratio: bytes_saved / bytes_original
    - compression_latency: time to compress (seconds)
    - decompression_latency: time to decompress (seconds)
    - compression_errors: total errors by type
    - bandwidth_saved: total bytes saved
    - dictionary_cache_hits/misses
    """

    def __init__(self, backend: MetricsBackend = MetricsBackend.NOOP, **backend_config: Any) -> None:
        self.backend = backend
        self.backend_config = backend_config
        self._client: Optional[Any] = None

        if backend == MetricsBackend.PROMETHEUS:
            self._init_prometheus()
        elif backend == MetricsBackend.STATSD:
            self._init_statsd(**backend_config)
        elif backend == MetricsBackend.CLOUDWATCH:
            self._init_cloudwatch(**backend_config)

        logger.info(f"CompressionMetrics initialized with backend: {backend.value}")

    def _init_prometheus(self) -> None:
        """Initialize Prometheus metrics."""
        try:
            from prometheus_client import Counter, Histogram, Gauge

            self.compression_latency = Histogram(
                'compression_latency_seconds',
                'Time spent compressing data',
                ['operation', 'endpoint', 'version']
            )

            self.compression_ratio = Histogram(
                'compression_ratio',
                'Compression ratio achieved',
                ['endpoint', 'version'],
                buckets=(1.0, 2.0, 3.0, 4.0, 5.0, 7.5, 10.0)
            )

            self.compression_errors = Counter(
                'compression_errors_total',
                'Total compression errors',
                ['error_type', 'endpoint']
            )

            self.bandwidth_saved = Counter(
                'bandwidth_saved_bytes_total',
                'Total bandwidth saved by compression',
                ['endpoint', 'version']
            )

            self.dictionary_cache_hits = Counter(
                'dictionary_cache_hits_total',
                'Dictionary cache hits',
                ['version']
            )

            self.dictionary_cache_misses = Counter(
                'dictionary_cache_misses_total',
                'Dictionary cache misses',
                ['version']
            )

            self.payload_size = Histogram(
                'payload_size_bytes',
                'Payload sizes',
                ['encoding', 'endpoint'],
                buckets=(100, 500, 1000, 5000, 10000, 50000, 100000, 500000)
            )

            logger.info("Prometheus metrics initialized")

        except ImportError:
            logger.warning("prometheus_client not installed, metrics disabled")
            self.backend = MetricsBackend.NOOP

    def _init_statsd(self, host: str = 'localhost', port: int = 8125, prefix: str = 'compression') -> None:
        """Initialize StatsD client."""
        try:
            from statsd import StatsClient
            self._client = StatsClient(host=host, port=port, prefix=prefix)
            logger.info(f"StatsD client initialized: {host}:{port}")
        except ImportError:
            logger.warning("statsd not installed, metrics disabled")
            self.backend = MetricsBackend.NOOP

    def _init_cloudwatch(self, namespace: str = 'Compression', **kwargs: Any) -> None:
        """Initialize CloudWatch metrics."""
        try:
            import boto3
            self._client = boto3.client('cloudwatch', **kwargs)
            self.namespace = namespace
            logger.info(f"CloudWatch metrics initialized: namespace={namespace}")
        except ImportError:
            logger.warning("boto3 not installed, metrics disabled")
            self.backend = MetricsBackend.NOOP

    def record_compression(
        self,
        original_size: int,
        compressed_size: int,
        latency_seconds: float,
        endpoint: str = "unknown",
        version: str = "unknown",
        operation: str = "encode"
    ) -> None:
        """Record a compression operation."""
        ratio = original_size / compressed_size if compressed_size > 0 else 0
        bytes_saved = original_size - compressed_size

        if self.backend == MetricsBackend.PROMETHEUS:
            self.compression_latency.labels(
                operation=operation,
                endpoint=endpoint,
                version=version
            ).observe(latency_seconds)

            self.compression_ratio.labels(
                endpoint=endpoint,
                version=version
            ).observe(ratio)

            self.bandwidth_saved.labels(
                endpoint=endpoint,
                version=version
            ).inc(bytes_saved)

            self.payload_size.labels(
                encoding="proto-zstd",
                endpoint=endpoint
            ).observe(compressed_size)

        elif self.backend == MetricsBackend.STATSD and self._client:
            self._client.timing(f'{endpoint}.{operation}.latency', latency_seconds * 1000)
            self._client.gauge(f'{endpoint}.compression_ratio', ratio)
            self._client.incr(f'{endpoint}.bandwidth_saved', bytes_saved)

        elif self.backend == MetricsBackend.CLOUDWATCH and self._client:
            self._client.put_metric_data(
                Namespace=self.namespace,
                MetricData=[
                    {
                        'MetricName': 'CompressionLatency',
                        'Value': latency_seconds,
                        'Unit': 'Seconds',
                        'Dimensions': [
                            {'Name': 'Endpoint', 'Value': endpoint},
                            {'Name': 'Operation', 'Value': operation},
                            {'Name': 'Version', 'Value': version}
                        ]
                    },
                    {
                        'MetricName': 'CompressionRatio',
                        'Value': ratio,
                        'Unit': 'None',
                        'Dimensions': [
                            {'Name': 'Endpoint', 'Value': endpoint},
                            {'Name': 'Version', 'Value': version}
                        ]
                    },
                    {
                        'MetricName': 'BandwidthSaved',
                        'Value': bytes_saved,
                        'Unit': 'Bytes',
                        'Dimensions': [
                            {'Name': 'Endpoint', 'Value': endpoint}
                        ]
                    }
                ]
            )

    def record_error(self, error_type: str, endpoint: str = "unknown") -> None:
        """Record a compression error."""
        if self.backend == MetricsBackend.PROMETHEUS:
            self.compression_errors.labels(
                error_type=error_type,
                endpoint=endpoint
            ).inc()

        elif self.backend == MetricsBackend.STATSD and self._client:
            self._client.incr(f'{endpoint}.errors.{error_type}')

        elif self.backend == MetricsBackend.CLOUDWATCH and self._client:
            self._client.put_metric_data(
                Namespace=self.namespace,
                MetricData=[
                    {
                        'MetricName': 'CompressionErrors',
                        'Value': 1,
                        'Unit': 'Count',
                        'Dimensions': [
                            {'Name': 'ErrorType', 'Value': error_type},
                            {'Name': 'Endpoint', 'Value': endpoint}
                        ]
                    }
                ]
            )

    def record_cache_hit(self, version: str) -> None:
        """Record a dictionary cache hit."""
        if self.backend == MetricsBackend.PROMETHEUS:
            self.dictionary_cache_hits.labels(version=version).inc()

        elif self.backend == MetricsBackend.STATSD and self._client:
            self._client.incr(f'dictionary.cache.hits')

    def record_cache_miss(self, version: str) -> None:
        """Record a dictionary cache miss."""
        if self.backend == MetricsBackend.PROMETHEUS:
            self.dictionary_cache_misses.labels(version=version).inc()

        elif self.backend == MetricsBackend.STATSD and self._client:
            self._client.incr(f'dictionary.cache.misses')


class CompressionTimer:
    """Context manager for timing compression operations."""

    def __init__(
        self,
        metrics: CompressionMetrics,
        operation: str,
        endpoint: str = "unknown",
        version: str = "unknown"
    ) -> None:
        self.metrics = metrics
        self.operation = operation
        self.endpoint = endpoint
        self.version = version
        self.start_time: float = 0
        self.original_size: int = 0
        self.compressed_size: int = 0

    def __enter__(self) -> 'CompressionTimer':
        self.start_time = time.perf_counter()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:  # type: ignore
        if exc_type is None and self.original_size > 0:
            latency = time.perf_counter() - self.start_time
            self.metrics.record_compression(
                original_size=self.original_size,
                compressed_size=self.compressed_size,
                latency_seconds=latency,
                endpoint=self.endpoint,
                version=self.version,
                operation=self.operation
            )

    def set_sizes(self, original_size: int, compressed_size: int) -> None:
        """Set payload sizes for metrics."""
        self.original_size = original_size
        self.compressed_size = compressed_size


# Singleton instance
_default_metrics: Optional[CompressionMetrics] = None


def get_metrics(**kwargs: Any) -> CompressionMetrics:
    """Get the default metrics instance."""
    global _default_metrics
    if _default_metrics is None:
        _default_metrics = CompressionMetrics(**kwargs)
    return _default_metrics
