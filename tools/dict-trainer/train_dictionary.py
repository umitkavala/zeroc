#!/usr/bin/env python3
"""
Train and export ProtoZstd dictionaries from training samples.

Usage:
    python train_dictionary.py \
        --schema ecommerce.v1.Order \
        --version 1.0.0 \
        --samples samples.jsonl \
        --output dict.zdict
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../prototype'))

import argparse
import json
import struct
import time
import zlib
import hashlib
import zstandard as zstd
from pathlib import Path
from typing import List
from data_generator import DataGenerator
import api_schemas_pb2 as schemas


def json_to_proto_order(data: dict) -> bytes:
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


def json_to_proto_product_view(data: dict) -> bytes:
    """Convert JSON product view to protobuf binary."""
    view = schemas.ProductView()
    view.user_id = data["user_id"]
    view.product_id = data["product_id"]
    view.timestamp = data["timestamp"]
    view.referrer = data["referrer"]
    view.device_type = data["device_type"]
    return view.SerializeToString()


def json_to_proto_search(data: dict) -> bytes:
    """Convert JSON search request to protobuf binary."""
    search = schemas.SearchRequest()
    search.user_id = data["user_id"]
    search.query = data["query"]
    search.timestamp = data["timestamp"]
    search.page = data["page"]
    search.limit = data["limit"]
    search.filters.extend(data["filters"])
    return search.SerializeToString()


def create_dictionary(
    samples: List[bytes],
    schema_name: str,
    version: str,
    dict_size: int = 102400,
    compression_level: int = 3
) -> bytes:
    """
    Create ProtoZstd dictionary from training samples.

    Format (132-byte header):
      - Magic: "PZSTDICT" (8 bytes)
      - Version: SemVer (12 bytes)
      - Schema: Name (64 bytes)
      - Dict ID: CRC32 (4 bytes)
      - Sample Count: uint32 (4 bytes)
      - Created: Unix timestamp (8 bytes)
      - Compression Level: uint32 (4 bytes)
      - Dictionary Size: uint32 (4 bytes)
      - Min Protobuf Size: uint32 (4 bytes)
      - Max Protobuf Size: uint32 (4 bytes)
      - SHA256 Prefix: (8 bytes)
      - Reserved: (8 bytes)
    """
    print(f"Training dictionary for {schema_name} v{version}...")
    print(f"  Samples: {len(samples)}")
    print(f"  Target size: {dict_size} bytes")

    # 1. Train Zstd dictionary
    zstd_dict = zstd.train_dictionary(dict_size, samples, level=compression_level)
    zstd_dict_data = zstd_dict.as_bytes()

    print(f"  Dictionary trained: {len(zstd_dict_data)} bytes")

    # 2. Calculate metadata
    dict_id = zlib.crc32(zstd_dict_data) & 0xFFFFFFFF
    if dict_id == 0:
        dict_id = 0x00000001

    sample_sizes = [len(s) for s in samples]
    min_size = min(sample_sizes)
    max_size = max(sample_sizes)
    avg_size = sum(sample_sizes) / len(sample_sizes)

    sha256_full = hashlib.sha256(zstd_dict_data).digest()
    sha256_prefix = struct.unpack('>Q', sha256_full[:8])[0]

    print(f"  Dictionary ID: 0x{dict_id:08x}")
    print(f"  Payload size range: {min_size}-{max_size} bytes (avg: {avg_size:.0f})")

    # 3. Build header (132 bytes total)
    header = struct.pack(
        '>8s12s64sIIQIIIIQQ',
        b'PZSTDICT',                                      # Magic (8 bytes)
        version.encode('ascii').ljust(12, b'\0'),        # Version (12 bytes)
        schema_name.encode('ascii').ljust(64, b'\0'),    # Schema (64 bytes)
        dict_id,                                         # Dictionary ID (4 bytes)
        len(samples),                                    # Sample count (4 bytes)
        int(time.time()),                                # Created timestamp (8 bytes)
        compression_level,                               # Compression level (4 bytes)
        len(zstd_dict_data),                             # Dictionary size (4 bytes)
        min_size,                                        # Min protobuf size (4 bytes)
        max_size,                                        # Max protobuf size (4 bytes)
        sha256_prefix,                                   # SHA256 prefix (8 bytes)
        0                                                # Reserved (8 bytes)
    )

    assert len(header) == 132, f"Header size should be 132, got {len(header)}"

    # 4. Combine header + dictionary
    return header + zstd_dict_data


def generate_training_samples(schema: str, count: int) -> List[dict]:
    """Generate training samples for a schema."""
    generator = DataGenerator(seed=42)

    if "Order" in schema:
        return generator.generate_batch("order", count)
    elif "ProductView" in schema:
        return generator.generate_batch("product_view", count)
    elif "Search" in schema:
        return generator.generate_batch("search", count)
    else:
        raise ValueError(f"Unknown schema: {schema}")


def main():
    parser = argparse.ArgumentParser(description="Train ProtoZstd dictionary")
    parser.add_argument("--schema", required=True, help="Schema name (e.g., ecommerce.v1.Order)")
    parser.add_argument("--version", required=True, help="Dictionary version (e.g., 1.0.0)")
    parser.add_argument("--samples", type=int, default=10000, help="Number of training samples")
    parser.add_argument("--dict-size", type=int, default=102400, help="Dictionary size in bytes")
    parser.add_argument("--level", type=int, default=3, help="Compression level (1-22)")
    parser.add_argument("--output", help="Output file path")

    args = parser.parse_args()

    # Determine converter based on schema
    if "Order" in args.schema:
        converter = json_to_proto_order
    elif "ProductView" in args.schema:
        converter = json_to_proto_product_view
    elif "Search" in args.schema:
        converter = json_to_proto_search
    else:
        print(f"Error: Unknown schema type: {args.schema}")
        return 1

    # Generate training samples
    print(f"Generating {args.samples} training samples...")
    json_samples = generate_training_samples(args.schema, args.samples)

    # Convert to protobuf
    print(f"Converting to protobuf...")
    proto_samples = [converter(s) for s in json_samples]

    # Train dictionary
    dictionary = create_dictionary(
        samples=proto_samples,
        schema_name=args.schema,
        version=args.version,
        dict_size=args.dict_size,
        compression_level=args.level
    )

    # Determine output path
    if args.output:
        output_path = Path(args.output)
    else:
        # Default: dictionaries/formats/{schema}-{version}.zdict
        schema_short = args.schema.split('.')[-1]
        output_path = Path(__file__).parent.parent.parent / "dictionaries" / "formats" / f"{schema_short}-{args.version}.zdict"

    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Write dictionary
    with open(output_path, 'wb') as f:
        f.write(dictionary)

    print(f"\n✓ Dictionary saved to: {output_path}")
    print(f"  Total size: {len(dictionary)} bytes")
    print(f"  Header: 132 bytes")
    print(f"  Zstd data: {len(dictionary) - 132} bytes")

    # Generate metadata file
    meta_path = output_path.with_suffix('.meta.json')
    metadata = {
        "schema": args.schema,
        "version": args.version,
        "dictionary_id": f"0x{zlib.crc32(dictionary[132:]) & 0xFFFFFFFF:08x}",
        "created": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "size": len(dictionary),
        "sha256": hashlib.sha256(dictionary).hexdigest(),
        "training": {
            "sample_count": args.samples,
            "compression_level": args.level,
            "dict_size": args.dict_size
        }
    }

    with open(meta_path, 'w') as f:
        json.dump(metadata, f, indent=2)

    print(f"  Metadata: {meta_path}")

    # Generate SHA256 checksum
    sha256_path = output_path.with_suffix('.zdict.sha256')
    with open(sha256_path, 'w') as f:
        f.write(f"{metadata['sha256']}  {output_path.name}\n")

    print(f"  Checksum: {sha256_path}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
