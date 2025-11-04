# Zeroc Implementations

Multi-language implementations of the Zeroc compression protocol.

## Overview

This directory contains implementations of Zeroc in various programming languages, all conforming to the same protocol specification.

## Implementation Status

| Language | Status | Package | Docs |
|----------|--------|---------|------|
| **Python** | ✅ Complete | `umitkavala-zeroc` | [README](python/README.md) |
| **Java** | 🚧 Skeleton | `io.github.umitkavala:zeroc` | [README](java/README.md) |
| **Go** | 🚧 Skeleton | `github.com/umitkavala/zeroc/implementations/go/zeroc` | [README](go/README.md) |
| **JavaScript** | 🚧 Skeleton | `@umitkavala/zeroc` | [README](javascript/README.md) |
| **C#** | 🚧 Skeleton | `Umitkavala.Zeroc` | [README](csharp/README.md) |

## Python (Reference Implementation)

**Status:** ✅ Complete

The Python implementation is the reference implementation with full functionality:

- Complete wire format encoder/decoder
- Dictionary loader with validation
- CRC32C checksum support
- Dictionary caching
- Comprehensive test suite
- Type annotations

### Quick Start

```bash
cd implementations/python
pip install -e .
```

```python
from zeroc import DictionaryLoader, encode_frame, decode_frame

# Load dictionary
loader = DictionaryLoader()
metadata, dict_obj = loader.load("../../dictionaries/formats/Order-1.0.0.zdict")

# Encode
compressor = loader.get_compressor("../../dictionaries/formats/Order-1.0.0.zdict")
frame = encode_frame(proto_bytes, metadata['dictionary_id'], compress=True, compressor=compressor)

# Decode
compressed, frame_meta = decode_frame(frame)
decompressor = loader.get_decompressor("../../dictionaries/formats/Order-1.0.0.zdict")
proto_bytes = decompressor.decompress(compressed)
```

See [Python README](python/README.md) for full documentation.

## Java

**Status:** 🚧 Skeleton

Maven/Gradle project with planned features:
- Wire format encoder/decoder
- Dictionary loader
- Thread-safe operations
- Full test coverage

**Requirements:** Java 21 (LTS), Maven 3.9+

### Structure

```
java/
├── pom.xml
├── src/main/java/com/zeroc/
└── src/test/java/com/zeroc/
```

See [Java README](java/README.md) for planned API.

## Go

**Status:** 🚧 Skeleton

Go module with planned features:
- Wire format encoder/decoder
- Dictionary loader
- Goroutine-safe operations
- Zero-allocation optimizations

**Requirements:** Go 1.22+

### Structure

```
go/
├── go.mod
├── zeroc/
│   ├── wire_format.go
│   ├── dictionary.go
│   └── constants.go
└── examples/
```

See [Go README](go/README.md) for planned API.

## JavaScript/TypeScript

**Status:** 🚧 Skeleton

NPM package with planned features:
- Wire format encoder/decoder
- Dictionary loader
- Browser and Node.js support
- TypeScript type definitions
- WASM integration for zstd

**Requirements:** Node.js 20+ (LTS), TypeScript 5.0+

### Structure

```
javascript/
├── package.json
├── tsconfig.json
├── src/
│   ├── wire-format.ts
│   ├── dictionary-loader.ts
│   └── constants.ts
└── test/
```

See [JavaScript README](javascript/README.md) for planned API.

## C#

**Status:** 🚧 Skeleton

.NET library with planned features:
- Wire format encoder/decoder
- Dictionary loader
- Thread-safe operations
- Span<T> and Memory<T> support
- ASP.NET Core middleware

**Requirements:** .NET 8.0 (LTS), C# 12

### Structure

```
csharp/
├── Zeroc.sln
├── src/Zeroc/
│   ├── Zeroc.csproj
│   ├── WireFormat.cs
│   └── Constants.cs
└── test/Zeroc.Tests/
```

See [C# README](csharp/README.md) for planned API.

## Protocol Compliance

All implementations must comply with:

- [Wire Format Specification](../spec/WIRE_FORMAT.md)
- [Dictionary Format Specification](../spec/DICTIONARY_FORMAT.md)
- [Protocol Specification](../spec/PROTOCOL.md)

## Cross-Language Testing

Test vectors are provided in `../test-data/golden/` for verifying cross-language compatibility:

```
test-data/golden/
├── frame-identity.bin          # Uncompressed frame
├── frame-compressed.bin        # Compressed frame (no dict)
├── frame-compressed-dict.bin   # Compressed with dictionary
└── frame-checksum.bin          # Frame with CRC32C checksum
```

Each implementation should:
1. Successfully decode all golden test frames
2. Produce byte-identical output when encoding with same parameters
3. Pass cross-language round-trip tests

## Contributing New Languages

To add support for a new language:

1. **Create directory structure:**
   ```
   implementations/<language>/
   ├── README.md
   ├── <build-config>  (e.g., Cargo.toml, CMakeLists.txt)
   ├── src/
   │   ├── wire_format.<ext>
   │   ├── dictionary.<ext>
   │   └── constants.<ext>
   └── tests/
   ```

2. **Implement core functionality:**
   - Wire format encoder/decoder
   - Dictionary loader with validation
   - Varint encoding/decoding (LEB128)
   - CRC32C checksum validation

3. **Add tests:**
   - Unit tests for all core functions
   - Integration tests with golden test vectors
   - Round-trip tests (encode → decode → verify)

4. **Update this README:**
   - Add language to status table
   - Link to language-specific README

5. **Add CI/CD:**
   - Add workflow in `.github/workflows/<language>.yml`
   - Test on multiple OS (Linux, macOS, Windows)
   - Generate coverage reports

## Development Guidelines

### API Consistency

All implementations should provide similar APIs:

**Encoding:**
```
encode_frame(proto_bytes, dictionary_id, schema_hash, compress, checksum, compressor)
  → frame_bytes
```

**Decoding:**
```
decode_frame(frame_bytes)
  → (payload_bytes, metadata)
```

**Dictionary Loading:**
```
loader = DictionaryLoader()
metadata, dict_obj = loader.load(filepath)
compressor = loader.get_compressor(filepath, level)
decompressor = loader.get_decompressor(filepath)
```

### Error Handling

All implementations should throw/return errors for:
- `InvalidMagic`: Magic bytes mismatch
- `UnsupportedVersion`: Protocol version not supported
- `ChecksumMismatch`: CRC32C validation failed
- `TruncatedFrame`: Incomplete frame data
- `InvalidDictionary`: Dictionary format invalid
- `DictionaryIDMismatch`: Dictionary CRC32 mismatch

### Performance Targets

Implementations should target:

| Operation | Latency | Throughput |
|-----------|---------|------------|
| Encode (no dict) | <1ms | >1M ops/sec |
| Encode (with dict) | <2ms | >500K ops/sec |
| Decode (no dict) | <0.5ms | >2M ops/sec |
| Decode (with dict) | <1ms | >1M ops/sec |

### Thread Safety

All implementations should be thread-safe:
- Dictionary loader with concurrent caching
- Immutable dictionary objects after loading
- Reusable compressor/decompressor instances (where supported)

## Benchmarking

Each implementation should include benchmarks:

```bash
# Python
cd python && pytest benchmarks/ --benchmark-only

# Java
cd java && mvn test -P benchmark

# Go
cd go && go test -bench=. -benchmem

# JavaScript
cd javascript && npm run bench

# C#
cd csharp && dotnet run -c Release --project Benchmarks
```

## Documentation

Each implementation must have:

1. **README.md** with:
   - Installation instructions
   - Quick start example
   - Full API documentation
   - Performance characteristics
   - Build and test instructions

2. **Examples** directory with:
   - Basic usage example
   - Dictionary compression example
   - Error handling example
   - Integration example (HTTP client/server)

3. **API Documentation:**
   - Python: Docstrings
   - Java: Javadoc
   - Go: godoc
   - JavaScript: TSDoc
   - C#: XML documentation

## License

See main repository [LICENSE](../LICENSE).

## Related Documentation

- [Main README](../README.md)
- [Protocol Specification](../spec/PROTOCOL.md)
- [Wire Format Specification](../spec/WIRE_FORMAT.md)
- [Dictionary Format Specification](../spec/DICTIONARY_FORMAT.md)
- [Repository Structure](../spec/REPOSITORY_STRUCTURE.md)
