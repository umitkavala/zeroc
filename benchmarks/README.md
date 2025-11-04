# Zeroc Benchmarks

Comprehensive benchmarks comparing different compression approaches for API payloads.

## Approaches Compared

1. **Raw JSON** - Uncompressed JSON (baseline)
2. **JSON + gzip** - Industry standard compression (gzip level 6)
3. **Protobuf** - Binary protobuf without compression
4. **Protobuf + gzip** - Protobuf with gzip compression (level 6)
5. **Zeroc** - Protobuf + zstd with 100KB trained dictionary (level 3)

## Metrics Measured

### Payload Sizes
- Average bytes per message
- Compression ratio vs baseline (Raw JSON)
- Size reduction percentage

### Latency
- **Encode latency**: Time to compress (p50, p95, p99)
- **Decode latency**: Time to decompress (p50, p95, p99)
- Measured over 1,000 iterations for statistical accuracy

## Data Types

### Orders
- Complex nested structure
- Multiple items (1-5 per order)
- Shipping address
- Typical size: ~350 bytes JSON

### Product Views
- Simple event structure
- Common in analytics
- Typical size: ~110 bytes JSON

### Search Requests
- Query with filters
- Pagination parameters
- Typical size: ~120 bytes JSON

## Running Benchmarks

### Prerequisites

```bash
# Ensure dictionaries are trained
cd tools/dict-trainer
python train_dictionary.py --schema ecommerce.v1.Order --version 1.0.0
python train_dictionary.py --schema ecommerce.v1.ProductView --version 1.0.0
python train_dictionary.py --schema ecommerce.v1.SearchRequest --version 1.0.0

# Install dependencies
cd ../..
source .venv/bin/activate
pip install zstandard crc32c protobuf
```

### Run Comprehensive Benchmarks

```bash
cd benchmarks
python comprehensive_benchmark.py
```

**Expected runtime**: ~60-90 seconds

### Sample Output

```
================================================================================
                    ZEROC COMPREHENSIVE BENCHMARKS
================================================================================

Comparing 5 compression approaches:
  1. Raw JSON (baseline)
  2. JSON + gzip
  3. Protobuf (binary)
  4. Protobuf + gzip
  5. Zeroc (protobuf + zstd + trained dictionary)

============================================================
Benchmarking: ORDER
============================================================
Generating 10,000 samples...

  Benchmarking Raw JSON...
  Benchmarking JSON + gzip...
  Benchmarking Protobuf...
  Benchmarking Protobuf + gzip...
  Benchmarking Zeroc (proto + zstd + dict)...

================================================================================
RESULTS: ORDER
================================================================================

PAYLOAD SIZES:
Approach                       Avg Size  vs Baseline   Reduction
--------------------------------------------------------------------------------
Raw JSON                          356.0B        1.00x        0.0%
JSON + gzip                       244.3B        1.46x       31.4%
Protobuf                          113.0B        3.15x       68.3%
Protobuf + gzip                    98.5B        3.61x       72.3%
Zeroc (proto + zstd + dict)        62.8B        5.67x       82.4%

ENCODE LATENCY (milliseconds):
Approach                           p50        p95        p99
--------------------------------------------------------------------------------
Raw JSON                         0.005      0.007      0.009
JSON + gzip                      0.033      0.045      0.052
Protobuf                         0.004      0.006      0.007
Protobuf + gzip                  0.028      0.039      0.045
Zeroc (proto + zstd + dict)      0.002      0.003      0.004

DECODE LATENCY (milliseconds):
Approach                           p50        p95        p99
--------------------------------------------------------------------------------
Raw JSON                         0.003      0.004      0.005
JSON + gzip                      0.006      0.008      0.010
Protobuf                         0.001      0.002      0.002
Protobuf + gzip                  0.005      0.007      0.008
Zeroc (proto + zstd + dict)      0.001      0.001      0.002

KEY INSIGHTS:
  • Zeroc is 3.89x smaller than JSON+gzip
  • Zeroc encodes 13.0x faster than JSON+gzip
  • Zeroc decodes 5.0x faster than JSON+gzip
  • Bandwidth saved: 74.3%
```

## Customization

### Adjust Sample Count

Edit `comprehensive_benchmark.py`:

```python
benchmarker = CompressionBenchmark(
    sample_count=10000,      # Number of samples to generate
    latency_iterations=1000  # Iterations for latency measurement
)
```

### Change Compression Levels

Modify compression parameters:

```python
# For gzip
gzip.compress(data, compresslevel=6)  # 1-9 (default: 6)

# For Zeroc/zstd
compressor = dict_loader.get_compressor(dict_path, level=3)  # 1-22 (default: 3)
```

### Add New Data Types

1. Add protobuf schema to `prototype/api_schemas.proto`
2. Compile: `python -m grpc_tools.protoc --python_out=. api_schemas.proto`
3. Add converter method to benchmark class
4. Train dictionary: `python tools/dict-trainer/train_dictionary.py --schema YourSchema --version 1.0.0`
5. Add benchmark call in `main()`

## Expected Results

### Payload Size Improvements

| Data Type | JSON+gzip | Zeroc | Improvement |
|-----------|-----------|-------|-------------|
| Orders | ~244 bytes | ~63 bytes | 3.9x smaller |
| Product Views | ~109 bytes | ~27 bytes | 4.0x smaller |
| Search Requests | ~121 bytes | ~29 bytes | 4.2x smaller |

### Latency Performance

| Operation | JSON+gzip | Zeroc | Speedup |
|-----------|-----------|-------|---------|
| Encode (p99) | 0.033-0.052ms | 0.001-0.004ms | 8-26x faster |
| Decode (p99) | 0.006-0.010ms | 0.001-0.002ms | 3-6x faster |

## Why Zeroc Wins

### Size Advantages

1. **Binary Protocol**: Protobuf eliminates JSON overhead (field names, quotes, whitespace)
2. **Trained Dictionary**: 100KB dictionary captures domain-specific patterns
3. **Zstd Algorithm**: Modern compression with excellent small-payload performance
4. **Zipfian Distribution**: Realistic data patterns amplify dictionary effectiveness

### Latency Advantages

1. **No JSON Parsing**: Skip expensive JSON serialization/deserialization
2. **Fast Dictionary Lookup**: Zstd dictionary compression is highly optimized
3. **Small Payloads**: Less data to process = faster operations
4. **CPU-Friendly**: Zstd designed for modern CPU architectures

### When Gzip Fails

Gzip actually **increases** size for some small payloads:

- Product Views: 108.7 → 109.2 bytes (grows by 0.5 bytes!)
- Search Requests: 121.5 → 120.6 bytes (barely shrinks)

This is due to gzip's ~18-byte header overhead overwhelming compression gains on tiny messages.

Zeroc achieves 4x compression on these same payloads.

## Performance Tips

### For Maximum Compression

```python
compressor = dict_loader.get_compressor(dict_path, level=19)  # Slower, better compression
```

### For Minimum Latency

```python
compressor = dict_loader.get_compressor(dict_path, level=1)  # Faster, slightly larger
```

### Balanced (Default)

```python
compressor = dict_loader.get_compressor(dict_path, level=3)  # Good balance
```

## Benchmark Validation

### Verify Round-Trip Correctness

```python
# All approaches should produce identical data after encode → decode
original_json = {"order_id": "123", ...}
encoded = encode_func(original_json)
decoded = decode_func(encoded)
assert decoded == original_json or proto_matches(decoded, original_json)
```

### Check for Data Loss

The benchmarks validate that:
- JSON round-trips produce identical objects
- Protobuf round-trips preserve all fields
- Zeroc decompression matches original protobuf

## Contributing

To add new benchmark scenarios:

1. Create new data generator in `prototype/data_generator.py`
2. Add protobuf schema
3. Train dictionary
4. Add benchmark method
5. Update this README with results

## References

- [Zstandard Documentation](https://facebook.github.io/zstd/)
- [Protocol Buffers Guide](https://protobuf.dev/)
- [Dictionary Training Guide](https://github.com/facebook/zstd#dictionary-compression-how-to)
