# Zeroc Python Implementation

Python reference implementation of the Zeroc compression protocol.

## Features

- ✅ Complete wire format implementation (12-byte header + varint + payload)
- ✅ Dictionary loader with 132-byte header validation
- ✅ CRC32C checksum support
- ✅ Dictionary caching for performance
- ✅ Comprehensive test suite
- ✅ Type annotations for IDE support

## Installation

### From Source

```bash
cd implementations/python
pip install -e .
```

### Dependencies

```bash
pip install zstandard crc32c protobuf
```

## Quick Start

### Basic Compression (No Dictionary)

```python
from zeroc import encode_frame, decode_frame, decompress_payload

# Encode protobuf to Zeroc frame
proto_bytes = b"Your protobuf serialized data"
frame = encode_frame(proto_bytes, compress=True, checksum=True)

# Decode frame
compressed, metadata = decode_frame(frame)

# Decompress
decompressed = decompress_payload(compressed, 0)
```

### With Trained Dictionary

```python
from zeroc import DictionaryLoader, encode_frame, decode_frame

# Load dictionary
loader = DictionaryLoader()
metadata, dict_obj = loader.load("dictionaries/formats/Order-1.0.0.zdict")

# Get compressor/decompressor
compressor = loader.get_compressor("dictionaries/formats/Order-1.0.0.zdict")
decompressor = loader.get_decompressor("dictionaries/formats/Order-1.0.0.zdict")

# Encode with dictionary
frame = encode_frame(
    proto_bytes,
    dictionary_id=metadata['dictionary_id'],
    compress=True,
    checksum=True,
    compressor=compressor
)

# Decode and decompress
compressed, frame_meta = decode_frame(frame)
decompressed = decompressor.decompress(compressed)
```

## API Reference

### Wire Format

#### `encode_frame(proto_bytes, dictionary_id=0, schema_hash=0, compress=True, checksum=False, compressor=None)`

Encode protobuf bytes to Zeroc frame.

**Parameters:**
- `proto_bytes` (bytes): Protobuf binary data
- `dictionary_id` (int): Dictionary ID (CRC32), 0 for no dictionary
- `schema_hash` (int): Schema hash (CRC32)
- `compress` (bool): Whether to compress (True) or identity (False)
- `checksum` (bool): Whether to include CRC32C checksum
- `compressor` (ZstdCompressor): Required if dictionary_id > 0

**Returns:**
- `bytes`: Complete Zeroc frame

**Example:**
```python
frame = encode_frame(proto_bytes, compress=True, checksum=True)
```

#### `decode_frame(frame)`

Decode Zeroc frame to payload and metadata.

**Parameters:**
- `frame` (bytes): Complete Zeroc frame

**Returns:**
- `(bytes, dict)`: Tuple of (payload, metadata)

**Metadata Fields:**
- `version`: Protocol version byte
- `major_version`: Major version (1)
- `minor_version`: Minor version (0)
- `flags`: Flags byte
- `dictionary_id`: Dictionary ID
- `schema_hash`: Schema hash
- `compressed_size`: Payload size in bytes
- `compression_enabled`: Boolean
- `dictionary_used`: Boolean
- `checksum_included`: Boolean

**Raises:**
- `ValueError`: If frame is invalid or malformed

**Example:**
```python
compressed, metadata = decode_frame(frame)
print(f"Dictionary ID: 0x{metadata['dictionary_id']:08x}")
```

#### `decompress_payload(compressed, dictionary_id, decompressor=None)`

Decompress payload with optional dictionary.

**Parameters:**
- `compressed` (bytes): Compressed bytes
- `dictionary_id` (int): Dictionary ID (0 for no dictionary)
- `decompressor` (ZstdDecompressor): Required if dictionary_id > 0

**Returns:**
- `bytes`: Decompressed protobuf bytes

**Example:**
```python
proto_bytes = decompress_payload(compressed, 0)  # No dictionary
proto_bytes = decompress_payload(compressed, dict_id, decompressor)  # With dictionary
```

### Dictionary Loader

#### `load_dictionary(filepath)`

Load Zeroc dictionary from .zdict file.

**Parameters:**
- `filepath` (str): Path to .zdict file

**Returns:**
- `(dict, ZstdCompressionDict)`: Tuple of (metadata, dictionary object)

**Metadata Fields:**
- `version`: SemVer string (e.g., "1.0.0")
- `schema_name`: Schema name (e.g., "ecommerce.v1.Order")
- `dictionary_id`: Dictionary ID (CRC32)
- `sample_count`: Number of training samples
- `created`: Unix timestamp
- `compression_level`: Zstd compression level
- `dict_size`: Dictionary size in bytes
- `min_size`: Minimum protobuf size
- `max_size`: Maximum protobuf size
- `sha256_prefix`: First 8 bytes of SHA256

**Raises:**
- `FileNotFoundError`: If file doesn't exist
- `ValueError`: If dictionary format is invalid

**Example:**
```python
metadata, dict_obj = load_dictionary("Order-1.0.0.zdict")
print(f"Dictionary ID: 0x{metadata['dictionary_id']:08x}")
```

#### `DictionaryLoader`

Dictionary loader with caching.

**Methods:**

##### `load(filepath)`

Load dictionary with caching.

```python
loader = DictionaryLoader()
metadata, dict_obj = loader.load("Order-1.0.0.zdict")
```

##### `get_compressor(filepath, level=3)`

Get ZstdCompressor for dictionary.

```python
compressor = loader.get_compressor("Order-1.0.0.zdict", level=3)
compressed = compressor.compress(proto_bytes)
```

##### `get_decompressor(filepath)`

Get ZstdDecompressor for dictionary.

```python
decompressor = loader.get_decompressor("Order-1.0.0.zdict")
decompressed = decompressor.decompress(compressed)
```

##### `clear_cache()`

Clear dictionary cache.

```python
loader.clear_cache()
```

### Constants

```python
from zeroc import (
    MAGIC_BYTES,           # b'PZ'
    PROTOCOL_VERSION,      # 0x10 (v1.0)
    FLAG_COMPRESSION_ENABLED,
    FLAG_DICTIONARY_USED,
    FLAG_CHECKSUM_INCLUDED,
)
```

## Examples

See `examples/basic_usage.py` for comprehensive examples:

```bash
cd implementations/python
python examples/basic_usage.py
```

Examples include:
1. Compression without dictionary
2. Compression with trained dictionary
3. Identity frame (no compression)
4. Batch compression (100 messages)

## Testing

### Run Tests

```bash
# Install test dependencies
pip install pytest

# Run all tests
cd implementations/python
pytest tests/ -v

# Run specific test
pytest tests/test_wire_format.py::TestFrameEncoding::test_identity_frame -v

# Run with coverage
pip install pytest-cov
pytest tests/ --cov=zeroc --cov-report=html
```

### Test Coverage

- Wire format: varint encoding/decoding, frame encoding/decoding, error handling
- Dictionary loader: format validation, caching, real dictionaries
- Round-trip tests: encode → decode → decompress

## Performance

Typical performance on modern hardware:

| Operation | Latency | Throughput |
|-----------|---------|------------|
| Encode (no dict) | ~0.001ms | ~1M ops/sec |
| Encode (with dict) | ~0.002ms | ~500K ops/sec |
| Decode (no dict) | <0.001ms | ~2M ops/sec |
| Decode (with dict) | <0.001ms | ~2M ops/sec |

## Wire Format Specification

Zeroc frame structure:

```
+-------------------+
| Magic "PZ" (2B)   |  Fixed header
+-------------------+
| Version (1B)      |  0x10 = v1.0
+-------------------+
| Flags (1B)        |  Compression/Dict/Checksum
+-------------------+
| Dict ID (4B)      |  CRC32 of dictionary (big-endian)
+-------------------+
| Schema Hash (4B)  |  CRC32 of schema (big-endian)
+-------------------+
| Payload Len       |  LEB128 varint
+-------------------+
| Compressed Data   |  Zstd compressed protobuf
+-------------------+
| CRC32C (4B)       |  Optional checksum (if flag set)
+-------------------+
```

## Dictionary Format Specification

Zeroc dictionary file (.zdict):

```
+----------------------+
| Magic "PZSTDICT" (8B)|  132-byte header
+----------------------+
| Version (12B)        |  SemVer, null-padded
+----------------------+
| Schema Name (64B)    |  Schema name, null-padded
+----------------------+
| Dict ID (4B)         |  CRC32 of dictionary data
+----------------------+
| Sample Count (4B)    |  Training sample count
+----------------------+
| Created (8B)         |  Unix timestamp
+----------------------+
| Compression Lvl (4B) |  Zstd level used
+----------------------+
| Dict Size (4B)       |  Dictionary data size
+----------------------+
| Min Protobuf (4B)    |  Min protobuf size
+----------------------+
| Max Protobuf (4B)    |  Max protobuf size
+----------------------+
| SHA256 Prefix (8B)   |  First 8 bytes of SHA256
+----------------------+
| Reserved (8B)        |  Reserved for future use
+----------------------+
| Zstd Dict Data       |  Raw Zstd dictionary
+----------------------+
```

## Troubleshooting

### Import Error

```python
ModuleNotFoundError: No module named 'zeroc'
```

**Solution:**
```bash
cd implementations/python
pip install -e .
```

### Dictionary Not Found

```python
FileNotFoundError: Dictionary not found: Order-1.0.0.zdict
```

**Solution:**
```bash
# Train dictionaries first
cd tools/dict-trainer
python train_dictionary.py --schema ecommerce.v1.Order --version 1.0.0
```

### Dictionary ID Mismatch

```python
ValueError: Dictionary ID mismatch: header says 0x12345678, calculated 0x87654321
```

**Cause:** Dictionary file is corrupted or modified.

**Solution:** Retrain the dictionary or download from CDN.

### Checksum Mismatch

```python
ValueError: Checksum mismatch: expected 0x12345678, got 0x87654321
```

**Cause:** Frame data is corrupted during transmission.

**Solution:** Check network transmission, retry request.

## Contributing

See main repository [CONTRIBUTING.md](../../CONTRIBUTING.md).

## License

See main repository [LICENSE](../../LICENSE).

## Related Documentation

- [Wire Format Specification](../../spec/WIRE_FORMAT.md)
- [Dictionary Format Specification](../../spec/DICTIONARY_FORMAT.md)
- [Protocol Specification](../../spec/PROTOCOL.md)
- [Repository Structure](../../spec/REPOSITORY_STRUCTURE.md)
