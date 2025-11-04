#!/usr/bin/env python3
"""
Zeroc client SDK for FastAPI server.

Demonstrates how to make compressed API requests using Zeroc.
"""
import sys
import time
from pathlib import Path
from typing import Optional, Dict, Any

# Add parent directories to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "implementations" / "python"))
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "prototype"))

import requests
import api_schemas_pb2 as schemas

# Import Zeroc
try:
    from zeroc import DictionaryLoader, encode_frame, decode_frame, decompress_payload
except ImportError:
    print("ERROR: Cannot import zeroc. Please install: pip install -e implementations/python")
    sys.exit(1)


class ZerocClient:
    """
    HTTP client with Zeroc compression support.

    Automatically compresses requests and decompresses responses using Zeroc.
    """

    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.session = requests.Session()
        self.dict_loader = DictionaryLoader()

        # Load Order dictionary
        dict_path = Path(__file__).parent.parent.parent / "dictionaries" / "formats" / "Order-1.0.0.zdict"
        try:
            self.order_metadata, _ = self.dict_loader.load(str(dict_path))
            self.order_compressor = self.dict_loader.get_compressor(str(dict_path))
            self.order_decompressor = self.dict_loader.get_decompressor(str(dict_path))
            print(f"✓ Loaded Order dictionary (ID: 0x{self.order_metadata['dictionary_id']:08x})")
        except FileNotFoundError:
            print(f"WARNING: Dictionary not found at {dict_path}")
            self.order_compressor = None
            self.order_decompressor = None

    def get_order(self, order_id: str, use_compression: bool = True) -> Dict[str, Any]:
        """
        Get order by ID.

        Args:
            order_id: Order ID to fetch
            use_compression: Whether to request Zeroc compression

        Returns:
            Order data dict with compression stats
        """
        url = f"{self.base_url}/orders/{order_id}"
        headers = {}

        if use_compression and self.order_compressor:
            headers["Accept"] = "application/x-zeroc"

        start_time = time.time()
        response = self.session.get(url, headers=headers)
        latency = (time.time() - start_time) * 1000

        if response.headers.get("content-type") == "application/x-zeroc":
            # Decompress Zeroc frame
            frame = response.content
            compressed_payload, metadata = decode_frame(frame)
            proto_bytes = self.order_decompressor.decompress(compressed_payload)

            # Parse protobuf
            order = schemas.Order()
            order.ParseFromString(proto_bytes)

            # Get compression stats from headers
            original_size = int(response.headers.get("X-Zeroc-Original-Size", 0))
            compressed_size = int(response.headers.get("X-Zeroc-Compressed-Size", 0))
            ratio = float(response.headers.get("X-Zeroc-Ratio", 0))

            return {
                "order_id": order.order_id,
                "user_id": order.user_id,
                "timestamp": order.timestamp,
                "payment_method": order.payment_method,
                "total_amount": order.total_amount,
                "items": [
                    {
                        "product_id": item.product_id,
                        "quantity": item.quantity,
                        "price": item.price
                    }
                    for item in order.items
                ],
                "shipping_address": {
                    "street": order.shipping_address.street,
                    "city": order.shipping_address.city,
                    "postal_code": order.shipping_address.postal_code,
                    "country": order.shipping_address.country
                },
                "_compression": {
                    "used": True,
                    "original_size": original_size,
                    "compressed_size": compressed_size,
                    "ratio": ratio,
                    "latency_ms": latency
                }
            }
        else:
            # JSON response
            data = response.json()
            data["_compression"] = {
                "used": False,
                "size": len(response.content),
                "latency_ms": latency
            }
            return data

    def get_stats(self) -> Dict[str, Any]:
        """Get server compression statistics."""
        response = self.session.get(f"{self.base_url}/stats")
        return response.json()

    def health_check(self) -> Dict[str, Any]:
        """Check server health."""
        response = self.session.get(f"{self.base_url}/health")
        return response.json()


def main():
    """Demo client usage."""
    print("\n" + "="*80)
    print(" " * 25 + "ZEROC CLIENT DEMO")
    print("="*80 + "\n")

    # Create client
    client = ZerocClient()

    # Check server health
    print("1. Checking server health...")
    health = client.health_check()
    print(f"   Status: {health['status']}")
    print(f"   Zeroc enabled: {health['zeroc_enabled']}")
    print()

    # Test without compression
    print("2. Fetching order WITHOUT Zeroc compression...")
    order_json = client.get_order("ORD-12345", use_compression=False)
    print(f"   Order ID: {order_json['order_id']}")
    print(f"   Total: ${order_json['total_amount']:.2f}")
    print(f"   Response size: {order_json['_compression']['size']} bytes")
    print(f"   Latency: {order_json['_compression']['latency_ms']:.2f}ms")
    print()

    # Test with compression
    print("3. Fetching order WITH Zeroc compression...")
    order_compressed = client.get_order("ORD-12345", use_compression=True)
    print(f"   Order ID: {order_compressed['order_id']}")
    print(f"   Total: ${order_compressed['total_amount']:.2f}")
    if order_compressed['_compression']['used']:
        comp = order_compressed['_compression']
        print(f"   Original size: {comp['original_size']} bytes")
        print(f"   Compressed size: {comp['compressed_size']} bytes")
        print(f"   Compression ratio: {comp['ratio']:.2f}x")
        print(f"   Bytes saved: {comp['original_size'] - comp['compressed_size']} bytes")
        print(f"   Latency: {comp['latency_ms']:.2f}ms")
    print()

    # Compare
    if order_compressed['_compression']['used']:
        print("4. Comparison:")
        json_size = order_json['_compression']['size']
        zeroc_size = order_compressed['_compression']['compressed_size']
        savings = ((json_size - zeroc_size) / json_size) * 100
        print(f"   JSON response: {json_size} bytes")
        print(f"   Zeroc response: {zeroc_size} bytes")
        print(f"   Bandwidth savings: {savings:.1f}%")
        print(f"   Improvement: {json_size / zeroc_size:.2f}x smaller")
        print()

    # Get server stats
    print("5. Server compression statistics:")
    stats = client.get_stats()
    print(f"   Total requests: {stats['total_requests']}")
    print(f"   Compressed requests: {stats['compressed_requests']}")
    print(f"   Total bytes saved: {stats['total_bytes_saved']}")
    print(f"   Avg response time: {stats['avg_response_time_ms']:.2f}ms")
    print()

    print("="*80)
    print(" " * 25 + "DEMO COMPLETE")
    print("="*80 + "\n")


if __name__ == "__main__":
    main()
