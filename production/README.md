# Production Compression Middleware

Production-ready implementation of the Proto + zstd compression system.

## Features

- ✅ **Automatic compression/decompression** - Transparent to application code
- ✅ **Dictionary management** - Versioning, caching, CDN distribution
- ✅ **Error handling** - Graceful fallback to gzip
- ✅ **Metrics** - Prometheus, StatsD, CloudWatch support
- ✅ **Security** - Size limits, decompression bomb protection
- ✅ **Framework integration** - FastAPI, Flask, vanilla HTTP

## Quick Start

### Client SDK

```python
from production import CompressedAPIClient, CompressionConfig, MetricsBackend

# Configure compression
config = CompressionConfig(
    enabled=True,
    dictionary_version="1.0.0",
    cdn_url="https://cdn.example.com/dicts",
    fallback_to_gzip=True,
    max_payload_size=10 * 1024 * 1024  # 10MB
)

# Create client
with CompressedAPIClient(
    base_url="https://api.example.com",
    compression_config=config,
    metrics_backend=MetricsBackend.PROMETHEUS
) as client:
    # POST with automatic compression
    order_data = {
        "order_id": "ORD-12345",
        "user_id": 1001,
        # ... more fields
    }

    response = client.post(
        endpoint="/orders",
        data=order_data,
        data_type="order"  # Determines protobuf schema
    )

    print(f"Response: {response}")
```

### Server Integration (FastAPI)

```python
from production import create_compression_app, CompressionConfig, MetricsBackend

# Create app with compression
app = create_compression_app(
    compression_config=CompressionConfig(
        enabled=True,
        dictionary_version="1.0.0"
    ),
    metrics_backend=MetricsBackend.PROMETHEUS
)

# Run server
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

### Server Integration (Flask)

```python
from production import create_flask_compression_app

app = create_flask_compression_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
```

## Installation

```bash
# Required dependencies
uv pip install protobuf zstandard requests

# Optional: Metrics backends
uv pip install prometheus-client  # For Prometheus
uv pip install statsd             # For StatsD
uv pip install boto3              # For CloudWatch

# Optional: Server frameworks
uv pip install fastapi uvicorn    # For FastAPI
uv pip install flask              # For Flask
```

## Configuration

### CompressionConfig

```python
from production import CompressionConfig

config = CompressionConfig(
    # Enable/disable compression
    enabled=True,

    # Dictionary version (semantic versioning)
    dictionary_version="1.0.0",

    # Fallback to gzip on proto+zstd failure
    fallback_to_gzip=True,

    # Max compressed payload size (10MB)
    max_payload_size=10 * 1024 * 1024,

    # Max decompressed size (50MB, prevents decompression bombs)
    max_decompressed_size=50 * 1024 * 1024,

    # CDN URL for dictionary distribution
    cdn_url="https://cdn.example.com/dicts",

    # Enable metrics collection
    metrics_enabled=True
)
```

## Modules

### `middleware.py`

Core compression middleware with error handling.

**Classes:**
- `CompressionMiddleware` - Main middleware class
- `CompressionConfig` - Configuration dataclass
- `CompressionError` - Base exception
- `PayloadTooLarge` - Payload size limit exceeded
- `DecompressionBomb` - Decompressed size limit exceeded

### `dictionary_manager.py`

Dictionary versioning, caching, and CDN distribution.

**Features:**
- In-memory caching with TTL
- Disk cache fallback
- CDN download with integrity verification
- Thread-safe operations
- Automatic eviction of old versions

**Usage:**
```python
from production import DictionaryManager

manager = DictionaryManager(
    cache_dir="/tmp/compression_dicts",
    cdn_base_url="https://cdn.example.com/dicts",
    cache_ttl=86400,  # 24 hours
    max_cache_size=5   # Keep 5 versions
)

# Get compressor for version
compressor = manager.get_compressor("1.0.0")

# Preload dictionary
manager.preload_version("1.1.0")

# Get cache stats
stats = manager.get_cache_stats()
print(f"Cached versions: {stats['cached_versions']}")
```

### `metrics.py`

Metrics collection with multiple backend support.

**Supported Backends:**
- **Prometheus** - Pull-based metrics (recommended)
- **StatsD** - Push-based metrics
- **CloudWatch** - AWS CloudWatch metrics
- **NOOP** - Disabled (for testing)

**Metrics Tracked:**
- `compression_latency_seconds` - Encode/decode latency
- `compression_ratio` - Compression ratio achieved
- `compression_errors_total` - Error counts by type
- `bandwidth_saved_bytes_total` - Total bandwidth saved
- `dictionary_cache_hits/misses` - Cache performance
- `payload_size_bytes` - Payload size distribution

**Usage:**
```python
from production import get_metrics, MetricsBackend, CompressionTimer

# Initialize metrics
metrics = get_metrics(
    backend=MetricsBackend.PROMETHEUS
)

# Record compression
metrics.record_compression(
    original_size=1000,
    compressed_size=250,
    latency_seconds=0.002,
    endpoint="/orders",
    version="1.0.0"
)

# Or use timer
with CompressionTimer(metrics, operation="encode", endpoint="/orders") as timer:
    compressed = compress(data)
    timer.set_sizes(len(data), len(compressed))
```

### `client.py`

Production HTTP client SDK.

**Features:**
- Automatic request compression
- Automatic response decompression
- Content negotiation
- Error handling and retries
- Metrics integration

**Usage:**
```python
from production import CompressedAPIClient

with CompressedAPIClient("https://api.example.com") as client:
    # POST request
    response = client.post("/orders", data=order_data, data_type="order")

    # GET request
    order = client.get("/orders/12345")
```

### `server.py`

Server framework integrations.

**Supported Frameworks:**
- FastAPI (recommended)
- Flask

**Example:**
```python
from production import create_compression_app

app = create_compression_app()

# Endpoints automatically support compression
@app.post("/custom")
async def custom_endpoint(request: Request):
    # Decompressed data available in request.state.decompressed_data
    if hasattr(request.state, "decompressed_data"):
        data = request.state.decompressed_data
    else:
        data = await request.json()

    return {"status": "ok"}
```

## Headers

### Request Headers

| Header | Value | Description |
|--------|-------|-------------|
| `Content-Type` | `application/x-protobuf` | Protobuf encoded |
| `Content-Type` | `application/json` | JSON encoded |
| `Content-Encoding` | `proto-zstd` | Proto + zstd compression |
| `Content-Encoding` | `gzip` | Gzip compression |
| `X-Compression-Dict-Version` | `1.0.0` | Dictionary version used |
| `X-Original-Size` | `1024` | Original uncompressed size |
| `Accept-Encoding` | `proto-zstd, gzip` | Accepted encodings |

## Error Handling

```python
from production import CompressionError, PayloadTooLarge, DecompressionBomb

try:
    response = client.post("/orders", data=large_order, data_type="order")

except PayloadTooLarge:
    # Payload exceeds max_payload_size
    print("Order too large, split into multiple requests")

except DecompressionBomb:
    # Decompressed size exceeds max_decompressed_size
    print("Invalid compressed data")

except CompressionError as e:
    # Other compression errors (falls back to gzip if enabled)
    print(f"Compression error: {e}")
```

## Testing

```python
# Disable compression for testing
config = CompressionConfig(enabled=False)
client = CompressedAPIClient(base_url, compression_config=config)

# Or use NOOP metrics
metrics = get_metrics(backend=MetricsBackend.NOOP)
```

## Production Deployment

### 1. Dictionary Distribution

Upload dictionaries to CDN:
```bash
# Upload dictionary
aws s3 cp dict_1.0.0.zdict s3://your-bucket/dicts/

# Generate checksum
sha256sum dict_1.0.0.zdict > dict_1.0.0.zdict.sha256
aws s3 cp dict_1.0.0.zdict.sha256 s3://your-bucket/dicts/

# Set CDN URL in config
cdn_url="https://cdn.example.com/dicts"
```

### 2. Enable Metrics

**Prometheus:**
```python
# Server exposes /metrics endpoint automatically
app = create_compression_app(metrics_backend=MetricsBackend.PROMETHEUS)

# Scrape configuration (prometheus.yml)
scrape_configs:
  - job_name: 'api'
    static_configs:
      - targets: ['localhost:8000']
    metrics_path: '/metrics'
```

**StatsD:**
```python
metrics = get_metrics(
    backend=MetricsBackend.STATSD,
    host='statsd.example.com',
    port=8125,
    prefix='api.compression'
)
```

**CloudWatch:**
```python
metrics = get_metrics(
    backend=MetricsBackend.CLOUDWATCH,
    namespace='MyAPI/Compression',
    region_name='us-east-1'
)
```

### 3. Monitoring Alerts

See [PRODUCTION.md](../PRODUCTION.md) for alert configurations.

## Performance Tips

1. **Preload dictionaries** on server startup
   ```python
   manager = get_dictionary_manager()
   manager.preload_version("1.0.0")
   ```

2. **Use connection pooling**
   ```python
   session = requests.Session()
   client = CompressedAPIClient(base_url, session=session)
   ```

3. **Adjust cache TTL** based on dictionary update frequency
   ```python
   manager = DictionaryManager(cache_ttl=7*24*3600)  # 7 days
   ```

4. **Monitor metrics** and tune compression levels

## Troubleshooting

### Dictionary not found

```python
# Check dictionary manager cache
manager = get_dictionary_manager()
stats = manager.get_cache_stats()
print(stats)

# Clear cache and reload
manager.clear_cache()
manager.preload_version("1.0.0")
```

### High compression latency

- Check dictionary size (smaller = faster)
- Reduce zstd compression level
- Monitor CPU usage

### High error rate

- Check metrics for error types
- Verify dictionary versions match
- Check network connectivity to CDN

## Examples

See `examples/` directory for:
- Complete client/server examples
- Integration tests
- Performance benchmarks

## License

Production code for educational/commercial use.
