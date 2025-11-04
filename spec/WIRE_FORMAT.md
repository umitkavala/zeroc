# ProtoZstd Wire Format Specification

**Version:** 1.0
**Status:** Draft
**Last Updated:** 2025-01-04

## 1. Overview

The ProtoZstd wire format defines the binary layout for compressed Protocol Buffer messages transmitted over a network. It is designed for:

- **Compact representation** - Minimal overhead (12-14 bytes)
- **Fast parsing** - Fixed-size header for quick validation
- **Extensibility** - Reserved fields for future features
- **Self-describing** - Includes version and schema information

## 2. Frame Structure

### 2.1 Complete Frame

```
+------------------+------------------+
|      Header      | Compressed Payload|
|    (12 bytes)    |   (Variable)     |
+------------------+------------------+
```

### 2.2 Header Layout (12 bytes)

```
 0                   1                   2                   3
 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|  Magic (0x50) |  Magic (0x5A) |    Version    |     Flags     |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                       Dictionary ID (32-bit)                   |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                     Schema Hash (32-bit CRC32)                 |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
```

**All multi-byte integers are in network byte order (big-endian).**

## 3. Header Fields

### 3.1 Magic Bytes (2 bytes)

```
Offset: 0-1
Value: 0x50 0x5A (ASCII "PZ" for ProtoZstd)
Purpose: Quick format identification
```

**Rationale:** Allows receivers to quickly reject non-ProtoZstd data without parsing further.

**Implementation:**
```python
MAGIC_BYTES = b'PZ'  # 0x50 0x5A
assert header[0:2] == MAGIC_BYTES, "Invalid magic bytes"
```

### 3.2 Protocol Version (1 byte)

```
Offset: 2
Format: Major.Minor encoded as 0xMM (Major*16 + Minor)
Range: 0x10 (v1.0) to 0xFF (v15.15)
```

**Examples:**
- `0x10` = Protocol v1.0
- `0x11` = Protocol v1.1
- `0x20` = Protocol v2.0

**Decoding:**
```python
major = version >> 4
minor = version & 0x0F
```

**Version Compatibility:**
- Same major version: Compatible (use lowest minor)
- Different major version: Incompatible (fallback required)

### 3.3 Flags (1 byte)

```
Offset: 3
Format: 8 bits, LSB first

Bit 0: COMPRESSION_ENABLED
  0 = Identity (no compression)
  1 = Zstd compression

Bit 1: DICTIONARY_USED
  0 = No dictionary (plain zstd)
  1 = Dictionary compression

Bit 2: CHECKSUM_INCLUDED
  0 = No checksum
  1 = CRC32C checksum appended

Bit 3: RESERVED
Bit 4: RESERVED
Bit 5: RESERVED
Bit 6: RESERVED
Bit 7: RESERVED
```

**Flag Constants:**
```python
FLAG_COMPRESSION_ENABLED = 0x01  # 0b00000001
FLAG_DICTIONARY_USED     = 0x02  # 0b00000010
FLAG_CHECKSUM_INCLUDED   = 0x04  # 0b00000100
```

**Usage:**
```python
# Set flags
flags = FLAG_COMPRESSION_ENABLED | FLAG_DICTIONARY_USED

# Check flags
is_compressed = bool(flags & FLAG_COMPRESSION_ENABLED)
uses_dict = bool(flags & FLAG_DICTIONARY_USED)
has_checksum = bool(flags & FLAG_CHECKSUM_INCLUDED)
```

### 3.4 Dictionary ID (4 bytes)

```
Offset: 4-7
Format: CRC32 of dictionary file
Purpose: Identifies specific dictionary version
Special: 0x00000000 = No dictionary
```

**Calculation:**
```python
import zlib

def calculate_dict_id(dictionary_bytes: bytes) -> int:
    """Calculate CRC32 of dictionary data."""
    return zlib.crc32(dictionary_bytes) & 0xFFFFFFFF
```

**Usage:**
- Client includes expected dictionary ID in header
- Server validates it has matching dictionary
- If mismatch, fallback to gzip or reject

### 3.5 Schema Hash (4 bytes)

```
Offset: 8-11
Format: CRC32 of .proto file
Purpose: Detect schema version mismatches
```

**Calculation:**
```python
def calculate_schema_hash(proto_file_content: str) -> int:
    """Calculate CRC32 of normalized .proto file."""
    # Normalize: remove comments and whitespace
    normalized = normalize_proto(proto_file_content)
    return zlib.crc32(normalized.encode('utf-8')) & 0xFFFFFFFF
```

**Normalization Rules:**
1. Remove comments (// and /* */)
2. Remove leading/trailing whitespace
3. Collapse multiple spaces to single space
4. Sort field declarations by field number
5. Convert to UTF-8

## 4. Payload Format

### 4.1 Payload Structure

```
┌─────────────────────────────────────┐
│  Payload Length (varint)            │  Optional (for framing)
├─────────────────────────────────────┤
│  Compressed Data (N bytes)          │  Zstd compressed protobuf
├─────────────────────────────────────┤
│  Checksum (4 bytes)                 │  Optional (if flag set)
└─────────────────────────────────────┘
```

### 4.2 Payload Length

**Format:** LEB128 variable-length integer (protobuf varint encoding)

**Encoding:**
```python
def encode_varint(value: int) -> bytes:
    """Encode integer as LEB128 varint."""
    result = bytearray()
    while value > 0x7F:
        result.append((value & 0x7F) | 0x80)
        value >>= 7
    result.append(value & 0x7F)
    return bytes(result)
```

**Decoding:**
```python
def decode_varint(data: bytes) -> tuple[int, int]:
    """Decode LEB128 varint, return (value, bytes_consumed)."""
    result = 0
    shift = 0
    pos = 0
    while True:
        byte = data[pos]
        result |= (byte & 0x7F) << shift
        pos += 1
        if not (byte & 0x80):
            break
        shift += 7
    return result, pos
```

**Examples:**
- `0` → `0x00` (1 byte)
- `127` → `0x7F` (1 byte)
- `128` → `0x80 0x01` (2 bytes)
- `300` → `0xAC 0x02` (2 bytes)
- `100000` → `0xA0 0x8D 0x06` (3 bytes)

### 4.3 Compressed Data

**Format:** Standard Zstandard frame

**Properties:**
- Must be valid Zstd frame
- May use dictionary (ID in header)
- Default compression level: 3
- No custom Zstd headers (handled by library)

### 4.4 Checksum (Optional)

```
Format: CRC32C (Castagnoli)
Size: 4 bytes
Position: After compressed data
Included: Only if FLAG_CHECKSUM_INCLUDED is set
```

**Calculation:**
```python
import crc32c

def calculate_checksum(data: bytes) -> int:
    """Calculate CRC32C checksum."""
    return crc32c.crc32c(data)
```

**Verification:**
```python
expected_checksum = struct.unpack('>I', checksum_bytes)[0]
actual_checksum = calculate_checksum(compressed_data)
assert expected_checksum == actual_checksum, "Checksum mismatch"
```

## 5. Complete Frame Examples

### 5.1 Minimal Frame (Identity, No Dictionary)

```
Hex dump:
50 5A 10 00 00 00 00 00 00 00 00 00  [Header: 12 bytes]
0A 07 4F 52 44 2D 31 32 33           [Payload: 9 bytes]

Breakdown:
50 5A        Magic "PZ"
10           Protocol v1.0
00           Flags: identity, no dict, no checksum
00 00 00 00  Dictionary ID: 0 (none)
00 00 00 00  Schema Hash: 0 (unknown)
0A 07...     Protobuf payload (uncompressed)
```

### 5.2 Compressed with Dictionary

```
Hex dump:
50 5A 10 03 1A 2B 3C 4D AB CD EF 12  [Header: 12 bytes]
09                                   [Payload length: 9]
28 B5 2F FD 60 02 00 11 00 00        [Zstd frame: 10 bytes]

Breakdown:
50 5A        Magic "PZ"
10           Protocol v1.0
03           Flags: compressed + dictionary
1A 2B 3C 4D  Dictionary ID: 0x1A2B3C4D
AB CD EF 12  Schema Hash: 0xABCDEF12
09           Varint: payload length = 9
28 B5...     Zstd compressed data
```

### 5.3 With Checksum

```
Hex dump:
50 5A 10 07 1A 2B 3C 4D AB CD EF 12  [Header: 12 bytes]
09                                   [Payload length: 9]
28 B5 2F FD 60 02 00 11 00 00        [Zstd frame: 10 bytes]
DE AD BE EF                          [Checksum: 4 bytes]

Breakdown:
50 5A        Magic "PZ"
10           Protocol v1.0
07           Flags: compressed + dict + checksum
1A 2B 3C 4D  Dictionary ID: 0x1A2B3C4D
AB CD EF 12  Schema Hash: 0xABCDEF12
09           Varint: payload length = 9
28 B5...     Zstd compressed data
DE AD BE EF  CRC32C checksum
```

## 6. Encoding Algorithm

```python
def encode_frame(
    proto_bytes: bytes,
    dictionary_id: int = 0,
    schema_hash: int = 0,
    compress: bool = True,
    checksum: bool = False,
    compressor: Optional[zstd.ZstdCompressor] = None
) -> bytes:
    """Encode protobuf as ProtoZstd frame."""

    # 1. Compress payload (if enabled)
    if compress and compressor:
        compressed = compressor.compress(proto_bytes)
        flags = FLAG_COMPRESSION_ENABLED
        if dictionary_id > 0:
            flags |= FLAG_DICTIONARY_USED
    else:
        compressed = proto_bytes
        flags = 0

    # 2. Add checksum (if enabled)
    if checksum:
        flags |= FLAG_CHECKSUM_INCLUDED
        checksum_value = calculate_checksum(compressed)
        checksum_bytes = struct.pack('>I', checksum_value)
    else:
        checksum_bytes = b''

    # 3. Build header
    header = struct.pack(
        '>2sBBII',  # Magic, Version, Flags, DictID, SchemaHash
        MAGIC_BYTES,
        0x10,  # Protocol v1.0
        flags,
        dictionary_id,
        schema_hash
    )

    # 4. Build frame
    payload_length = encode_varint(len(compressed))
    return header + payload_length + compressed + checksum_bytes
```

## 7. Decoding Algorithm

```python
def decode_frame(frame: bytes) -> tuple[bytes, dict]:
    """Decode ProtoZstd frame to protobuf bytes and metadata."""

    # 1. Parse header
    if len(frame) < 12:
        raise ValueError("Frame too short")

    magic, version, flags, dict_id, schema_hash = struct.unpack(
        '>2sBBII', frame[0:12]
    )

    # 2. Validate magic
    if magic != MAGIC_BYTES:
        raise ValueError(f"Invalid magic: {magic!r}")

    # 3. Check version
    major = version >> 4
    if major != 1:
        raise ValueError(f"Unsupported protocol version: {major}")

    # 4. Parse payload length
    payload_length, varint_size = decode_varint(frame[12:])

    # 5. Extract compressed data
    payload_start = 12 + varint_size
    payload_end = payload_start + payload_length
    compressed = frame[payload_start:payload_end]

    # 6. Verify checksum (if present)
    if flags & FLAG_CHECKSUM_INCLUDED:
        expected_checksum = struct.unpack('>I', frame[payload_end:payload_end+4])[0]
        actual_checksum = calculate_checksum(compressed)
        if expected_checksum != actual_checksum:
            raise ValueError("Checksum mismatch")

    # 7. Decompress (if compressed)
    if flags & FLAG_COMPRESSION_ENABLED:
        # Use dictionary if specified
        if flags & FLAG_DICTIONARY_USED:
            decompressor = get_decompressor(dict_id)
        else:
            decompressor = zstd.ZstdDecompressor()
        proto_bytes = decompressor.decompress(compressed)
    else:
        proto_bytes = compressed

    # 8. Return protobuf bytes and metadata
    metadata = {
        'version': version,
        'flags': flags,
        'dictionary_id': dict_id,
        'schema_hash': schema_hash,
        'compressed_size': len(compressed),
        'uncompressed_size': len(proto_bytes)
    }

    return proto_bytes, metadata
```

## 8. Size Calculations

### 8.1 Overhead Analysis

```
Fixed Overhead:
  Header: 12 bytes

Variable Overhead:
  Payload length varint: 1-5 bytes (typical: 1-2 bytes)
  Checksum (optional): 4 bytes

Minimum Frame Size:
  12 + 1 + 1 = 14 bytes (1-byte payload)

Typical Overhead:
  12 + 1 + 0 = 13 bytes (no checksum)
  12 + 2 + 0 = 14 bytes (payload 128-16383 bytes)
  12 + 1 + 4 = 17 bytes (with checksum)
```

### 8.2 Compression Efficiency

```
Example: 1000-byte protobuf payload

Without ProtoZstd (JSON + gzip):
  Raw JSON: 2500 bytes
  Gzipped: 800 bytes
  Overhead: gzip header ~18 bytes
  Total: ~818 bytes

With ProtoZstd:
  Protobuf: 1000 bytes
  Compressed: 250 bytes
  ProtoZstd overhead: 13 bytes
  Total: ~263 bytes

Improvement: 818 / 263 = 3.1x smaller
```

## 9. Validation Rules

### 9.1 Encoder MUST

1. Set magic bytes to `0x50 0x5A`
2. Use network byte order (big-endian)
3. Set valid protocol version
4. Set flags correctly based on compression/dictionary/checksum
5. Include correct dictionary ID if using dictionary
6. Calculate schema hash correctly
7. Produce valid Zstd frames
8. Include checksum if FLAG_CHECKSUM_INCLUDED is set

### 9.2 Decoder MUST

1. Validate magic bytes
2. Check protocol version compatibility
3. Verify dictionary availability if FLAG_DICTIONARY_USED
4. Verify checksum if FLAG_CHECKSUM_INCLUDED
5. Enforce size limits (compressed and decompressed)
6. Handle invalid frames gracefully
7. Support fallback to alternative encodings

## 10. Future Extensions

### 10.1 Reserved Fields

- **Flags bits 3-7**: Reserved for future use
- **Decoder behavior**: MUST ignore unknown flags
- **Encoder behavior**: MUST set reserved bits to 0

### 10.2 Potential Future Flags

```
Bit 3: STREAMING_MODE (for large payloads)
Bit 4: ENCRYPTION_ENABLED (payload is encrypted)
Bit 5: CUSTOM_METADATA (additional metadata follows header)
Bit 6-7: Reserved
```

## 11. Test Vectors

See `test-data/wire-format/` for complete test vectors.

### 11.1 Valid Frames

```
test-vectors/valid-minimal.bin          # Minimal frame
test-vectors/valid-compressed.bin       # With compression
test-vectors/valid-dictionary.bin       # With dictionary
test-vectors/valid-checksum.bin         # With checksum
test-vectors/valid-large.bin            # Large payload (>64KB)
```

### 11.2 Invalid Frames

```
test-vectors/invalid-magic.bin          # Wrong magic bytes
test-vectors/invalid-version.bin        # Unsupported version
test-vectors/invalid-checksum.bin       # Checksum mismatch
test-vectors/invalid-truncated.bin      # Truncated frame
test-vectors/invalid-bomb.bin           # Decompression bomb
```

## 12. Implementation Checklist

- [ ] Encode/decode header correctly
- [ ] Support all flag combinations
- [ ] Validate magic bytes
- [ ] Check protocol version compatibility
- [ ] Handle dictionary ID correctly
- [ ] Calculate schema hash
- [ ] Encode/decode varint payload length
- [ ] Compress/decompress with Zstd
- [ ] Verify checksums (if enabled)
- [ ] Enforce size limits
- [ ] Handle invalid frames gracefully
- [ ] Pass all test vectors

---

**Document Version:** 1.0
**Compatible Protocol Version:** 1.0
**Last Updated:** 2025-01-04
