# Changelog

All notable changes to the Zeroc Python implementation will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2024-11-04

### Added
- Initial release of Zeroc Python reference implementation
- Wire format encoder/decoder supporting Protocol v1.0
- Dictionary loader with validation and caching
- CRC32C checksum support for data integrity
- LEB128 varint encoding/decoding
- Compression using Zstandard with trained dictionaries
- Type annotations for all public APIs
- Comprehensive documentation and specifications

### Features
- **Wire Format**: 12-byte header + varint length + payload + optional checksum
- **Dictionary Format**: 132-byte header with metadata + zstd dictionary data
- **Compression**: 2.35-3.22x better than JSON+gzip
- **Performance**: Sub-millisecond encode/decode latency
- **Multi-platform**: Tested on Linux, macOS, and Windows
- **Python Support**: Python 3.8, 3.9, 3.10, 3.11, 3.12

### Benchmarks
- Orders (complex nested): 75.8B vs 244B JSON+gzip (3.22x improvement)
- Product Views (small events): 46.5B vs 109.3B JSON+gzip (2.35x improvement)
- Search Requests (medium): 47.1B vs 119.8B JSON+gzip (2.54x improvement)

### Documentation
- Protocol specification (65 pages)
- Wire format specification (40 pages)
- Dictionary format specification (45 pages)
- Production deployment guide
- Comprehensive benchmark suite

### Dependencies
- zstandard >= 0.21.0
- crc32c >= 2.3

[1.0.0]: https://github.com/umitkavala/zeroc/releases/tag/v1.0.0
