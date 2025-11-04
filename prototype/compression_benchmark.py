"""
Compression pipeline and benchmarking for API payloads.
"""
import json
import gzip
import time
import zstandard as zstd
import numpy as np
from typing import Any, Callable, List, Dict, Optional, Sequence
from data_generator import DataGenerator
import api_schemas_pb2 as schemas  # type: ignore


class CompressionPipeline:
    def __init__(self) -> None:
        self.zstd_dict: Optional[zstd.ZstdCompressionDict] = None
        self.zstd_compressor: Optional[zstd.ZstdCompressor] = None
        self.zstd_decompressor: Optional[zstd.ZstdDecompressor] = None

    def json_to_proto_order(self, data: Dict[str, Any]) -> bytes:
        """Convert JSON order to protobuf binary."""
        order = schemas.Order()  # type: ignore[attr-defined]
        order.order_id = data["order_id"]
        order.user_id = data["user_id"]
        order.timestamp = data["timestamp"]
        order.payment_method = data["payment_method"]
        order.total_amount = data["total_amount"]

        # Shipping address
        addr = data["shipping_address"]
        order.shipping_address.street = addr["street"]
        order.shipping_address.city = addr["city"]
        order.shipping_address.postal_code = addr["postal_code"]
        order.shipping_address.country = addr["country"]

        # Items
        for item_data in data["items"]:
            item = order.items.add()
            item.product_id = item_data["product_id"]
            item.quantity = item_data["quantity"]
            item.price = item_data["price"]

        return order.SerializeToString()

    def json_to_proto_product_view(self, data: Dict[str, Any]) -> bytes:
        """Convert JSON product view to protobuf binary."""
        view = schemas.ProductView()  # type: ignore[attr-defined]
        view.user_id = data["user_id"]
        view.product_id = data["product_id"]
        view.timestamp = data["timestamp"]
        view.referrer = data["referrer"]
        view.device_type = data["device_type"]
        return view.SerializeToString()

    def json_to_proto_search(self, data: Dict[str, Any]) -> bytes:
        """Convert JSON search request to protobuf binary."""
        search = schemas.SearchRequest()  # type: ignore[attr-defined]
        search.user_id = data["user_id"]
        search.query = data["query"]
        search.timestamp = data["timestamp"]
        search.page = data["page"]
        search.limit = data["limit"]
        search.filters.extend(data["filters"])
        return search.SerializeToString()

    def train_zstd_dictionary(self, samples: Sequence[bytes], dict_size: int = 100 * 1024) -> zstd.ZstdCompressionDict:
        """Train a zstd dictionary on sample data."""
        print(f"Training zstd dictionary with {len(samples)} samples...")
        dict_data = zstd.train_dictionary(dict_size, samples)  # type: ignore[arg-type]
        self.zstd_dict = dict_data
        self.zstd_compressor = zstd.ZstdCompressor(dict_data=dict_data)
        self.zstd_decompressor = zstd.ZstdDecompressor(dict_data=dict_data)
        print(f"Dictionary trained: {len(dict_data)} bytes")
        return dict_data

    def compress_json_gzip(self, data: Dict[str, Any]) -> bytes:
        """Compress JSON with gzip."""
        json_bytes = json.dumps(data).encode('utf-8')
        return gzip.compress(json_bytes, compresslevel=6)

    def compress_proto_zstd(self, proto_bytes: bytes) -> bytes:
        """Compress protobuf with zstd (using trained dictionary)."""
        if self.zstd_compressor is None:
            # Fallback to no dictionary
            return zstd.compress(proto_bytes)
        return self.zstd_compressor.compress(proto_bytes)

    def decompress_json_gzip(self, compressed: bytes) -> Dict[str, Any]:
        """Decompress gzip and parse JSON."""
        json_bytes = gzip.decompress(compressed)
        return json.loads(json_bytes)

    def decompress_proto_zstd(self, compressed: bytes, data_type: str) -> bytes:
        """Decompress zstd protobuf."""
        if self.zstd_decompressor is None:
            return zstd.decompress(compressed)
        return self.zstd_decompressor.decompress(compressed)


class Benchmarker:
    def __init__(self, pipeline: CompressionPipeline) -> None:
        self.pipeline = pipeline
        self.generator = DataGenerator()

    def measure_latency(self, func: Callable[..., Any], *args: Any, iterations: int = 100) -> List[float]:
        """Measure latency over multiple iterations."""
        latencies = []
        for _ in range(iterations):
            start = time.perf_counter()
            func(*args)
            end = time.perf_counter()
            latencies.append((end - start) * 1000)  # Convert to ms
        return latencies

    def calculate_percentiles(self, latencies: List[float]) -> Dict[str, float]:
        """Calculate latency percentiles."""
        return {
            "p50": float(np.percentile(latencies, 50)),
            "p95": float(np.percentile(latencies, 95)),
            "p99": float(np.percentile(latencies, 99)),
            "mean": float(np.mean(latencies)),
            "min": float(np.min(latencies)),
            "max": float(np.max(latencies))
        }

    def benchmark_data_type(self, data_type: str, sample_count: int,
                           proto_converter: Callable[[Dict[str, Any]], bytes], latency_iterations: int = 1000) -> Dict[str, Any]:
        """Benchmark a specific data type."""
        print(f"\n{'='*60}")
        print(f"Benchmarking: {data_type.upper()}")
        print(f"{'='*60}")

        # Generate sample data
        print(f"Generating {sample_count:,} samples...")
        samples = self.generator.generate_batch(data_type, sample_count)

        # Convert first batch to proto for dictionary training
        training_size = min(10000, sample_count)
        print(f"Converting {training_size:,} samples to protobuf for dictionary training...")
        proto_samples = [proto_converter(s) for s in samples[:training_size]]

        # Train dictionary
        self.pipeline.train_zstd_dictionary(proto_samples)

        # Benchmark on subset for detailed metrics
        test_samples = samples[:latency_iterations]

        # Measure sizes
        raw_json_sizes = []
        gzip_sizes = []
        proto_zstd_sizes = []

        print(f"\nCompressing {len(test_samples):,} samples...")
        for sample in test_samples:
            # Raw JSON
            json_bytes = json.dumps(sample).encode('utf-8')
            raw_json_sizes.append(len(json_bytes))

            # Gzip
            gzip_compressed = self.pipeline.compress_json_gzip(sample)
            gzip_sizes.append(len(gzip_compressed))

            # Proto + zstd
            proto_bytes = proto_converter(sample)
            proto_compressed = self.pipeline.compress_proto_zstd(proto_bytes)
            proto_zstd_sizes.append(len(proto_compressed))

        # Latency benchmarks
        print("Measuring encode latency...")
        sample = test_samples[0]

        # JSON + gzip encode latency
        gzip_encode_latencies = self.measure_latency(
            self.pipeline.compress_json_gzip, sample, iterations=latency_iterations
        )

        # Proto + zstd encode latency
        def proto_zstd_encode(data: Dict[str, Any]) -> bytes:
            proto_bytes = proto_converter(data)
            return self.pipeline.compress_proto_zstd(proto_bytes)

        proto_encode_latencies = self.measure_latency(
            proto_zstd_encode, sample, iterations=latency_iterations
        )

        # Decode latency
        print("Measuring decode latency...")
        gzip_sample = self.pipeline.compress_json_gzip(sample)
        proto_sample = proto_zstd_encode(sample)

        gzip_decode_latencies = self.measure_latency(
            self.pipeline.decompress_json_gzip, gzip_sample, iterations=latency_iterations
        )

        proto_decode_latencies = self.measure_latency(
            self.pipeline.decompress_proto_zstd, proto_sample, data_type,
            iterations=latency_iterations
        )

        # Calculate metrics
        avg_raw_size = np.mean(raw_json_sizes)
        avg_gzip_size = np.mean(gzip_sizes)
        avg_proto_zstd_size = np.mean(proto_zstd_sizes)

        gzip_ratio = avg_raw_size / avg_gzip_size
        proto_ratio = avg_raw_size / avg_proto_zstd_size
        improvement = avg_gzip_size / avg_proto_zstd_size

        results = {
            "data_type": data_type,
            "sample_count": sample_count,
            "sizes": {
                "raw_json_avg": avg_raw_size,
                "gzip_avg": avg_gzip_size,
                "proto_zstd_avg": avg_proto_zstd_size
            },
            "compression_ratios": {
                "gzip": gzip_ratio,
                "proto_zstd": proto_ratio,
                "proto_vs_gzip": improvement
            },
            "latency_ms": {
                "gzip_encode": self.calculate_percentiles(gzip_encode_latencies),
                "gzip_decode": self.calculate_percentiles(gzip_decode_latencies),
                "proto_zstd_encode": self.calculate_percentiles(proto_encode_latencies),
                "proto_zstd_decode": self.calculate_percentiles(proto_decode_latencies)
            }
        }

        self.print_results(results)
        return results

    def print_results(self, results: Dict[str, Any]) -> None:
        """Print benchmark results in a readable format."""
        print(f"\n{'-'*60}")
        print("RESULTS")
        print(f"{'-'*60}")

        sizes = results["sizes"]
        print(f"\nAverage Payload Sizes:")
        print(f"  Raw JSON:      {sizes['raw_json_avg']:>8.1f} bytes")
        print(f"  Gzip:          {sizes['gzip_avg']:>8.1f} bytes")
        print(f"  Proto + zstd:  {sizes['proto_zstd_avg']:>8.1f} bytes")

        ratios = results["compression_ratios"]
        print(f"\nCompression Ratios:")
        print(f"  Gzip:          {ratios['gzip']:.2f}x")
        print(f"  Proto + zstd:  {ratios['proto_zstd']:.2f}x")
        print(f"  Improvement:   {ratios['proto_vs_gzip']:.2f}x better than gzip")

        latency = results["latency_ms"]
        print(f"\nEncode Latency (ms):")
        print(f"  Gzip:          p50={latency['gzip_encode']['p50']:.3f} | " +
              f"p95={latency['gzip_encode']['p95']:.3f} | " +
              f"p99={latency['gzip_encode']['p99']:.3f}")
        print(f"  Proto + zstd:  p50={latency['proto_zstd_encode']['p50']:.3f} | " +
              f"p95={latency['proto_zstd_encode']['p95']:.3f} | " +
              f"p99={latency['proto_zstd_encode']['p99']:.3f}")

        print(f"\nDecode Latency (ms):")
        print(f"  Gzip:          p50={latency['gzip_decode']['p50']:.3f} | " +
              f"p95={latency['gzip_decode']['p95']:.3f} | " +
              f"p99={latency['gzip_decode']['p99']:.3f}")
        print(f"  Proto + zstd:  p50={latency['proto_zstd_decode']['p50']:.3f} | " +
              f"p95={latency['proto_zstd_decode']['p95']:.3f} | " +
              f"p99={latency['proto_zstd_decode']['p99']:.3f}")


def main() -> None:
    print("="*60)
    print("API Payload Compression Benchmark")
    print("Protobuf + zstd (with trained dictionary) vs JSON + gzip")
    print("="*60)

    pipeline = CompressionPipeline()
    benchmarker = Benchmarker(pipeline)

    all_results = []

    # Benchmark Orders
    order_results = benchmarker.benchmark_data_type(
        "order",
        sample_count=1000000,  # 1M orders
        proto_converter=pipeline.json_to_proto_order,
        latency_iterations=1000
    )
    all_results.append(order_results)

    # Benchmark Product Views
    view_results = benchmarker.benchmark_data_type(
        "product_view",
        sample_count=10000000,  # 10M product views
        proto_converter=pipeline.json_to_proto_product_view,
        latency_iterations=1000
    )
    all_results.append(view_results)

    # Benchmark Search Requests
    search_results = benchmarker.benchmark_data_type(
        "search",
        sample_count=20000000,  # 20M search requests
        proto_converter=pipeline.json_to_proto_search,
        latency_iterations=1000
    )
    all_results.append(search_results)

    # Summary
    print(f"\n\n{'='*60}")
    print("SUMMARY")
    print(f"{'='*60}")

    for result in all_results:
        ratio = result["compression_ratios"]["proto_vs_gzip"]
        p99_encode = result["latency_ms"]["proto_zstd_encode"]["p99"]
        p99_decode = result["latency_ms"]["proto_zstd_decode"]["p99"]

        print(f"\n{result['data_type'].upper()}:")
        print(f"  Compression: {ratio:.2f}x better than gzip")
        print(f"  Latency (p99): encode={p99_encode:.3f}ms | decode={p99_decode:.3f}ms")

        # Check if we met the goals
        if ratio >= 2.0:
            print(f"  ✓ GOAL MET: >2x better compression than gzip")
        else:
            print(f"  ✗ Goal not met: {ratio:.2f}x < 2.0x target")

        if p99_encode < 1.0 and p99_decode < 1.0:
            print(f"  ✓ GOAL MET: Sub-millisecond latency")
        else:
            print(f"  ✗ Latency warning: Some operations > 1ms")


if __name__ == "__main__":
    main()
