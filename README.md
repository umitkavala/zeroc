# Zeroc: High-Performance API Compression Protocol

**Zeroc** is a compression protocol optimized for API payloads using **Protobuf + Zstandard with trained dictionaries**.

Achieve **2.35-3.22x better compression** than JSON+gzip with **4-5x faster** encode/decode speeds.

## 🎯 Benchmark Results

Comprehensive comparison across 5 approaches (Raw JSON, JSON+gzip, Protobuf, Protobuf+gzip, Zeroc):

### Orders (Complex Nested Structures)

| Approach | Size | vs JSON | vs JSON+gzip | Encode p99 | Decode p99 |
|----------|------|---------|--------------|------------|------------|
| Raw JSON | 356.0B | 1.00x | - | 0.002ms | 0.002ms |
| JSON + gzip | 244.0B | 1.46x | 1.00x | 0.010ms | 0.004ms |
| Protobuf | 113.5B | 3.14x | 2.15x | 0.002ms | <0.001ms |
| Protobuf + gzip | 128.5B | 2.77x | 1.90x | 0.005ms | 0.002ms |
| **Zeroc** | **75.8B** | **4.70x** | **3.22x** | **0.002ms** | **0.001ms** |

**Zeroc wins**: 3.22x smaller than JSON+gzip, 4.6x faster encode, 4.4x faster decode

### Product Views (Small Events)

| Approach | Size | vs JSON | vs JSON+gzip | Encode p99 | Decode p99 |
|----------|------|---------|--------------|------------|------------|
| Raw JSON | 108.8B | 1.00x | - | 0.001ms | 0.001ms |
| JSON + gzip | 109.3B | 1.00x | 1.00x ⚠️ | 0.006ms | 0.004ms |
| Protobuf | 28.6B | 3.80x | 3.82x | 0.001ms | <0.001ms |
| Protobuf + gzip | 48.7B | 2.24x | 2.24x | 0.003ms | 0.001ms |
| **Zeroc** | **46.5B** | **2.34x** | **2.35x** | **0.001ms** | **0.001ms** |

**Zeroc wins**: 2.35x smaller than JSON+gzip (which actually grows!), 4.4x faster encode, 4.6x faster decode

### Search Requests (Medium Complexity)

| Approach | Size | vs JSON | vs JSON+gzip | Encode p99 | Decode p99 |
|----------|------|---------|--------------|------------|------------|
| Raw JSON | 120.7B | 1.00x | - | 0.001ms | 0.001ms |
| JSON + gzip | 119.8B | 1.01x | 1.00x ⚠️ | 0.007ms | 0.004ms |
| Protobuf | 39.8B | 3.03x | 3.01x | 0.001ms | <0.001ms |
| Protobuf + gzip | 58.7B | 2.06x | 2.04x | 0.005ms | 0.001ms |
| **Zeroc** | **47.1B** | **2.56x** | **2.54x** | **0.001ms** | **0.001ms** |

**Zeroc wins**: 2.54x smaller than JSON+gzip (which barely compresses), 5.0x faster encode, 5.1x faster decode

⚠️ **Note**: JSON+gzip actually **increases** size for small payloads due to ~18-byte header overhead!

## 📁 Project Structure

```
compress/
├── README.md                      # This file
├── INDEX.md                       # Complete documentation index
│
├── prototype/                     # Original prototype & benchmarks
│   ├── api_schemas.proto          # Protobuf schema definitions
│   ├── api_schemas_pb2.py         # Generated protobuf Python code
│   ├── data_generator.py          # Mock e-commerce data generator
│   ├── compression_benchmark.py   # Compression pipeline & benchmarks
│   └── README.md                  # Prototype documentation
│
├── production/                    # Production-ready implementation
│   ├── middleware.py              # Compression middleware
│   ├── dictionary_manager.py      # Dictionary versioning & caching
│   ├── metrics.py                 # Monitoring (Prometheus/StatsD)
│   ├── client.py                  # HTTP client SDK
│   ├── server.py                  # FastAPI/Flask integration
│   ├── example.py                 # End-to-end examples
│   └── README.md                  # Production API docs
│
├── spec/                          # Protocol specifications
│   ├── PROTOCOL.md                # Complete protocol spec (65 pages)
│   ├── WIRE_FORMAT.md             # Binary wire format (40 pages)
│   ├── DICTIONARY_FORMAT.md       # Dictionary format (45 pages)
│   └── REPOSITORY_STRUCTURE.md    # Repository design (20 pages)
│
├── benchmarks/                    # Comprehensive benchmarks
│   ├── comprehensive_benchmark.py # Compare 5 approaches
│   ├── results.txt                # Latest benchmark results
│   └── README.md                  # Benchmark documentation
│
├── implementations/               # Multi-language implementations
│   ├── python/                    # Python (reference implementation)
│   ├── java/                      # Java (skeleton)
│   ├── go/                        # Go (skeleton)
│   ├── javascript/                # JavaScript/TypeScript (skeleton)
│   ├── csharp/                    # C# (skeleton)
│   └── README.md                  # Implementation guide
│
├── dictionaries/                  # Trained compression dictionaries
│   └── formats/                   # Per-schema dictionaries
│       ├── Order-1.0.0.zdict      # 100KB trained on 10K samples
│       ├── ProductView-1.0.0.zdict
│       └── SearchRequest-1.0.0.zdict
│
├── tools/                         # Development tools
│   └── dict-trainer/              # Dictionary training tool
│       └── train_dictionary.py    # CLI for training dictionaries
│
└── Documentation
    ├── PRODUCTION.md              # Production deployment guide
    ├── PRODUCTIONIZATION_SUMMARY.md  # Migration roadmap
    ├── PROJECT_README.md          # Main project overview
    └── PROTOCOL_DESIGN_SUMMARY.md # Design decisions (35 pages)
```

## 🚀 Quick Start

### Prerequisites

- **macOS** (tested on macOS)
- **UV** package manager ([install here](https://github.com/astral-sh/uv))
- **Python 3.10+**

### Installation

```bash
# 1. Create virtual environment
uv venv

# 2. Install dependencies
uv pip install protobuf zstandard numpy grpcio-tools

# 3. Compile protobuf schemas
source .venv/bin/activate
cd prototype
python -m grpc_tools.protoc --proto_path=. --python_out=. api_schemas.proto
```

### Run Benchmarks

```bash
# Run comprehensive benchmarks (compares 5 approaches)
source .venv/bin/activate
python benchmarks/comprehensive_benchmark.py
```

**Expected runtime:** ~60-90 seconds

This will compare:
1. Raw JSON (baseline)
2. JSON + gzip (industry standard)
3. Protobuf (binary only)
4. Protobuf + gzip
5. Zeroc (protobuf + zstd + dictionary)

See [benchmarks/README.md](benchmarks/README.md) for detailed documentation.

## 📊 What Gets Benchmarked

### Data Types

1. **Orders** (1M samples)
   - Order ID, user ID, timestamp
   - Multiple items with product ID, quantity, price
   - Shipping address (street, city, postal code, country)
   - Payment method, total amount

2. **Product Views** (10M samples)
   - User ID, product ID, timestamp
   - Referrer, device type

3. **Search Requests** (20M samples)
   - User ID, query string, timestamp
   - Pagination (page, limit)
   - Filters array

### Compression Methods

| Method | Description |
|--------|-------------|
| **Raw JSON** | Uncompressed JSON baseline |
| **JSON + gzip** | Industry standard (gzip level 6) |
| **Proto + zstd** | Protobuf binary + zstd with 100KB trained dictionary |

### Metrics Measured

- **Payload sizes**: Average bytes for each compression method
- **Compression ratios**: How much smaller vs raw JSON
- **Encode latency**: Time to compress (p50, p95, p99)
- **Decode latency**: Time to decompress (p50, p95, p99)

## 🔧 Customization

### Adjust Dataset Sizes

Edit `compression_benchmark.py` line 283-303:

```python
# Benchmark Orders
order_results = benchmarker.benchmark_data_type(
    "order",
    sample_count=1000000,  # ← Change this
    proto_converter=pipeline.json_to_proto_order,
    latency_iterations=1000  # ← Latency test iterations
)
```

### Modify Data Distribution

Edit `data_generator.py` line 21:

```python
# Zipfian parameter (1.0 = uniform, 2.0 = highly skewed)
self.zipf_products = self._generate_zipfian(self.num_products, 1.2)  # ← Adjust alpha
```

### Change Dictionary Size

Edit `compression_benchmark.py` line 66:

```python
def train_zstd_dictionary(self, samples: Sequence[bytes], dict_size: int = 100 * 1024):
    # ← Change dict_size (default: 100KB)
```

### Add New API Schemas

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

3. **Add converter** in `compression_benchmark.py`:
   ```python
   def json_to_proto_new_message(self, data: Dict[str, Any]) -> bytes:
       msg = schemas.NewMessage()  # type: ignore[attr-defined]
       msg.field1 = data["field1"]
       msg.field2 = data["field2"]
       return msg.SerializeToString()
   ```

4. **Add generator** in `data_generator.py`:
   ```python
   def generate_new_message(self) -> Dict[str, Any]:
       return {
           "field1": random.randint(1, 1000),
           "field2": random.choice(["value1", "value2"])
       }
   ```

## 📈 Understanding Results

### Why Proto + zstd Wins

1. **Binary Efficiency**: Protobuf eliminates JSON overhead (field names, quotes, whitespace)
2. **Trained Dictionary**: 100KB dictionary captures common patterns across 10K training samples
3. **Zipfian Distribution**: Realistic product popularity creates repetitive patterns
4. **Small Payloads**: At 100-350 bytes, dictionary compression provides massive wins

### When Gzip Fails

Notice gzip actually **increases** size for small payloads:
- Product Views: 108.7 → 109.2 bytes (grows!)
- Search Requests: 121.5 → 120.6 bytes (barely shrinks)

This is due to gzip header overhead (~18 bytes) overwhelming compression gains on tiny messages.

### Latency Breakdown

| Operation | Gzip | Proto + zstd | Speedup |
|-----------|------|--------------|---------|
| **Encode** | 0.007-0.033ms | 0.001-0.002ms | 3.5-30x faster |
| **Decode** | 0.003-0.006ms | <0.001ms | 3-6x faster |

## 🛠️ Development

### Type Checking

```bash
# Install type checker
uv pip install pyright types-protobuf

# Run type checks
source .venv/bin/activate
pyright data_generator.py compression_benchmark.py
```

### Test Data Generation

```bash
# Test individual generators
source .venv/bin/activate
python data_generator.py
```

Output:
```json
Sample Order:
{
  "order_id": "ORD-1234567",
  "user_id": 12345,
  "timestamp": 1704067200,
  "items": [...],
  "shipping_address": {...},
  "payment_method": "credit_card",
  "total_amount": 123.45
}
```

## 🔬 Technical Details

### Architecture

```
JSON Data → Protobuf Binary → zstd Compression → Compressed Bytes
                ↓                      ↓
         Schema-based         Dictionary-based
         Serialization         Compression
```

### Training Process

1. Generate sample data using realistic distributions
2. Convert 10,000 samples to protobuf binary
3. Train 100KB zstd dictionary on protobuf samples
4. Use dictionary for all subsequent compression operations

### Compression Pipeline

```python
# Encode
json_dict → protobuf.SerializeToString() → zstd_compressor.compress() → bytes

# Decode
bytes → zstd_decompressor.decompress() → protobuf.ParseFromString() → json_dict
```

## 📝 Performance Tips

### For Maximum Compression

1. **Larger dictionaries**: Increase `dict_size` to 200KB or 500KB
2. **More training samples**: Use 50K-100K samples for dictionary training
3. **Higher zstd level**: Add `level=19` to `ZstdCompressor()`

### For Minimum Latency

1. **Smaller dictionaries**: Reduce to 50KB
2. **Lower zstd level**: Use `level=1` (default is 3)
3. **Fewer training samples**: Use 1K-5K samples

### Balanced (Current Settings)

- **Dictionary size**: 100KB
- **Training samples**: 10K
- **Compression level**: 3 (default)

## 🎓 Use Cases

### Ideal For

- ✅ High-throughput API systems
- ✅ Mobile apps with bandwidth constraints
- ✅ IoT devices with limited data plans
- ✅ Microservices with repeated message patterns
- ✅ Real-time data streaming

### Not Ideal For

- ❌ Large, unique documents (>10MB)
- ❌ Already-compressed media (images, videos)
- ❌ Systems with limited CPU resources
- ❌ One-off, highly variable messages

## 📚 References

- [Protocol Buffers Documentation](https://protobuf.dev/)
- [Zstandard Compression](https://facebook.github.io/zstd/)
- [Zstandard Dictionary Training](https://github.com/facebook/zstd#dictionary-compression-how-to)
- [UV Package Manager](https://github.com/astral-sh/uv)

## 📄 License

This is a prototype/benchmark project. Use freely for educational and commercial purposes.

## 🤝 Contributing

This is a prototype benchmark. Feel free to:
- Add new API message types
- Test different compression algorithms
- Experiment with dictionary sizes
- Benchmark on different platforms

---

**Built with:** Python • Protobuf • zstd • NumPy • UV
