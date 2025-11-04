#!/usr/bin/env python3
"""
Comprehensive compression benchmarks comparing:
1. Raw JSON (baseline)
2. JSON + gzip
3. Protobuf (binary)
4. Protobuf + gzip
5. Zeroc (protobuf + zstd + trained dictionary)

Measures payload sizes and latency (p50, p95, p99) for each approach.
"""
import sys
import json
import gzip
import time
import statistics
from pathlib import Path
from typing import List, Dict, Any, Tuple

# Add paths for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "prototype"))
sys.path.insert(0, str(Path(__file__).parent.parent / "implementations" / "python"))

import zstandard as zstd
import api_schemas_pb2 as schemas
from data_generator import DataGenerator
from zeroc import DictionaryLoader, encode_frame, decode_frame, decompress_payload


class CompressionBenchmark:
    """Comprehensive compression benchmarking."""

    def __init__(self, sample_count: int = 10000, latency_iterations: int = 1000):
        self.sample_count = sample_count
        self.latency_iterations = latency_iterations
        self.generator = DataGenerator(seed=42)
        self.dict_loader = DictionaryLoader()

    def json_to_proto_order(self, data: Dict[str, Any]) -> bytes:
        """Convert JSON order to protobuf binary."""
        order = schemas.Order()
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

    def json_to_proto_product_view(self, data: Dict[str, Any]) -> bytes:
        """Convert JSON product view to protobuf binary."""
        view = schemas.ProductView()
        view.user_id = data["user_id"]
        view.product_id = data["product_id"]
        view.timestamp = data["timestamp"]
        view.referrer = data["referrer"]
        view.device_type = data["device_type"]
        return view.SerializeToString()

    def json_to_proto_search(self, data: Dict[str, Any]) -> bytes:
        """Convert JSON search request to protobuf binary."""
        search = schemas.SearchRequest()
        search.user_id = data["user_id"]
        search.query = data["query"]
        search.timestamp = data["timestamp"]
        search.page = data["page"]
        search.limit = data["limit"]
        search.filters.extend(data["filters"])
        return search.SerializeToString()

    def measure_latency(self, func, iterations: int) -> Tuple[float, float, float]:
        """Measure p50, p95, p99 latency in milliseconds."""
        times = []
        for _ in range(iterations):
            start = time.perf_counter()
            func()
            end = time.perf_counter()
            times.append((end - start) * 1000)  # Convert to ms

        times.sort()
        p50 = statistics.median(times)
        p95 = times[int(len(times) * 0.95)]
        p99 = times[int(len(times) * 0.99)]
        return p50, p95, p99

    def benchmark_approach(
        self,
        name: str,
        encode_func,
        decode_func,
        sample_data,
        sample_proto=None
    ) -> Dict[str, Any]:
        """Benchmark a specific compression approach."""
        print(f"\n  Benchmarking {name}...")

        # Measure payload sizes
        encoded_samples = [encode_func(s) for s in sample_data[:1000]]
        avg_size = sum(len(e) for e in encoded_samples) / len(encoded_samples)

        # Measure encode latency
        test_sample = sample_data[0]
        p50_encode, p95_encode, p99_encode = self.measure_latency(
            lambda: encode_func(test_sample),
            self.latency_iterations
        )

        # Measure decode latency
        encoded_test = encode_func(test_sample)
        p50_decode, p95_decode, p99_decode = self.measure_latency(
            lambda: decode_func(encoded_test),
            self.latency_iterations
        )

        return {
            "name": name,
            "avg_size_bytes": avg_size,
            "encode_p50_ms": p50_encode,
            "encode_p95_ms": p95_encode,
            "encode_p99_ms": p99_encode,
            "decode_p50_ms": p50_decode,
            "decode_p95_ms": p95_decode,
            "decode_p99_ms": p99_decode,
        }

    def benchmark_data_type(
        self,
        data_type: str,
        proto_converter,
        dict_path: str
    ) -> List[Dict[str, Any]]:
        """Benchmark all approaches for a data type."""
        print(f"\n{'='*60}")
        print(f"Benchmarking: {data_type.upper()}")
        print(f"{'='*60}")
        print(f"Generating {self.sample_count:,} samples...")

        # Generate samples
        json_samples = self.generator.generate_batch(data_type, self.sample_count)
        proto_samples = [proto_converter(s) for s in json_samples]

        # Load dictionary for Zeroc
        dict_metadata, dict_obj = self.dict_loader.load(dict_path)
        compressor = self.dict_loader.get_compressor(dict_path, level=3)
        decompressor = self.dict_loader.get_decompressor(dict_path)

        results = []

        # 1. Raw JSON (baseline)
        results.append(self.benchmark_approach(
            "Raw JSON",
            lambda s: json.dumps(s).encode('utf-8'),
            lambda e: json.loads(e.decode('utf-8')),
            json_samples
        ))

        # 2. JSON + gzip
        results.append(self.benchmark_approach(
            "JSON + gzip",
            lambda s: gzip.compress(json.dumps(s).encode('utf-8'), compresslevel=6),
            lambda e: json.loads(gzip.decompress(e).decode('utf-8')),
            json_samples
        ))

        # 3. Protobuf (binary)
        results.append(self.benchmark_approach(
            "Protobuf",
            lambda s: proto_converter(s),
            lambda e: e,  # Just return as-is for size measurement
            json_samples
        ))

        # 4. Protobuf + gzip
        results.append(self.benchmark_approach(
            "Protobuf + gzip",
            lambda s: gzip.compress(proto_converter(s), compresslevel=6),
            lambda e: gzip.decompress(e),
            json_samples
        ))

        # 5. Zeroc (protobuf + zstd + dictionary)
        def encode_zeroc(s):
            proto = proto_converter(s)
            return encode_frame(
                proto,
                dictionary_id=dict_metadata['dictionary_id'],
                compress=True,
                checksum=False,
                compressor=compressor
            )

        def decode_zeroc(e):
            compressed, metadata = decode_frame(e)
            return decompress_payload(
                compressed,
                metadata['dictionary_id'],
                decompressor
            )

        results.append(self.benchmark_approach(
            "Zeroc (proto + zstd + dict)",
            encode_zeroc,
            decode_zeroc,
            json_samples
        ))

        return results

    def print_results(self, data_type: str, results: List[Dict[str, Any]]):
        """Print formatted benchmark results."""
        baseline_size = results[0]["avg_size_bytes"]

        print(f"\n{'='*80}")
        print(f"RESULTS: {data_type.upper()}")
        print(f"{'='*80}")
        print()

        # Payload sizes comparison
        print("PAYLOAD SIZES:")
        print(f"{'Approach':<30} {'Avg Size':>12} {'vs Baseline':>12} {'Reduction':>12}")
        print("-" * 80)

        for r in results:
            size = r["avg_size_bytes"]
            ratio = baseline_size / size if size > 0 else 0
            reduction = (1 - size / baseline_size) * 100 if baseline_size > 0 else 0
            print(f"{r['name']:<30} {size:>10.1f}B  {ratio:>10.2f}x  {reduction:>10.1f}%")

        print()

        # Encode latency comparison
        print("ENCODE LATENCY (milliseconds):")
        print(f"{'Approach':<30} {'p50':>10} {'p95':>10} {'p99':>10}")
        print("-" * 80)

        for r in results:
            print(f"{r['name']:<30} {r['encode_p50_ms']:>9.3f}  {r['encode_p95_ms']:>9.3f}  {r['encode_p99_ms']:>9.3f}")

        print()

        # Decode latency comparison
        print("DECODE LATENCY (milliseconds):")
        print(f"{'Approach':<30} {'p50':>10} {'p95':>10} {'p99':>10}")
        print("-" * 80)

        for r in results:
            print(f"{r['name']:<30} {r['decode_p50_ms']:>9.3f}  {r['decode_p95_ms']:>9.3f}  {r['decode_p99_ms']:>9.3f}")

        print()

        # Key insights
        json_gzip = results[1]
        zeroc = results[4]

        size_improvement = json_gzip["avg_size_bytes"] / zeroc["avg_size_bytes"]
        encode_speedup = json_gzip["encode_p99_ms"] / zeroc["encode_p99_ms"]
        decode_speedup = json_gzip["decode_p99_ms"] / zeroc["decode_p99_ms"]

        print("KEY INSIGHTS:")
        print(f"  • Zeroc is {size_improvement:.2f}x smaller than JSON+gzip")
        print(f"  • Zeroc encodes {encode_speedup:.2f}x faster than JSON+gzip")
        print(f"  • Zeroc decodes {decode_speedup:.2f}x faster than JSON+gzip")
        print(f"  • Bandwidth saved: {(1 - zeroc['avg_size_bytes'] / json_gzip['avg_size_bytes']) * 100:.1f}%")


def main():
    """Run comprehensive benchmarks."""
    print("\n" + "="*80)
    print(" " * 20 + "ZEROC COMPREHENSIVE BENCHMARKS")
    print("="*80)
    print()
    print("Comparing 5 compression approaches:")
    print("  1. Raw JSON (baseline)")
    print("  2. JSON + gzip")
    print("  3. Protobuf (binary)")
    print("  4. Protobuf + gzip")
    print("  5. Zeroc (protobuf + zstd + trained dictionary)")
    print()

    benchmarker = CompressionBenchmark(
        sample_count=10000,
        latency_iterations=1000
    )

    # Dictionary paths
    dict_base = Path(__file__).parent.parent / "dictionaries" / "formats"

    # Benchmark Order
    order_results = benchmarker.benchmark_data_type(
        "order",
        benchmarker.json_to_proto_order,
        str(dict_base / "Order-1.0.0.zdict")
    )
    benchmarker.print_results("Order", order_results)

    # Benchmark ProductView
    view_results = benchmarker.benchmark_data_type(
        "product_view",
        benchmarker.json_to_proto_product_view,
        str(dict_base / "ProductView-1.0.0.zdict")
    )
    benchmarker.print_results("ProductView", view_results)

    # Benchmark SearchRequest
    search_results = benchmarker.benchmark_data_type(
        "search",
        benchmarker.json_to_proto_search,
        str(dict_base / "SearchRequest-1.0.0.zdict")
    )
    benchmarker.print_results("SearchRequest", search_results)

    print("\n" + "="*80)
    print(" " * 25 + "BENCHMARKS COMPLETE!")
    print("="*80)
    print()


if __name__ == "__main__":
    main()
