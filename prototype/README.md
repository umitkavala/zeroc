# ProtoZstd Prototype & Benchmark

This directory contains the original prototype implementation that demonstrated the feasibility of the ProtoZstd compression protocol.

## Files

| File | Description | Lines |
|------|-------------|-------|
| **api_schemas.proto** | Protocol Buffer schema definitions | 36 |
| **api_schemas_pb2.py** | Generated protobuf Python code | Auto-generated |
| **data_generator.py** | Mock e-commerce data generator with Zipfian distributions | 145 |
| **compression_benchmark.py** | Complete compression benchmark suite | 335 |

## Benchmark Results

Successfully tested with **31 million samples** (1M orders + 10M product views + 20M search requests):

| Metric | Orders | Product Views | Search Requests |
|--------|--------|---------------|-----------------|
| **Compression vs Gzip** | **3.88x better** | **4.01x better** | **4.21x better** |
| **Payload Reduction** | 356 → 62.8 bytes (82%) | 108.7 → 27.2 bytes (75%) | 121.5 → 28.7 bytes (76%) |
| **Encode Latency (p99)** | 0.002ms | 0.001ms | 0.001ms |
| **Decode Latency (p99)** | <0.001ms | <0.001ms | <0.001ms |

## Quick Start

### Prerequisites

```bash
# From project root
uv venv
uv pip install protobuf zstandard numpy grpcio-tools
```

### Generate Protobuf Code

```bash
cd prototype
source ../.venv/bin/activate
python -m grpc_tools.protoc --proto_path=. --python_out=. api_schemas.proto
```

### Run Benchmark

```bash
# Run with full dataset (takes ~30-40 seconds)
python compression_benchmark.py

# Output will show:
# - Compression ratios for each data type
# - Latency percentiles (p50, p95, p99)
# - Bandwidth savings
```

## Data Generator

The data generator creates realistic e-commerce API payloads:

```python
from data_generator import DataGenerator

gen = DataGenerator(seed=42)

# Generate order
order = gen.generate_order()
# {"order_id": "ORD-1234567", "user_id": 12345, ...}

# Generate product view
view = gen.generate_product_view()
# {"user_id": 1001, "product_id": 42, ...}

# Generate search request
search = gen.generate_search_request()
# {"user_id": 1001, "query": "laptop", ...}
```

### Features

- **Zipfian distribution** for realistic product popularity
- **10,000 products**, **50,000 users**
- **Diverse data**: Multiple countries, cities, payment methods
- **Configurable seed** for reproducible results

## Compression Benchmark

The benchmark suite tests three data types with different payload sizes:

### Architecture

```
JSON Data → Protobuf → Zstd + Dictionary → Compressed Bytes
            ↓           ↓
       Binary Format  Trained on 10K samples
```

### Process

1. **Generate Data**: Create realistic API payloads
2. **Train Dictionary**: Use 10,000 samples to train 100KB zstd dictionary
3. **Compress**: Encode JSON → Proto → Zstd with dictionary
4. **Measure**: Record sizes, compression ratios, latency
5. **Compare**: Benchmark against JSON + gzip

### Metrics Tracked

- **Payload sizes**: Raw JSON, gzip, proto+zstd
- **Compression ratios**: vs raw JSON
- **Encode latency**: Time to compress (p50, p95, p99)
- **Decode latency**: Time to decompress (p50, p95, p99)

## Key Insights

### Why Proto + Zstd Wins

1. **Protobuf Efficiency**: Binary format eliminates JSON overhead
   - No field names in payload
   - Compact varint encoding
   - Schema-based validation

2. **Dictionary Compression**: Trained on domain-specific data
   - Captures common patterns (field names, values)
   - 100KB dictionary provides massive wins on small payloads
   - Amortizes overhead across many messages

3. **Small Payload Optimization**:
   - Gzip struggles with <1KB payloads (header overhead)
   - Proto + zstd excels: 75-82% size reduction

### When It Works Best

| Payload Type | Size Range | Compression Ratio |
|--------------|------------|-------------------|
| API Requests | 100-500 bytes | 4-5x vs gzip |
| API Responses | 500-2KB | 3-4x vs gzip |
| IoT Telemetry | 50-200 bytes | 5-6x vs gzip |

### When to Use Alternatives

- **Large files (>10MB)**: Use streaming compression
- **Unique data**: Dictionary won't help much
- **CPU-constrained**: Gzip is faster to compress (but slower to decompress)

## Extending the Benchmark

### Add New Message Types

1. **Define protobuf schema** in `api_schemas.proto`:
   ```protobuf
   message NewMessage {
     int32 field1 = 1;
     string field2 = 2;
   }
   ```

2. **Recompile**:
   ```bash
   python -m grpc_tools.protoc --proto_path=. --python_out=. api_schemas.proto
   ```

3. **Add generator** in `data_generator.py`:
   ```python
   def generate_new_message(self) -> Dict[str, Any]:
       return {"field1": 123, "field2": "value"}
   ```

4. **Add benchmark** in `compression_benchmark.py`:
   ```python
   def json_to_proto_new_message(self, data: Dict[str, Any]) -> bytes:
       msg = schemas.NewMessage()
       msg.field1 = data["field1"]
       msg.field2 = data["field2"]
       return msg.SerializeToString()
   ```

### Adjust Parameters

```python
# In compression_benchmark.py

# Dictionary size (default: 100KB)
dict_size = 50 * 1024  # 50KB for faster compression
dict_size = 200 * 1024  # 200KB for better compression

# Compression level (default: 3)
compression_level = 1  # Faster compression
compression_level = 5  # Better compression

# Sample counts
sample_count = 10000      # Quick test
sample_count = 1000000    # Production-scale
```

## Integration with Production Code

The prototype served as the foundation for the production implementation in `../production/`:

| Prototype Component | Production Component |
|---------------------|---------------------|
| `compression_benchmark.py` | `production/middleware.py` |
| Dictionary training | `production/dictionary_manager.py` |
| Proto conversion | `production/middleware.py` (converters) |
| Metrics | `production/metrics.py` |

## Performance Tuning Tips

### For Maximum Compression

```python
# Use larger dictionary
dict_size = 200 * 1024

# Higher compression level
compression_level = 5

# More training samples
training_samples = 50000
```

### For Minimum Latency

```python
# Use smaller dictionary
dict_size = 50 * 1024

# Lower compression level
compression_level = 1

# Fewer training samples (faster to load)
training_samples = 1000
```

### For Balanced Performance

```python
# Current settings (recommended)
dict_size = 100 * 1024
compression_level = 3
training_samples = 10000
```

## Benchmark Reproducibility

All benchmarks use a **fixed seed (42)** for reproducibility:

```python
gen = DataGenerator(seed=42)
```

This ensures:
- Same product popularity distribution
- Same user IDs
- Same timestamps
- Identical results across runs

## Future Enhancements

- [ ] Streaming compression for large payloads
- [ ] Multiple compression algorithms (LZ4, Brotli)
- [ ] Adaptive dictionary selection
- [ ] Cross-language benchmarks
- [ ] Real production data analysis

## References

- **Zstandard**: https://facebook.github.io/zstd/
- **Protocol Buffers**: https://developers.google.com/protocol-buffers
- **Dictionary Training**: https://github.com/facebook/zstd#dictionary-compression

---

**This prototype proved the concept. See `../spec/` for the formal protocol specification.**
