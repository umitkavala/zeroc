# ProtoZstd Dictionary Format Specification

**Version:** 1.0
**Status:** Draft
**Last Updated:** 2025-01-04

## 1. Overview

ProtoZstd dictionaries are Zstandard compression dictionaries with additional metadata for versioning, validation, and distribution. They enable high compression ratios (3-5x better than gzip) on small API payloads.

## 2. Dictionary File Format

### 2.1 File Structure

```
┌───────────────────────────────────────────────────┐
│                ProtoZstd Header                    │
│                   (132 bytes)                      │
├───────────────────────────────────────────────────┤
│               Zstd Dictionary Data                 │
│                (Variable size)                     │
└───────────────────────────────────────────────────┘
```

### 2.2 Header Structure (132 bytes)

```
 Offset  Size  Field                    Description
 ──────  ────  ─────                    ───────────
    0      8   Magic                    "PZSTDICT" (0x505A53544449 4354)
    8     12   Version                  SemVer (e.g., "1.2.0\0\0\0\0\0\0\0")
   20     64   Schema Name              Fully qualified proto message
   84      4   Dictionary ID (CRC32)    Unique identifier
   88      4   Training Sample Count    Number of samples used
   92      8   Created Timestamp        Unix timestamp (seconds)
  100      4   Compression Level        Zstd compression level used
  104      4   Dictionary Size          Size of Zstd dictionary data
  108      4   Min Protobuf Size        Minimum protobuf size (bytes)
  112      4   Max Protobuf Size        Maximum protobuf size (bytes)
  116      8   SHA256 (Part 1)          First 8 bytes of SHA256
  124      8   Reserved                 Future use (must be zeros)
```

All multi-byte integers in **network byte order (big-endian)**.

## 3. Field Specifications

### 3.1 Magic (8 bytes)

```
Value: "PZSTDICT" (ASCII)
Hex: 0x50 0x5A 0x53 0x54 0x44 0x49 0x43 0x54
Purpose: File format identification
```

**Validation:**
```python
MAGIC = b'PZSTDICT'
assert header[0:8] == MAGIC, "Not a ProtoZstd dictionary"
```

### 3.2 Version (12 bytes)

```
Format: SemVer string, NUL-padded
Example: "1.2.0\0\0\0\0\0\0\0"
Encoding: ASCII

Semantics:
  MAJOR: Breaking changes (incompatible schema)
  MINOR: Non-breaking changes (retraining, new fields)
  PATCH: Metadata/documentation updates
```

**Parsing:**
```python
version_str = header[8:20].rstrip(b'\0').decode('ascii')
major, minor, patch = version_str.split('.')
```

**Compatibility:**
- Same major version: Compatible (prefer higher minor)
- Different major version: Incompatible (require exact match)

### 3.3 Schema Name (64 bytes)

```
Format: Fully qualified protobuf message name
Example: "ecommerce.v1.Order\0\0\0..."
Encoding: ASCII, NUL-padded
Max Length: 63 characters + NUL terminator
```

**Examples:**
```
"ecommerce.v1.Order"
"iot.telemetry.v2.SensorReading"
"api.logging.v1.LogEntry"
```

**Purpose:**
- Identifies which protobuf schema this dictionary is for
- Prevents using wrong dictionary for wrong message type

### 3.4 Dictionary ID (4 bytes)

```
Format: CRC32 of Zstd dictionary data
Purpose: Unique identifier for this specific dictionary
Range: 0x00000001 to 0xFFFFFFFF (0 reserved for "no dictionary")
```

**Calculation:**
```python
import zlib

def calculate_dict_id(zstd_dict_data: bytes) -> int:
    """Calculate CRC32 of dictionary data."""
    crc = zlib.crc32(zstd_dict_data) & 0xFFFFFFFF
    # Ensure non-zero (0 means "no dictionary")
    return crc if crc != 0 else 0x00000001
```

**Usage:**
- Included in wire format header for dictionary verification
- Used for dictionary caching and lookup

### 3.5 Training Sample Count (4 bytes)

```
Format: Unsigned 32-bit integer
Range: 1 to 4,294,967,295
Typical: 1,000 to 100,000
```

**Purpose:**
- Indicates dictionary quality (more samples = better)
- Helps users decide if retraining is needed

**Recommendations:**
- Minimum: 1,000 samples
- Recommended: 10,000 samples
- Maximum practical: 100,000 samples (diminishing returns)

### 3.6 Created Timestamp (8 bytes)

```
Format: Unix timestamp (seconds since epoch)
Range: 0 to 2^63-1
Example: 1704067200 (2024-01-01 00:00:00 UTC)
```

**Purpose:**
- Track dictionary age
- Determine if retraining is needed
- Audit trail for dictionary management

### 3.7 Compression Level (4 bytes)

```
Format: Unsigned 32-bit integer
Range: 1 to 22 (Zstd compression levels)
Default: 3 (balanced)
Typical: 1-5
```

**Level Guidelines:**
| Level | Speed | Ratio | Use Case |
|-------|-------|-------|----------|
| 1 | Fast | Good | Latency-critical |
| 3 | Balanced | Better | Default recommendation |
| 5 | Slower | Best | Bandwidth-critical |
| 19-22 | Very slow | Marginal | Not recommended |

### 3.8 Dictionary Size (4 bytes)

```
Format: Unsigned 32-bit integer
Units: Bytes
Typical: 50KB - 200KB
Maximum: 2MB (practical limit)
```

**Size Recommendations:**
| Payload Size | Dict Size | Rationale |
|--------------|-----------|-----------|
| <500 bytes | 50KB | Small overhead |
| 500-2KB | 100KB | Balanced |
| 2KB-10KB | 200KB | Best compression |
| >10KB | 100KB | Diminishing returns |

### 3.9 Min/Max Protobuf Size (4 bytes each)

```
Format: Unsigned 32-bit integers
Purpose: Indicate expected payload size range
Units: Bytes
```

**Example:**
```
Min: 100 bytes (smallest training sample)
Max: 5000 bytes (largest training sample)
```

**Usage:**
- Detect if payload is outside expected range (may compress poorly)
- Decide whether to use dictionary or fallback

### 3.10 SHA256 Hash (8 bytes)

```
Format: First 8 bytes of SHA256 hash of entire dictionary
Purpose: Quick integrity check
Note: Full SHA256 should be distributed separately
```

**Calculation:**
```python
import hashlib

def calculate_sha256_prefix(dictionary_bytes: bytes) -> bytes:
    """Calculate first 8 bytes of SHA256."""
    full_hash = hashlib.sha256(dictionary_bytes).digest()
    return full_hash[:8]
```

**Usage:**
- Quick verification without full SHA256
- Sufficient for detecting corruption (not for security)

### 3.11 Reserved (8 bytes)

```
Format: 8 bytes of zeros
Purpose: Future extensions
Decoder behavior: MUST ignore
Encoder behavior: MUST write zeros
```

## 4. Zstd Dictionary Data

### 4.1 Format

Standard Zstandard dictionary as produced by `zstd --train` or `zstd.train_dictionary()`.

**Structure:**
```
┌─────────────────────────────┐
│  Zstd Dictionary Header     │  (magic, header)
├─────────────────────────────┤
│  Dictionary Tables          │  (Huffman, FSE, match)
├─────────────────────────────┤
│  Sample Data (optional)     │  (representative samples)
└─────────────────────────────┘
```

**Properties:**
- Self-contained (no external dependencies)
- Can be used directly by Zstd compressor/decompressor
- Optimized for specific data patterns

### 4.2 Training

**Process:**
```bash
# Collect samples
cat samples/*.proto.bin > all-samples.bin

# Train dictionary (using zstd CLI)
zstd --train -o dict.zdict --maxdict=102400 all-samples.bin

# Or using Python
import zstandard as zstd

samples = [...]  # List of bytes objects
dict_data = zstd.train_dictionary(102400, samples)
```

**Best Practices:**
1. Use 10,000+ representative samples
2. Include diverse examples (edge cases)
3. Exclude outliers (>3σ from mean size)
4. Normalize data (remove timestamps, IDs)
5. Validate compression ratio on test set

## 5. File Format Example

### 5.1 Complete Dictionary File

```hex
Offset  00 01 02 03 04 05 06 07  08 09 0A 0B 0C 0D 0E 0F  ASCII
──────────────────────────────────────────────────────────────────
0x0000  50 5A 53 54 44 49 43 54  31 2E 32 2E 30 00 00 00  PZSTDICT1.2.0...
0x0010  00 00 00 00 65 63 6F 6D  6D 65 72 63 65 2E 76 31  ....ecommerce.v1
0x0020  2E 4F 72 64 65 72 00 00  00 00 00 00 00 00 00 00  .Order..........
0x0030  00 00 00 00 00 00 00 00  00 00 00 00 00 00 00 00  ................
0x0040  00 00 00 00 00 00 00 00  00 00 00 00 1A 2B 3C 4D  .............+<M
0x0050  00 00 27 10 65 AB 12 34  00 00 00 03 00 01 90 00  ..'.e..4........
0x0060  00 00 00 64 00 00 13 88  A1 B2 C3 D4 E5 F6 07 08  ...d............
0x0070  00 00 00 00 00 00 00 00  [Zstd dict data follows]  ................

Breakdown:
0x00-07: Magic "PZSTDICT"
0x08-13: Version "1.2.0"
0x14-53: Schema "ecommerce.v1.Order"
0x54-57: Dict ID 0x1A2B3C4D
0x58-5B: Sample count 10000 (0x00002710)
0x5C-63: Timestamp 1704067200
0x64-67: Compression level 3
0x68-6B: Dict size 102400 bytes
0x6C-6F: Min proto size 100 bytes
0x70-73: Max proto size 5000 bytes
0x74-7B: SHA256 prefix
0x7C-83: Reserved (zeros)
0x84+  : Zstd dictionary data
```

## 6. Distribution Format

### 6.1 File Naming Convention

```
Format: {schema_name}-{version}.zdict

Examples:
ecommerce.Order-1.2.0.zdict
iot.Telemetry-2.0.0.zdict
api.LogEntry-1.0.0.zdict
```

### 6.2 Metadata Sidecar

**Filename:** `{dictionary}.meta.json`

```json
{
  "schema": "ecommerce.v1.Order",
  "version": "1.2.0",
  "dictionary_id": "0x1a2b3c4d",
  "created": "2024-01-01T00:00:00Z",
  "size": 102400,
  "sha256": "abc123def456...",
  "training": {
    "sample_count": 10000,
    "sample_source": "production-2024-01",
    "compression_level": 3,
    "min_size": 100,
    "max_size": 5000,
    "avg_size": 350
  },
  "performance": {
    "compression_ratio": 4.2,
    "encode_latency_p99_ms": 0.5,
    "decode_latency_p99_ms": 0.1
  },
  "compatibility": {
    "protocol_version": "1.0",
    "replaces": ["1.1.0"],
    "deprecated": false
  }
}
```

### 6.3 Checksum File

**Filename:** `{dictionary}.sha256`

```
abc123def456...  ecommerce.Order-1.2.0.zdict
```

## 7. Dictionary Lifecycle

### 7.1 Creation

```python
#!/usr/bin/env python3
"""Train and package ProtoZstd dictionary."""

import zstandard as zstd
import struct
import time
import zlib
import hashlib

def create_dictionary(
    samples: list[bytes],
    schema_name: str,
    version: str,
    dict_size: int = 102400,
    compression_level: int = 3
) -> bytes:
    """Create ProtoZstd dictionary from training samples."""

    # 1. Train Zstd dictionary
    zstd_dict = zstd.train_dictionary(dict_size, samples, level=compression_level)
    zstd_dict_data = bytes(zstd_dict)

    # 2. Calculate metadata
    dict_id = zlib.crc32(zstd_dict_data) & 0xFFFFFFFF
    dict_id = dict_id if dict_id != 0 else 0x00000001

    sample_sizes = [len(s) for s in samples]
    min_size = min(sample_sizes)
    max_size = max(sample_sizes)

    sha256_prefix = hashlib.sha256(zstd_dict_data).digest()[:8]

    # 3. Build header
    header = struct.pack(
        '>8s12s64sIIQIIIIQQ',
        b'PZSTDICT',                          # Magic
        version.encode('ascii').ljust(12, b'\0'),  # Version
        schema_name.encode('ascii').ljust(64, b'\0'),  # Schema
        dict_id,                              # Dictionary ID
        len(samples),                         # Sample count
        int(time.time()),                     # Created timestamp
        compression_level,                    # Compression level
        len(zstd_dict_data),                  # Dictionary size
        min_size,                             # Min protobuf size
        max_size,                             # Max protobuf size
        struct.unpack('>Q', sha256_prefix)[0],  # SHA256 prefix
        0                                     # Reserved
    )

    # 4. Combine header + dictionary
    return header + zstd_dict_data

# Example usage
samples = load_training_samples()
dictionary = create_dictionary(
    samples=samples,
    schema_name="ecommerce.v1.Order",
    version="1.2.0",
    dict_size=102400
)

with open("ecommerce.Order-1.2.0.zdict", "wb") as f:
    f.write(dictionary)
```

### 7.2 Loading

```python
def load_dictionary(filepath: str) -> tuple[dict, zstd.ZstdCompressionDict]:
    """Load ProtoZstd dictionary and metadata."""

    with open(filepath, 'rb') as f:
        data = f.read()

    # Parse header
    magic = data[0:8]
    if magic != b'PZSTDICT':
        raise ValueError("Invalid dictionary format")

    version = data[8:20].rstrip(b'\0').decode('ascii')
    schema_name = data[20:84].rstrip(b'\0').decode('ascii')

    dict_id, sample_count, created, compression_level, dict_size, \
    min_size, max_size, sha256_prefix, reserved = struct.unpack(
        '>IIQIIIIIQ', data[84:132]
    )

    # Extract Zstd dictionary data
    zstd_dict_data = data[132:]

    # Verify dictionary ID
    expected_dict_id = zlib.crc32(zstd_dict_data) & 0xFFFFFFFF
    if expected_dict_id != dict_id:
        raise ValueError("Dictionary ID mismatch")

    # Create Zstd dictionary object
    zstd_dict = zstd.ZstdCompressionDict(zstd_dict_data)

    # Return metadata and dictionary
    metadata = {
        'version': version,
        'schema_name': schema_name,
        'dictionary_id': dict_id,
        'sample_count': sample_count,
        'created': created,
        'compression_level': compression_level,
        'min_size': min_size,
        'max_size': max_size,
    }

    return metadata, zstd_dict
```

## 8. Distribution Protocol

### 8.1 CDN Structure

```
https://cdn.example.com/protozstd/
  ├── manifest.json                          # Catalog
  ├── dicts/
  │   ├── ecommerce.Order-1.2.0.zdict
  │   ├── ecommerce.Order-1.2.0.zdict.sha256
  │   ├── ecommerce.Order-1.2.0.meta.json
  │   ├── iot.Telemetry-2.0.0.zdict
  │   └── ...
  └── schemas/
      ├── ecommerce-v1.proto
      └── iot-v2.proto
```

### 8.2 Discovery API

```http
GET /protozstd/manifest.json HTTP/1.1
Host: cdn.example.com

HTTP/1.1 200 OK
Content-Type: application/json

{
  "version": "1.0",
  "dictionaries": [
    {
      "schema": "ecommerce.v1.Order",
      "version": "1.2.0",
      "dictionary_id": "0x1a2b3c4d",
      "url": "https://cdn.example.com/protozstd/dicts/ecommerce.Order-1.2.0.zdict",
      "sha256": "abc123...",
      "size": 102400,
      "created": "2024-01-01T00:00:00Z"
    }
  ]
}
```

### 8.3 Download and Verification

```python
import requests
import hashlib

def download_dictionary(url: str, expected_sha256: str) -> bytes:
    """Download and verify dictionary."""

    # Download
    response = requests.get(url)
    response.raise_for_status()
    dictionary = response.content

    # Verify checksum
    actual_sha256 = hashlib.sha256(dictionary).hexdigest()
    if actual_sha256 != expected_sha256:
        raise ValueError("Dictionary checksum mismatch")

    return dictionary
```

## 9. Validation

### 9.1 Required Checks

- [ ] Magic bytes are "PZSTDICT"
- [ ] Version is valid SemVer
- [ ] Schema name is non-empty and valid
- [ ] Dictionary ID matches CRC32 of Zstd data
- [ ] Sample count > 0
- [ ] Created timestamp is reasonable
- [ ] Compression level is 1-22
- [ ] Dictionary size matches actual Zstd data size
- [ ] Min size ≤ Max size
- [ ] SHA256 prefix matches (first 8 bytes)
- [ ] Reserved bytes are all zero
- [ ] Zstd dictionary data is valid

## 10. Best Practices

### 10.1 Training Data Selection

1. **Diversity**: Include variety of payloads
2. **Representativeness**: Match production distribution
3. **Volume**: 10,000+ samples recommended
4. **Freshness**: Retrain monthly with recent data
5. **Privacy**: Remove/anonymize PII before training

### 10.2 Version Management

1. **Semantic Versioning**: Follow SemVer strictly
2. **Backward Compatibility**: Support N-1 version
3. **Deprecation**: Mark old versions, remove after 6 months
4. **Testing**: Validate new dictionaries before deployment

### 10.3 Performance

1. **Size**: 50-200KB for optimal performance
2. **Level**: Use level 3 (balanced) for training
3. **Validation**: Test compression ratio on held-out set
4. **Monitoring**: Track compression metrics in production

---

**Document Version:** 1.0
**Last Updated:** 2025-01-04
