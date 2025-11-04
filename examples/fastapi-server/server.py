#!/usr/bin/env python3
"""
FastAPI server with Zeroc compression middleware.

Example e-commerce API demonstrating Zeroc compression for API payloads.
"""
import sys
import time
from pathlib import Path
from typing import Optional

# Add parent directories to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "implementations" / "python"))
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "prototype"))

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import api_schemas_pb2 as schemas

# Import Zeroc
try:
    from zeroc import DictionaryLoader, encode_frame, decode_frame, decompress_payload
except ImportError:
    print("ERROR: Cannot import zeroc. Please install: pip install -e implementations/python")
    sys.exit(1)

# Create FastAPI app
app = FastAPI(
    title="Zeroc E-commerce API",
    description="Example API with Zeroc compression",
    version="1.0.0"
)

# Initialize dictionary loader
dict_loader = DictionaryLoader()
DICT_PATH = Path(__file__).parent.parent.parent / "dictionaries" / "formats" / "Order-1.0.0.zdict"

# Load dictionaries at startup
try:
    order_metadata, _ = dict_loader.load(str(DICT_PATH))
    order_compressor = dict_loader.get_compressor(str(DICT_PATH), level=3)
    order_decompressor = dict_loader.get_decompressor(str(DICT_PATH))
    print(f"✓ Loaded Order dictionary (ID: 0x{order_metadata['dictionary_id']:08x})")
except FileNotFoundError:
    print(f"WARNING: Dictionary not found at {DICT_PATH}")
    print("Run: python tools/dict-trainer/train_dictionary.py --schema ecommerce.v1.Order")
    order_compressor = None
    order_decompressor = None


# Pydantic models for API
class OrderItem(BaseModel):
    product_id: str
    quantity: int
    price: float


class Address(BaseModel):
    street: str
    city: str
    postal_code: str
    country: str


class OrderRequest(BaseModel):
    order_id: str
    user_id: int
    items: list[OrderItem]
    shipping_address: Address
    payment_method: str
    total_amount: float


class OrderResponse(BaseModel):
    order_id: str
    status: str
    created_at: int
    compressed: bool
    compression_ratio: Optional[float] = None
    size_bytes: int


class StatsResponse(BaseModel):
    total_requests: int
    compressed_requests: int
    total_bytes_saved: int
    avg_compression_ratio: float
    avg_response_time_ms: float


# In-memory stats
stats = {
    "total_requests": 0,
    "compressed_requests": 0,
    "total_bytes_saved": 0,
    "total_response_time": 0.0
}


# Middleware for Zeroc compression
@app.middleware("http")
async def zeroc_compression_middleware(request: Request, call_next):
    """
    Middleware to handle Zeroc compression/decompression.

    - Checks Accept header for "application/x-zeroc"
    - Compresses responses using Zeroc if requested
    - Decompresses Zeroc requests if Content-Type is "application/x-zeroc"
    """
    start_time = time.time()

    # Check if client accepts Zeroc compression
    accept_zeroc = "application/x-zeroc" in request.headers.get("accept", "")

    # Check if request is Zeroc-compressed
    if request.headers.get("content-type") == "application/x-zeroc":
        # TODO: Decompress request body
        pass

    # Process request
    response = await call_next(request)

    # Compress response if client accepts Zeroc
    if accept_zeroc and response.status_code == 200:
        # Note: This is a simplified example
        # In production, you'd serialize the response to protobuf first
        stats["compressed_requests"] += 1

    stats["total_requests"] += 1
    stats["total_response_time"] += (time.time() - start_time) * 1000

    return response


def json_to_proto_order(data: dict) -> bytes:
    """Convert JSON order dict to protobuf bytes."""
    order = schemas.Order()
    order.order_id = data["order_id"]
    order.user_id = data["user_id"]
    order.timestamp = int(time.time())
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


# API Endpoints

@app.get("/")
async def root():
    """API root with welcome message."""
    return {
        "message": "Zeroc E-commerce API",
        "version": "1.0.0",
        "docs": "/docs",
        "endpoints": {
            "POST /orders": "Create order (supports Zeroc compression)",
            "GET /orders/{order_id}": "Get order (supports Zeroc compression)",
            "GET /stats": "Compression statistics",
            "GET /health": "Health check"
        }
    }


@app.post("/orders", response_model=OrderResponse)
async def create_order(order: OrderRequest, request: Request):
    """
    Create a new order.

    Supports Zeroc compression:
    - Set Accept: application/x-zeroc to receive compressed response
    - Response will be Zeroc-compressed protobuf frame
    """
    start_time = time.time()

    # Convert to protobuf
    proto_bytes = json_to_proto_order(order.dict())
    original_size = len(proto_bytes)

    # Check if client accepts Zeroc
    accept_zeroc = "application/x-zeroc" in request.headers.get("accept", "")

    if accept_zeroc and order_compressor:
        # Compress with Zeroc
        frame = encode_frame(
            proto_bytes,
            dictionary_id=order_metadata['dictionary_id'],
            compress=True,
            checksum=True,
            compressor=order_compressor
        )
        compressed_size = len(frame)
        compression_ratio = original_size / compressed_size

        # Update stats
        stats["compressed_requests"] += 1
        stats["total_bytes_saved"] += (original_size - compressed_size)

        # Return Zeroc-compressed response
        return Response(
            content=frame,
            media_type="application/x-zeroc",
            headers={
                "X-Zeroc-Original-Size": str(original_size),
                "X-Zeroc-Compressed-Size": str(compressed_size),
                "X-Zeroc-Ratio": f"{compression_ratio:.2f}",
                "X-Zeroc-Dictionary-ID": f"0x{order_metadata['dictionary_id']:08x}"
            }
        )
    else:
        # Return JSON response
        response_time = (time.time() - start_time) * 1000
        return OrderResponse(
            order_id=order.order_id,
            status="created",
            created_at=int(time.time()),
            compressed=False,
            size_bytes=original_size
        )


@app.get("/orders/{order_id}")
async def get_order(order_id: str, request: Request):
    """
    Get order by ID.

    Supports Zeroc compression with Accept: application/x-zeroc header.
    """
    # Mock order data
    mock_order = {
        "order_id": order_id,
        "user_id": 12345,
        "timestamp": int(time.time()),
        "items": [
            {"product_id": "PROD-001", "quantity": 2, "price": 29.99},
            {"product_id": "PROD-002", "quantity": 1, "price": 49.99}
        ],
        "shipping_address": {
            "street": "123 Main St",
            "city": "San Francisco",
            "postal_code": "94102",
            "country": "USA"
        },
        "payment_method": "credit_card",
        "total_amount": 109.97
    }

    # Convert to protobuf
    proto_bytes = json_to_proto_order(mock_order)
    original_size = len(proto_bytes)

    # Check if client accepts Zeroc
    accept_zeroc = "application/x-zeroc" in request.headers.get("accept", "")

    if accept_zeroc and order_compressor:
        # Compress with Zeroc
        frame = encode_frame(
            proto_bytes,
            dictionary_id=order_metadata['dictionary_id'],
            compress=True,
            checksum=True,
            compressor=order_compressor
        )
        compressed_size = len(frame)

        return Response(
            content=frame,
            media_type="application/x-zeroc",
            headers={
                "X-Zeroc-Original-Size": str(original_size),
                "X-Zeroc-Compressed-Size": str(compressed_size),
                "X-Zeroc-Ratio": f"{original_size / compressed_size:.2f}"
            }
        )
    else:
        # Return JSON
        return JSONResponse(content=mock_order)


@app.get("/stats", response_model=StatsResponse)
async def get_stats():
    """Get compression statistics."""
    avg_compression = (
        stats["total_bytes_saved"] / stats["compressed_requests"]
        if stats["compressed_requests"] > 0
        else 0
    )
    avg_response_time = (
        stats["total_response_time"] / stats["total_requests"]
        if stats["total_requests"] > 0
        else 0
    )

    return StatsResponse(
        total_requests=stats["total_requests"],
        compressed_requests=stats["compressed_requests"],
        total_bytes_saved=stats["total_bytes_saved"],
        avg_compression_ratio=avg_compression,
        avg_response_time_ms=avg_response_time
    )


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "zeroc_enabled": order_compressor is not None,
        "dictionary_loaded": order_compressor is not None
    }


if __name__ == "__main__":
    import uvicorn
    print("\n" + "="*80)
    print(" " * 25 + "ZEROC FASTAPI SERVER")
    print("="*80)
    print("\nStarting server with Zeroc compression support...")
    print("\nEndpoints:")
    print("  - http://localhost:8000/ (API documentation)")
    print("  - http://localhost:8000/docs (Swagger UI)")
    print("  - http://localhost:8000/health (Health check)")
    print("\nTo test Zeroc compression:")
    print('  curl -H "Accept: application/x-zeroc" http://localhost:8000/orders/ORD-123')
    print("\n" + "="*80 + "\n")

    uvicorn.run(app, host="0.0.0.0", port=8000)
