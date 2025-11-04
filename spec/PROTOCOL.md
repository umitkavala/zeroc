# ProtoZstd Protocol Specification

**Version:** 1.0
**Status:** Draft
**Last Updated:** 2025-01-04

## Abstract

ProtoZstd is a compression protocol optimized for API payloads, combining Protocol Buffers binary serialization with Zstandard dictionary compression. It achieves 4x better compression ratios than gzip with sub-millisecond latency through the use of pre-trained dictionaries tailored to specific data patterns.

## 1. Introduction

### 1.1 Motivation

Traditional API compression (gzip, deflate) suffers from poor compression ratios on small payloads (<10KB) due to:
- Overhead of JSON field names
- Generic compression without domain knowledge
- Header overhead proportional to payload size

ProtoZstd addresses these limitations through:
- Schema-based serialization (Protocol Buffers)
- Domain-specific dictionary training
- Efficient binary wire format
- Sub-millisecond compression/decompression

### 1.2 Goals

1. **High Compression Ratio**: 3-5x better than gzip for API payloads
2. **Low Latency**: <1ms compression/decompression on modern CPUs
3. **Backward Compatibility**: Graceful degradation to JSON+gzip
4. **Version Safety**: Safe evolution of schemas and dictionaries
5. **Multi-Language**: Implementations in Python, Java, Go, JS, C#

### 1.3 Non-Goals

- Compress large binary data (>10MB) - use streaming compression instead
- Replace Protocol Buffers - ProtoZstd builds on top of protobuf
- General-purpose compression - optimized for structured API data

## 2. Architecture

### 2.1 Components

```
┌─────────────────────────────────────────────────────┐
│                  Application Layer                   │
│              (JSON/Proto Messages)                   │
└──────────────────┬──────────────────────────────────┘
                   │
┌──────────────────▼──────────────────────────────────┐
│              ProtoZstd Encoder                       │
│  1. JSON → Proto (optional)                          │
│  2. Proto → Binary                                   │
│  3. Binary → Zstd (with dictionary)                  │
└──────────────────┬──────────────────────────────────┘
                   │
┌──────────────────▼──────────────────────────────────┐
│                 Wire Format                          │
│  [Header][Compressed Payload]                        │
└──────────────────┬──────────────────────────────────┘
                   │
                 Network
                   │
┌──────────────────▼──────────────────────────────────┐
│              ProtoZstd Decoder                       │
│  1. Wire → Header + Payload                          │
│  2. Zstd → Binary (with dictionary)                  │
│  3. Binary → Proto                                   │
│  4. Proto → JSON (optional)                          │
└─────────────────────────────────────────────────────┘
```

### 2.2 Layers

| Layer | Responsibility | Protocol |
|-------|----------------|----------|
| **Application** | Business logic | JSON/Proto messages |
| **Encoding** | Serialization | Protobuf |
| **Compression** | Size reduction | Zstandard + Dictionary |
| **Framing** | Wire format | ProtoZstd Wire Format |
| **Transport** | Delivery | HTTP, gRPC, WebSocket, etc. |

## 3. Protocol Flow

### 3.1 Capability Negotiation

#### 3.1.1 HTTP Headers

**Request:**
```http
POST /api/orders HTTP/1.1
Accept-Encoding: protozstd, gzip, identity
X-ProtoZstd-Version: 1.0
X-ProtoZstd-Dict-Version: 1.2.0
Content-Type: application/x-protobuf
Content-Encoding: protozstd
X-ProtoZstd-Schema: ecommerce.Order
```

**Response:**
```http
HTTP/1.1 200 OK
Content-Encoding: protozstd
X-ProtoZstd-Version: 1.0
X-ProtoZstd-Dict-Version: 1.2.0
X-ProtoZstd-Schema: ecommerce.OrderResponse
```

#### 3.1.2 Handshake Sequence

```
Client                          Server
  │                               │
  │  Accept-Encoding: protozstd   │
  ├──────────────────────────────>│
  │                               │
  │  X-ProtoZstd-Version: 1.0     │
  │  X-ProtoZstd-Dict-Version:... │
  ├──────────────────────────────>│
  │                               │
  │  Check dictionary available   │
  │                               ├─┐
  │                               │ │
  │                               │<┘
  │                               │
  │  Content-Encoding: protozstd  │
  │<──────────────────────────────┤
  │                               │
  │  OR fallback to gzip          │
  │  Content-Encoding: gzip       │
  │<──────────────────────────────┤
  │                               │
```

### 3.2 Compression Flow

```
1. Application Data (JSON/Proto)
   {"order_id": "ORD-123", ...}

2. Serialize to Protobuf Binary
   [0x0a 0x07 0x4f 0x52 0x44 0x2d 0x31 0x32 0x33 ...]

3. Compress with Zstd + Dictionary
   [0x28 0xb5 0x2f 0xfd ...]  (60% reduction)

4. Add ProtoZstd Header
   [Version][Flags][Dict ID][Schema Hash][Payload]

5. Transmit over network
```

### 3.3 Decompression Flow

```
1. Receive Wire Format
   [Header][Compressed Payload]

2. Parse Header
   - Validate protocol version
   - Extract dictionary ID
   - Extract schema hash
   - Check flags

3. Decompress with Zstd + Dictionary
   [0x0a 0x07 0x4f 0x52 0x44 ...]

4. Parse Protobuf
   Order {order_id: "ORD-123", ...}

5. Convert to JSON (optional)
   {"order_id": "ORD-123", ...}
```

## 4. Wire Format

See [WIRE_FORMAT.md](WIRE_FORMAT.md) for complete specification.

### 4.1 Header Structure (12 bytes)

```
 0                   1                   2                   3
 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|    Magic      |  Version      |     Flags     |   Reserved    |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                       Dictionary ID (32-bit)                   |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                     Schema Hash (32-bit CRC32)                 |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                    Compressed Payload (variable)               |
|                              ...                               |
```

### 4.2 Frame Format

```
┌────────────────────────────────────────┐
│  Magic Bytes (2 bytes): 0x50 0x5A      │  "PZ" (ProtoZstd)
├────────────────────────────────────────┤
│  Protocol Version (1 byte): 0x01       │  Version 1.0
├────────────────────────────────────────┤
│  Flags (1 byte)                        │  Bit flags (see below)
├────────────────────────────────────────┤
│  Dictionary ID (4 bytes)               │  CRC32 of dictionary
├────────────────────────────────────────┤
│  Schema Hash (4 bytes)                 │  CRC32 of .proto file
├────────────────────────────────────────┤
│  Compressed Payload Length (varint)    │  LEB128 encoded
├────────────────────────────────────────┤
│  Compressed Payload (N bytes)          │  Zstd compressed data
└────────────────────────────────────────┘
```

### 4.3 Flags

```
Bit 0: Compression Enabled (1 = compressed, 0 = identity)
Bit 1: Dictionary Used (1 = dictionary, 0 = no dictionary)
Bit 2: Checksum Included (1 = checksum, 0 = no checksum)
Bit 3: Reserved
Bit 4-7: Reserved for future use
```

## 5. Dictionary Management

### 5.1 Dictionary Format

Dictionaries are standard Zstandard dictionaries with metadata:

```
┌────────────────────────────────────┐
│  Magic: "ZSTD_DICT" (8 bytes)      │
├────────────────────────────────────┤
│  Version: SemVer (12 bytes)        │  e.g., "1.2.0\0\0\0\0\0\0\0"
├────────────────────────────────────┤
│  Schema: Name (64 bytes)           │  e.g., "ecommerce.Order"
├────────────────────────────────────┤
│  CRC32: Dictionary ID (4 bytes)    │  Unique identifier
├────────────────────────────────────┤
│  Training Samples: Count (4 bytes) │  Number of samples used
├────────────────────────────────────┤
│  Created: Unix timestamp (8 bytes) │  Creation time
├────────────────────────────────────┤
│  Reserved (32 bytes)               │  Future use
├────────────────────────────────────┤
│  Zstd Dictionary Data (N bytes)    │  Trained dictionary
└────────────────────────────────────┘

Total Header: 132 bytes
```

### 5.2 Dictionary Versioning

**SemVer 2.0 Semantics:**

- **Major (X.0.0)**: Breaking changes
  - Schema changes (field removal, type changes)
  - Incompatible with previous versions
  - Requires client update

- **Minor (1.X.0)**: Non-breaking changes
  - Schema additions (new optional fields)
  - Dictionary retraining with same schema
  - Backward compatible

- **Patch (1.2.X)**: Metadata/fixes
  - Checksum corrections
  - Documentation updates
  - No functional changes

### 5.3 Dictionary Discovery

#### 5.3.1 CDN-Based Discovery
```
https://cdn.example.com/protozstd/dicts/
  ├── manifest.json                    # Available dictionaries
  ├── ecommerce.Order-1.2.0.zdict      # Dictionary file
  ├── ecommerce.Order-1.2.0.zdict.sha256
  └── ecommerce.Order-1.2.0.meta.json  # Metadata
```

**manifest.json:**
```json
{
  "dictionaries": [
    {
      "schema": "ecommerce.Order",
      "version": "1.2.0",
      "crc32": "0x1a2b3c4d",
      "url": "https://cdn.example.com/.../ecommerce.Order-1.2.0.zdict",
      "sha256": "abc123...",
      "size": 102400,
      "created": "2025-01-01T00:00:00Z",
      "deprecated": false
    }
  ],
  "latest": {
    "ecommerce.Order": "1.2.0",
    "iot.Telemetry": "2.0.0"
  }
}
```

#### 5.3.2 HTTP Headers Method
```http
# Client requests dictionary info
GET /api/.well-known/protozstd/dictionaries HTTP/1.1

# Server responds with available dictionaries
HTTP/1.1 200 OK
Content-Type: application/json

{
  "dictionaries": [...],
  "latest": {...}
}
```

### 5.4 Dictionary Caching

**Client Caching Strategy:**
```
1. Check in-memory cache (LRU, max 5 dictionaries)
2. Check local disk cache (~/.protozstd/dicts/)
3. Download from CDN
4. Validate checksum (SHA-256)
5. Cache for 24 hours (configurable)
```

## 6. Version Negotiation

### 6.1 Protocol Version Compatibility

| Client Version | Server Version | Result |
|----------------|----------------|--------|
| 1.0 | 1.0 | ✅ Use ProtoZstd 1.0 |
| 1.1 | 1.0 | ✅ Downgrade to 1.0 |
| 1.0 | 1.1 | ✅ Use 1.0 (server supports) |
| 2.0 | 1.0 | ❌ Fallback to gzip |
| 1.0 | 2.0 | ❌ Fallback to gzip |

**Rule:** Use highest mutually supported MAJOR version. Within same MAJOR, use highest MINOR.

### 6.2 Dictionary Version Mismatch

#### 6.2.1 Client has newer dictionary
```
Client Dict: 1.3.0
Server Dict: 1.2.0

Action: Client uses 1.2.0 if cached, otherwise downloads 1.2.0
```

#### 6.2.2 Server has newer dictionary
```
Client Dict: 1.2.0
Server Dict: 1.3.0

Action: Server responds with X-ProtoZstd-Dict-Available: 1.3.0
        Client may upgrade on next request
```

#### 6.2.3 Incompatible major versions
```
Client Dict: 2.0.0
Server Dict: 1.2.0

Action: Fallback to gzip or reject with 406 Not Acceptable
```

### 6.3 Fallback Mechanism

**Priority Order:**
1. **ProtoZstd** (preferred)
2. **Protobuf + gzip**
3. **JSON + gzip**
4. **JSON + identity**

**Trigger Conditions for Fallback:**
- Dictionary not available
- Protocol version mismatch
- Compression error
- Client doesn't support ProtoZstd
- Server configuration (disable compression)

## 7. Error Handling

### 7.1 Error Codes

| Code | Name | Description | Recovery |
|------|------|-------------|----------|
| 0x00 | SUCCESS | No error | N/A |
| 0x01 | UNSUPPORTED_VERSION | Protocol version not supported | Fallback to gzip |
| 0x02 | DICTIONARY_NOT_FOUND | Dictionary ID not found | Download or fallback |
| 0x03 | DECOMPRESSION_FAILED | Zstd decompression error | Retry or fallback |
| 0x04 | INVALID_HEADER | Malformed header | Reject request |
| 0x05 | PAYLOAD_TOO_LARGE | Exceeds size limit | Reject request |
| 0x06 | DECOMPRESSION_BOMB | Decompressed size exceeds limit | Reject request |
| 0x07 | SCHEMA_MISMATCH | Schema hash doesn't match | Update schema |
| 0x08 | CHECKSUM_FAILED | Data corruption detected | Retry or reject |

### 7.2 Error Response Format

**HTTP Status Codes:**
```
400 Bad Request: Invalid header, malformed data
406 Not Acceptable: Unsupported version, no compatible encoding
413 Payload Too Large: Exceeds size limits
500 Internal Server Error: Server-side compression failure
```

**Error Header:**
```http
HTTP/1.1 406 Not Acceptable
X-ProtoZstd-Error: UNSUPPORTED_VERSION
X-ProtoZstd-Error-Detail: Client version 2.0 not supported, max 1.0
Content-Type: application/json

{
  "error": "compression_not_supported",
  "message": "ProtoZstd version 2.0 not supported",
  "supported_versions": ["1.0"],
  "supported_encodings": ["gzip", "identity"]
}
```

## 8. Security Considerations

### 8.1 Decompression Bombs

**Protection:**
- Limit compressed size (default: 10MB)
- Limit decompressed size (default: 50MB)
- Ratio check: reject if decompressed > 100x compressed
- Timeout on decompression (default: 1 second)

### 8.2 Dictionary Poisoning

**Protection:**
- Verify dictionary SHA-256 checksum
- Sign dictionaries (optional): ECDSA or RSA signature
- Use HTTPS for dictionary download
- Pin dictionary hashes in client configuration

### 8.3 Resource Exhaustion

**Protection:**
- Limit number of cached dictionaries (default: 5)
- Limit dictionary size (default: 500KB)
- Rate limit dictionary downloads
- LRU eviction for dictionary cache

### 8.4 Information Disclosure

**Considerations:**
- Dictionary training data may leak patterns
- Use anonymized/synthetic data for training
- Don't include PII in dictionary metadata
- Schema hashes reveal message structure

## 9. Performance Characteristics

### 9.1 Expected Performance

| Metric | Target | Typical |
|--------|--------|---------|
| Compression Ratio | >3x vs gzip | 3.5-4.5x |
| Compression Latency (p99) | <1ms | 0.5-2ms |
| Decompression Latency (p99) | <1ms | 0.1-0.5ms |
| Dictionary Size | <500KB | 100-200KB |
| Memory Usage | <100MB | 50-75MB |

### 9.2 Payload Size Recommendations

| Payload Size | Recommendation |
|--------------|----------------|
| <100 bytes | Identity (no compression) |
| 100-1KB | ProtoZstd (best ratio) |
| 1KB-10KB | ProtoZstd (balanced) |
| 10KB-100KB | ProtoZstd or gzip |
| >100KB | Streaming compression |

## 10. Implementation Requirements

### 10.1 Mandatory Features

- ✅ Protocol version 1.0 support
- ✅ Zstd compression/decompression
- ✅ Dictionary loading and caching
- ✅ Wire format encoding/decoding
- ✅ Fallback to gzip
- ✅ Error handling per spec

### 10.2 Optional Features

- ⬜ Dictionary auto-update
- ⬜ Compression level tuning
- ⬜ Streaming compression
- ⬜ Checksum verification
- ⬜ Dictionary signatures

### 10.3 Quality Requirements

- Unit test coverage >80%
- Integration tests with reference implementation
- Benchmark suite for regression testing
- Fuzz testing for security
- Cross-language compatibility tests

## 11. Interoperability

### 11.1 Reference Implementation

Python implementation serves as reference for:
- Wire format encoding/decoding
- Dictionary format
- Error handling
- Test vectors

### 11.2 Test Vectors

Provided in `test-data/golden/`:
- Uncompressed payloads
- Compressed payloads
- Expected compression ratios
- Error cases

### 11.3 Compatibility Matrix

| Feature | Python | Java | Go | JS | C# |
|---------|--------|------|----|----|-----|
| Protocol 1.0 | ✅ | ✅ | ✅ | ✅ | ✅ |
| Dictionary cache | ✅ | ✅ | ✅ | ✅ | ✅ |
| Fallback to gzip | ✅ | ✅ | ✅ | ✅ | ✅ |
| HTTP integration | ✅ | ✅ | ✅ | ✅ | ✅ |
| gRPC integration | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ |

## 12. Future Considerations

### 12.1 Protocol v2.0 Features

- Streaming compression for large payloads
- Multiple compression algorithms (LZ4, Brotli)
- Compression level negotiation
- Batch compression (multiple messages)
- Push-based dictionary updates

### 12.2 Extension Points

- Custom flags (bits 4-7)
- Reserved header bytes (for future fields)
- Metadata extensibility
- Plugin architecture for custom compressors

## Appendix A: Examples

See [examples/](examples/) directory for complete examples.

## Appendix B: References

- [RFC 7932](https://tools.ietf.org/html/rfc7932) - Brotli Compression
- [RFC 1952](https://tools.ietf.org/html/rfc1952) - GZIP file format
- [Zstandard Specification](https://github.com/facebook/zstd/blob/dev/doc/zstd_compression_format.md)
- [Protocol Buffers](https://developers.google.com/protocol-buffers)

## Appendix C: Glossary

- **Dictionary**: Pre-trained compression dictionary for Zstandard
- **Schema Hash**: CRC32 of Protocol Buffer .proto file
- **Wire Format**: Binary encoding for network transmission
- **Frame**: Single unit of compressed data
- **Fallback**: Alternative encoding when ProtoZstd unavailable

---

**Document History:**
- v1.0 (2025-01-04): Initial specification
