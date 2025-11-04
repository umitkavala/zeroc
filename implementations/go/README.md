# Zeroc Go Implementation

Go implementation of the Zeroc compression protocol.

## Status

🚧 **Under Development** - Skeleton implementation

## Planned Features

- ✅ Wire format encoder/decoder
- ✅ Dictionary loader with validation
- ✅ CRC32C checksum support
- ✅ Dictionary caching with sync.Map
- ✅ Goroutine-safe operations
- ✅ Zero-allocation optimizations

## Requirements

- Go 1.22 or higher

## Installation

```bash
go get github.com/umitkavala/zeroc/implementations/go/zeroc
```

## Dependencies

```bash
go get github.com/klauspost/compress/zstd
go get google.golang.org/protobuf
```

## Planned API

### Wire Format

```go
import "github.com/umitkavala/zeroc/implementations/go/zeroc"

// Encode
protoBytes := order.Marshal()
frame, err := zeroc.EncodeFrame(zeroc.EncodeOptions{
    ProtoBytes:   protoBytes,
    DictionaryID: 0,
    SchemaHash:   0,
    Compress:     true,
    Checksum:     true,
    Compressor:   nil, // optional
})

// Decode
decoded, metadata, err := zeroc.DecodeFrame(frame)

// Decompress
decompressed, err := zeroc.DecompressPayload(
    decoded,
    metadata.DictionaryID,
    nil, // decompressor (optional)
)
```

### Dictionary Loader

```go
import "github.com/umitkavala/zeroc/implementations/go/zeroc"

// Load dictionary
loader := zeroc.NewDictionaryLoader()
dict, err := loader.Load("dictionaries/Order-1.0.0.zdict")
if err != nil {
    log.Fatal(err)
}

// Get metadata
fmt.Printf("Schema: %s\n", dict.Metadata.SchemaName)
fmt.Printf("Dictionary ID: 0x%08x\n", dict.Metadata.DictionaryID)

// Get encoder/decoder
encoder, err := dict.NewEncoder(3) // compression level 3
decoder, err := dict.NewDecoder()
```

## Project Structure

```
implementations/go/
├── go.mod                          # Go module definition
├── go.sum                          # Dependency checksums
├── zeroc/
│   ├── wire_format.go             # Frame encoding/decoding
│   ├── wire_format_test.go
│   ├── dictionary.go              # Dictionary loading
│   ├── dictionary_test.go
│   ├── varint.go                  # LEB128 encoding
│   ├── varint_test.go
│   ├── constants.go               # Protocol constants
│   └── errors.go                  # Error types
├── examples/
│   └── basic_usage.go
└── README.md
```

## Build & Test

```bash
# Build
go build ./...

# Run tests
go test ./... -v

# Run tests with coverage
go test ./... -cover -coverprofile=coverage.out
go tool cover -html=coverage.out

# Run benchmarks
go test ./... -bench=. -benchmem

# Install
go install ./...
```

## Usage Example

```go
package main

import (
    "fmt"
    "log"

    "github.com/umitkavala/zeroc/implementations/go/zeroc"
    pb "your/protobuf/package"
)

func main() {
    // Load dictionary
    loader := zeroc.NewDictionaryLoader()
    dict, err := loader.Load("dictionaries/Order-1.0.0.zdict")
    if err != nil {
        log.Fatal(err)
    }

    // Create protobuf message
    order := &pb.Order{
        OrderId:   "ORD-123",
        UserId:    12345,
        Timestamp: time.Now().Unix(),
    }

    protoBytes, err := proto.Marshal(order)
    if err != nil {
        log.Fatal(err)
    }

    // Get encoder
    encoder, err := dict.NewEncoder(3)
    if err != nil {
        log.Fatal(err)
    }

    // Encode with dictionary
    frame, err := zeroc.EncodeFrame(zeroc.EncodeOptions{
        ProtoBytes:   protoBytes,
        DictionaryID: dict.Metadata.DictionaryID,
        SchemaHash:   0,
        Compress:     true,
        Checksum:     true,
        Encoder:      encoder,
    })
    if err != nil {
        log.Fatal(err)
    }

    fmt.Printf("Protobuf size: %d bytes\n", len(protoBytes))
    fmt.Printf("Frame size: %d bytes\n", len(frame))
    fmt.Printf("Compression ratio: %.2fx\n",
        float64(len(protoBytes))/float64(len(frame)))

    // Decode
    payload, metadata, err := zeroc.DecodeFrame(frame)
    if err != nil {
        log.Fatal(err)
    }

    // Get decoder
    decoder, err := dict.NewDecoder()
    if err != nil {
        log.Fatal(err)
    }

    // Decompress
    decompressed, err := zeroc.DecompressPayload(
        payload,
        metadata.DictionaryID,
        decoder,
    )
    if err != nil {
        log.Fatal(err)
    }

    // Parse back
    orderDecoded := &pb.Order{}
    if err := proto.Unmarshal(decompressed, orderDecoded); err != nil {
        log.Fatal(err)
    }

    fmt.Printf("Order ID: %s\n", orderDecoded.OrderId)
}
```

## Implementation Notes

### Concurrency Safety

The Go implementation will be goroutine-safe:
- `DictionaryLoader` uses `sync.Map` for caching
- `Dictionary` structs are immutable after loading
- Encoders/decoders can be pooled with `sync.Pool`

### Performance Optimizations

- Zero-allocation byte buffer pooling
- Reusable encoder/decoder instances
- Dictionary caching to avoid repeated I/O
- Benchmark-driven optimizations

### Error Handling

```go
var (
    ErrInvalidMagic        = errors.New("invalid magic bytes")
    ErrUnsupportedVersion  = errors.New("unsupported protocol version")
    ErrChecksumMismatch    = errors.New("checksum mismatch")
    ErrTruncatedFrame      = errors.New("truncated frame")
    ErrInvalidDictionary   = errors.New("invalid dictionary format")
    ErrDictionaryIDMismatch = errors.New("dictionary ID mismatch")
)
```

### Types

```go
// FrameMetadata contains decoded frame metadata
type FrameMetadata struct {
    Version          byte
    MajorVersion     int
    MinorVersion     int
    Flags            byte
    DictionaryID     uint32
    SchemaHash       uint32
    CompressedSize   int
    CompressionEnabled bool
    DictionaryUsed   bool
    ChecksumIncluded bool
}

// DictionaryMetadata contains dictionary file metadata
type DictionaryMetadata struct {
    Version          string
    SchemaName       string
    DictionaryID     uint32
    SampleCount      uint32
    Created          int64
    CompressionLevel uint32
    DictSize         uint32
    MinSize          uint32
    MaxSize          uint32
    SHA256Prefix     uint64
}

// Dictionary represents a loaded Zeroc dictionary
type Dictionary struct {
    Metadata *DictionaryMetadata
    Data     []byte
}
```

## Testing

```bash
# Run all tests
go test ./... -v

# Run specific test
go test ./zeroc -run TestWireFormat -v

# Run with race detector
go test ./... -race

# Run benchmarks
go test ./... -bench=. -benchmem
```

## Benchmarking

Expected performance on modern hardware:

```
BenchmarkEncodeFrame-8          1000000    1200 ns/op    128 B/op    2 allocs/op
BenchmarkDecodeFrame-8          2000000     600 ns/op     64 B/op    1 allocs/op
BenchmarkEncodeWithDict-8        500000    2000 ns/op    256 B/op    3 allocs/op
BenchmarkDecodeWithDict-8       1000000    1000 ns/op    128 B/op    2 allocs/op
```

## Contributing

See main repository [CONTRIBUTING.md](../../CONTRIBUTING.md).

## Related Documentation

- [Wire Format Specification](../../spec/WIRE_FORMAT.md)
- [Dictionary Format Specification](../../spec/DICTIONARY_FORMAT.md)
- [Protocol Specification](../../spec/PROTOCOL.md)
