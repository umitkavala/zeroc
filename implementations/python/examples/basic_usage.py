#!/usr/bin/env python3
"""
Basic usage example for Zeroc Python implementation.

This example demonstrates:
1. Loading a trained dictionary
2. Encoding protobuf messages to Zeroc frames
3. Decoding Zeroc frames back to protobuf
4. Compression statistics
"""
import sys
from pathlib import Path

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from zeroc import (
    encode_frame,
    decode_frame,
    decompress_payload,
    DictionaryLoader,
)

# Add prototype path for protobuf schemas
prototype_path = Path(__file__).parent.parent.parent.parent.parent / "prototype"
sys.path.insert(0, str(prototype_path))

import api_schemas_pb2 as schemas


def example_without_dictionary():
    """Example: Compress protobuf without dictionary."""
    print("=" * 60)
    print("Example 1: Compression without dictionary")
    print("=" * 60)

    # Create a sample Order protobuf
    order = schemas.Order()
    order.order_id = "ORD-123456"
    order.user_id = 12345
    order.timestamp = 1704067200
    order.payment_method = "credit_card"
    order.total_amount = 299.99

    # Add shipping address
    order.shipping_address.street = "123 Main St"
    order.shipping_address.city = "San Francisco"
    order.shipping_address.postal_code = "94102"
    order.shipping_address.country = "US"

    # Add items
    item1 = order.items.add()
    item1.product_id = "PROD-001"
    item1.quantity = 2
    item1.price = 99.99

    item2 = order.items.add()
    item2.product_id = "PROD-002"
    item2.quantity = 1
    item2.price = 100.01

    # Serialize to protobuf binary
    proto_bytes = order.SerializeToString()
    print(f"Protobuf size: {len(proto_bytes)} bytes")

    # Encode to Zeroc frame (with compression, without dictionary)
    frame = encode_frame(
        proto_bytes,
        dictionary_id=0,
        schema_hash=0,
        compress=True,
        checksum=True
    )
    print(f"Zeroc frame size: {len(frame)} bytes")
    print(f"Compression ratio: {len(proto_bytes) / len(frame):.2f}x")

    # Decode frame
    compressed, metadata = decode_frame(frame)
    print(f"\nMetadata:")
    print(f"  Version: {metadata['major_version']}.{metadata['minor_version']}")
    print(f"  Compression: {metadata['compression_enabled']}")
    print(f"  Dictionary: {metadata['dictionary_used']}")
    print(f"  Checksum: {metadata['checksum_included']}")

    # Decompress
    decompressed = decompress_payload(compressed, metadata['dictionary_id'])

    # Parse back to protobuf
    order_decoded = schemas.Order()
    order_decoded.ParseFromString(decompressed)

    print(f"\nDecoded order:")
    print(f"  Order ID: {order_decoded.order_id}")
    print(f"  User ID: {order_decoded.user_id}")
    print(f"  Total: ${order_decoded.total_amount}")
    print(f"  Items: {len(order_decoded.items)}")

    # Verify
    assert order_decoded.order_id == order.order_id
    assert order_decoded.total_amount == order.total_amount
    print("\n✓ Round trip successful!\n")


def example_with_dictionary():
    """Example: Compress protobuf with trained dictionary."""
    print("=" * 60)
    print("Example 2: Compression with trained dictionary")
    print("=" * 60)

    # Load trained Order dictionary
    dict_path = Path(__file__).parent.parent.parent.parent.parent / \
                "dictionaries" / "formats" / "Order-1.0.0.zdict"

    if not dict_path.exists():
        print(f"⚠ Dictionary not found: {dict_path}")
        print("Run: cd tools/dict-trainer && python train_dictionary.py")
        return

    loader = DictionaryLoader()
    metadata, dict_obj = loader.load(str(dict_path))

    print(f"Dictionary loaded:")
    print(f"  Schema: {metadata['schema_name']}")
    print(f"  Version: {metadata['version']}")
    print(f"  Dictionary ID: 0x{metadata['dictionary_id']:08x}")
    print(f"  Sample count: {metadata['sample_count']}")
    print(f"  Size range: {metadata['min_size']}-{metadata['max_size']} bytes")

    # Create sample Order
    order = schemas.Order()
    order.order_id = "ORD-789012"
    order.user_id = 67890
    order.timestamp = 1704153600
    order.payment_method = "paypal"
    order.total_amount = 549.99

    order.shipping_address.street = "456 Oak Ave"
    order.shipping_address.city = "Los Angeles"
    order.shipping_address.postal_code = "90001"
    order.shipping_address.country = "US"

    item = order.items.add()
    item.product_id = "PROD-100"
    item.quantity = 3
    item.price = 183.33

    proto_bytes = order.SerializeToString()
    print(f"\nProtobuf size: {len(proto_bytes)} bytes")

    # Get compressor with dictionary
    compressor = loader.get_compressor(str(dict_path), level=3)
    decompressor = loader.get_decompressor(str(dict_path))

    # Encode with dictionary
    frame = encode_frame(
        proto_bytes,
        dictionary_id=metadata['dictionary_id'],
        schema_hash=0xABCD1234,  # Example schema hash
        compress=True,
        checksum=True,
        compressor=compressor
    )

    print(f"Zeroc frame size: {len(frame)} bytes")
    print(f"Compression ratio: {len(proto_bytes) / len(frame):.2f}x")
    print(f"Space saved: {len(proto_bytes) - len(frame)} bytes ({100 * (1 - len(frame) / len(proto_bytes)):.1f}%)")

    # Decode
    compressed, frame_metadata = decode_frame(frame)
    print(f"\nFrame metadata:")
    print(f"  Dictionary ID: 0x{frame_metadata['dictionary_id']:08x}")
    print(f"  Schema hash: 0x{frame_metadata['schema_hash']:08x}")
    print(f"  Dictionary used: {frame_metadata['dictionary_used']}")

    # Decompress with dictionary
    decompressed = decompress_payload(
        compressed,
        frame_metadata['dictionary_id'],
        decompressor
    )

    # Parse and verify
    order_decoded = schemas.Order()
    order_decoded.ParseFromString(decompressed)

    assert order_decoded.order_id == order.order_id
    assert order_decoded.user_id == order.user_id
    print("\n✓ Dictionary compression successful!\n")


def example_identity_frame():
    """Example: Identity frame (no compression)."""
    print("=" * 60)
    print("Example 3: Identity frame (no compression)")
    print("=" * 60)

    # Create small ProductView
    view = schemas.ProductView()
    view.user_id = 12345
    view.product_id = "PROD-500"
    view.timestamp = 1704067200
    view.referrer = "google"
    view.device_type = "mobile"

    proto_bytes = view.SerializeToString()
    print(f"Protobuf size: {len(proto_bytes)} bytes")

    # Identity frame (no compression)
    frame = encode_frame(proto_bytes, compress=False, checksum=False)
    print(f"Identity frame size: {len(frame)} bytes")
    print(f"Overhead: {len(frame) - len(proto_bytes)} bytes (header + varint)")

    # Decode
    decoded, metadata = decode_frame(frame)
    assert decoded == proto_bytes
    assert metadata['compression_enabled'] is False

    print("\n✓ Identity frame successful!\n")


def example_batch_compression():
    """Example: Batch compress multiple messages."""
    print("=" * 60)
    print("Example 4: Batch compression")
    print("=" * 60)

    # Load dictionary
    dict_path = Path(__file__).parent.parent.parent.parent.parent / \
                "dictionaries" / "formats" / "ProductView-1.0.0.zdict"

    if not dict_path.exists():
        print(f"⚠ Dictionary not found: {dict_path}")
        return

    loader = DictionaryLoader()
    metadata, _ = loader.load(str(dict_path))
    compressor = loader.get_compressor(str(dict_path))

    print(f"Dictionary: {metadata['schema_name']} v{metadata['version']}")

    # Create 100 product views
    total_proto_size = 0
    total_frame_size = 0

    for i in range(100):
        view = schemas.ProductView()
        view.user_id = 10000 + i
        view.product_id = f"PROD-{i % 20:03d}"  # 20 popular products
        view.timestamp = 1704067200 + i
        view.referrer = ["google", "facebook", "direct", "email"][i % 4]
        view.device_type = ["mobile", "desktop", "tablet"][i % 3]

        proto_bytes = view.SerializeToString()
        frame = encode_frame(
            proto_bytes,
            dictionary_id=metadata['dictionary_id'],
            compress=True,
            checksum=False,
            compressor=compressor
        )

        total_proto_size += len(proto_bytes)
        total_frame_size += len(frame)

    print(f"\nCompressed 100 product views:")
    print(f"  Total protobuf size: {total_proto_size} bytes")
    print(f"  Total frame size: {total_frame_size} bytes")
    print(f"  Average compression: {total_proto_size / total_frame_size:.2f}x")
    print(f"  Bandwidth saved: {total_proto_size - total_frame_size} bytes")
    print("\n✓ Batch compression successful!\n")


def main():
    """Run all examples."""
    print("\n")
    print("╔" + "═" * 58 + "╗")
    print("║" + " " * 10 + "Zeroc Python Usage Examples" + " " * 16 + "║")
    print("╚" + "═" * 58 + "╝")
    print("\n")

    example_without_dictionary()
    example_with_dictionary()
    example_identity_frame()
    example_batch_compression()

    print("=" * 60)
    print("All examples completed successfully!")
    print("=" * 60)


if __name__ == "__main__":
    main()
