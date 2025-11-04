# Zeroc FastAPI Example

Production-ready FastAPI server with Zeroc compression middleware.

## Features

- ✅ FastAPI server with automatic Zeroc compression
- ✅ Compression middleware for transparent compression
- ✅ Client SDK with compression support
- ✅ E-commerce API example (orders)
- ✅ Compression statistics endpoint
- ✅ Docker support
- ✅ Production-ready code

## Quick Start

### Prerequisites

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Train dictionaries (if not already done)
cd ../../tools/dict-trainer
python train_dictionary.py --schema ecommerce.v1.Order --version 1.0.0

# 3. Compile protobuf schemas (if not already done)
cd ../../prototype
python -m grpc_tools.protoc --proto_path=. --python_out=. api_schemas.proto
```

### Run Server

```bash
# Start the FastAPI server
python server.py
```

Server will start on `http://localhost:8000`

### Test with Client

In a separate terminal:

```bash
# Run the demo client
python client.py
```

### Manual Testing

```bash
# Health check
curl http://localhost:8000/health

# Get order (JSON)
curl http://localhost:8000/orders/ORD-123

# Get order (Zeroc compressed)
curl -H "Accept: application/x-zeroc" \
     http://localhost:8000/orders/ORD-123 \
     --output response.zeroc

# View compression stats
curl http://localhost:8000/stats
```

## API Endpoints

### `GET /`
API root with documentation links

### `POST /orders`
Create a new order

**Request Body:**
```json
{
  "order_id": "ORD-123",
  "user_id": 12345,
  "items": [
    {
      "product_id": "PROD-001",
      "quantity": 2,
      "price": 29.99
    }
  ],
  "shipping_address": {
    "street": "123 Main St",
    "city": "San Francisco",
    "postal_code": "94102",
    "country": "USA"
  },
  "payment_method": "credit_card",
  "total_amount": 59.98
}
```

**Headers:**
- `Accept: application/x-zeroc` - Request Zeroc-compressed response

**Response:**
- Without compression: JSON response
- With compression: Zeroc-compressed protobuf frame

### `GET /orders/{order_id}`
Get order by ID

**Headers:**
- `Accept: application/x-zeroc` - Request Zeroc-compressed response

**Response Headers (when compressed):**
- `X-Zeroc-Original-Size` - Original protobuf size in bytes
- `X-Zeroc-Compressed-Size` - Compressed frame size in bytes
- `X-Zeroc-Ratio` - Compression ratio (e.g., "2.15")
- `X-Zeroc-Dictionary-ID` - Dictionary ID used for compression

### `GET /stats`
Get compression statistics

**Response:**
```json
{
  "total_requests": 100,
  "compressed_requests": 75,
  "total_bytes_saved": 15420,
  "avg_compression_ratio": 2.15,
  "avg_response_time_ms": 1.23
}
```

### `GET /health`
Health check endpoint

**Response:**
```json
{
  "status": "healthy",
  "zeroc_enabled": true,
  "dictionary_loaded": true
}
```

## Client SDK

### Basic Usage

```python
from client import ZerocClient

# Create client
client = ZerocClient(base_url="http://localhost:8000")

# Get order with Zeroc compression
order = client.get_order("ORD-123", use_compression=True)
print(f"Order total: ${order['total_amount']:.2f}")
print(f"Compression ratio: {order['_compression']['ratio']:.2f}x")
print(f"Bytes saved: {order['_compression']['original_size'] - order['_compression']['compressed_size']}")

# Get server stats
stats = client.get_stats()
print(f"Total bytes saved: {stats['total_bytes_saved']}")
```

### Custom Integration

```python
import requests
from zeroc import decode_frame, DictionaryLoader

# Load dictionary
loader = DictionaryLoader()
decompressor = loader.get_decompressor("path/to/Order-1.0.0.zdict")

# Make request with Zeroc compression
response = requests.get(
    "http://localhost:8000/orders/ORD-123",
    headers={"Accept": "application/x-zeroc"}
)

# Decompress response
if response.headers["content-type"] == "application/x-zeroc":
    frame = response.content
    compressed_payload, metadata = decode_frame(frame)
    proto_bytes = decompressor.decompress(compressed_payload)

    # Parse protobuf
    order = Order()
    order.ParseFromString(proto_bytes)
```

## Docker Support

### Build Image

```bash
docker build -t zeroc-api .
```

### Run Container

```bash
docker run -p 8000:8000 zeroc-api
```

### Docker Compose

```yaml
version: '3.8'
services:
  api:
    build: .
    ports:
      - "8000:8000"
    environment:
      - LOG_LEVEL=info
    volumes:
      - ../../dictionaries:/app/dictionaries:ro
```

## Performance

Expected performance on modern hardware:

| Metric | Value |
|--------|-------|
| Compression ratio | 2-3x vs JSON |
| Encode latency | 1-2ms |
| Decode latency | <1ms |
| Throughput | 1000+ req/sec |
| Memory overhead | ~1MB (dictionary cache) |

## Production Deployment

### Environment Variables

```bash
export ZEROC_DICT_PATH=/app/dictionaries
export ZEROC_COMPRESSION_LEVEL=3
export ZEROC_ENABLE_CHECKSUM=true
export LOG_LEVEL=info
```

### Best Practices

1. **Dictionary Caching**: Dictionaries are cached on startup for performance
2. **Compression Level**: Use level 3-6 for balanced speed/ratio
3. **Checksum**: Enable checksums (`checksum=True`) for production
4. **Content Negotiation**: Support both JSON and Zeroc responses
5. **Monitoring**: Track compression stats via `/stats` endpoint

### Monitoring

```python
# Add custom metrics
from prometheus_client import Counter, Histogram

compression_requests = Counter('zeroc_requests_total', 'Total Zeroc requests')
compression_ratio = Histogram('zeroc_compression_ratio', 'Compression ratio')
bytes_saved = Counter('zeroc_bytes_saved_total', 'Total bytes saved')
```

## Error Handling

The server handles common errors:

- **Dictionary not found**: Returns JSON response (no compression)
- **Invalid Zeroc frame**: Returns 400 Bad Request
- **Checksum mismatch**: Returns 400 Bad Request
- **Decompression error**: Returns 500 Internal Server Error

## Testing

### Unit Tests

```bash
pytest tests/test_server.py -v
```

### Load Testing

```bash
# Install locust
pip install locust

# Run load test
locust -f locustfile.py --host http://localhost:8000
```

### Integration Tests

```bash
# Start server
python server.py &

# Run client tests
python test_client.py

# Stop server
pkill -f server.py
```

## Troubleshooting

### Dictionary Not Found

```
WARNING: Dictionary not found at dictionaries/formats/Order-1.0.0.zdict
```

**Solution:**
```bash
cd ../../tools/dict-trainer
python train_dictionary.py --schema ecommerce.v1.Order --version 1.0.0
```

### Import Error

```
ModuleNotFoundError: No module named 'zeroc'
```

**Solution:**
```bash
cd ../../implementations/python
pip install -e .
```

### Port Already in Use

```
ERROR: [Errno 48] Address already in use
```

**Solution:**
```bash
# Kill existing process
lsof -ti:8000 | xargs kill -9

# Or use different port
uvicorn server:app --port 8001
```

## Architecture

```
Client Request
    ↓
FastAPI Middleware (checks Accept header)
    ↓
Business Logic (process order)
    ↓
Convert to Protobuf
    ↓
Zeroc Compression (if requested)
    ↓
Response (JSON or Zeroc frame)
    ↓
Client
```

## Next Steps

1. **Add Authentication**: Integrate JWT or API key auth
2. **Add Database**: Connect to PostgreSQL/MongoDB
3. **Add Caching**: Redis cache for hot orders
4. **Add Metrics**: Prometheus metrics export
5. **Add Tracing**: OpenTelemetry distributed tracing
6. **Add Rate Limiting**: Protect against abuse
7. **Add HTTPS**: TLS termination with Let's Encrypt

## License

MIT License - See ../../LICENSE

## Links

- [Main Repository](https://github.com/umitkavala/zeroc)
- [Protocol Specification](../../spec/PROTOCOL.md)
- [Python Implementation](../../implementations/python/README.md)
