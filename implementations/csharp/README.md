# Zeroc C# Implementation

C# implementation of the Zeroc compression protocol.

## Status

🚧 **Under Development** - Skeleton implementation

## Planned Features

- ✅ Wire format encoder/decoder
- ✅ Dictionary loader with validation
- ✅ CRC32C checksum support
- ✅ Dictionary caching with MemoryCache
- ✅ Thread-safe operations
- ✅ .NET 8.0+ support
- ✅ Span<T> and Memory<T> for zero-copy
- ✅ NuGet package

## Requirements

- .NET 8.0 or higher (LTS)
- C# 12+

## Installation

### NuGet

```bash
dotnet add package Umitkavala.Zeroc
```

### Package Manager

```powershell
Install-Package Umitkavala.Zeroc
```

## Dependencies

```xml
<ItemGroup>
  <PackageReference Include="ZstdSharp.Port" Version="0.7.3" />
  <PackageReference Include="Google.Protobuf" Version="3.25.1" />
  <PackageReference Include="System.IO.Hashing" Version="8.0.0" />
</ItemGroup>
```

## Planned API

### Wire Format

```csharp
using Umitkavala.Zeroc;

// Encode
byte[] protoBytes = order.ToByteArray();
byte[] frame = WireFormat.EncodeFrame(new EncodeOptions
{
    ProtoBytes = protoBytes,
    DictionaryId = 0,
    SchemaHash = 0,
    Compress = true,
    Checksum = true,
    Compressor = null // optional
});

// Decode
var (payload, metadata) = WireFormat.DecodeFrame(frame);

// Decompress
byte[] decompressed = WireFormat.DecompressPayload(
    payload,
    metadata.DictionaryId,
    null // decompressor (optional)
);
```

### Dictionary Loader

```csharp
using Umitkavala.Zeroc;

// Load dictionary
var loader = new DictionaryLoader();
var dict = await loader.LoadAsync("dictionaries/Order-1.0.0.zdict");

// Get metadata
Console.WriteLine($"Schema: {dict.Metadata.SchemaName}");
Console.WriteLine($"Dictionary ID: 0x{dict.Metadata.DictionaryId:X8}");

// Get compressor/decompressor
var compressor = dict.GetCompressor(3); // level 3
var decompressor = dict.GetDecompressor();
```

## Project Structure

```
implementations/csharp/
├── Zeroc.sln                   # Visual Studio solution
├── src/
│   └── Zeroc/
│       ├── Zeroc.csproj       # Project file
│       ├── WireFormat.cs          # Frame encoding/decoding
│       ├── Frame.cs               # Frame data structures
│       ├── FrameMetadata.cs       # Metadata structures
│       ├── Dictionary.cs          # Dictionary class
│       ├── DictionaryLoader.cs    # Dictionary loading
│       ├── DictionaryMetadata.cs  # Dictionary metadata
│       ├── Constants.cs           # Protocol constants
│       ├── Varint.cs              # LEB128 encoding
│       └── Exceptions.cs          # Exception types
├── test/
│   └── Zeroc.Tests/
│       ├── Zeroc.Tests.csproj
│       ├── WireFormatTests.cs
│       ├── DictionaryLoaderTests.cs
│       └── VarintTests.cs
├── examples/
│   └── BasicUsage/
│       ├── BasicUsage.csproj
│       └── Program.cs
└── README.md
```

## Build & Test

```bash
# Restore dependencies
dotnet restore

# Build
dotnet build

# Run tests
dotnet test

# Run tests with coverage
dotnet test --collect:"XPlat Code Coverage"

# Pack NuGet package
dotnet pack -c Release
```

## Usage Example

```csharp
using Umitkavala.Zeroc;
using YourProtobufNamespace;

class Program
{
    static async Task Main(string[] args)
    {
        // Load dictionary
        var loader = new DictionaryLoader();
        var dict = await loader.LoadAsync("dictionaries/Order-1.0.0.zdict");

        // Create protobuf message
        var order = new Order
        {
            OrderId = "ORD-123",
            UserId = 12345,
            Timestamp = DateTimeOffset.UtcNow.ToUnixTimeSeconds()
        };

        byte[] protoBytes = order.ToByteArray();

        // Get compressor
        var compressor = dict.GetCompressor(3);

        // Encode with dictionary
        byte[] frame = WireFormat.EncodeFrame(new EncodeOptions
        {
            ProtoBytes = protoBytes,
            DictionaryId = dict.Metadata.DictionaryId,
            SchemaHash = 0,
            Compress = true,
            Checksum = true,
            Compressor = compressor
        });

        Console.WriteLine($"Protobuf size: {protoBytes.Length} bytes");
        Console.WriteLine($"Frame size: {frame.Length} bytes");
        Console.WriteLine($"Compression ratio: {(float)protoBytes.Length / frame.Length:F2}x");

        // Decode
        var (payload, metadata) = WireFormat.DecodeFrame(frame);

        // Get decompressor
        var decompressor = dict.GetDecompressor();

        // Decompress
        byte[] decompressed = WireFormat.DecompressPayload(
            payload,
            metadata.DictionaryId,
            decompressor
        );

        // Parse back
        var orderDecoded = Order.Parser.ParseFrom(decompressed);
        Console.WriteLine($"Order ID: {orderDecoded.OrderId}");
    }
}
```

## Implementation Notes

### Thread Safety

The C# implementation will be thread-safe:
- `DictionaryLoader` uses `ConcurrentDictionary` for caching
- `Dictionary` objects are immutable after loading
- Compressor/decompressor instances use proper locking

### Performance Optimizations

- `Span<T>` and `Memory<T>` for zero-copy operations
- `ArrayPool<T>` for buffer reuse
- Dictionary caching with `MemoryCache`
- Async I/O for file operations

### Modern C# Features

```csharp
// Span-based encoding
public static ReadOnlySpan<byte> EncodeFrame(
    ReadOnlySpan<byte> protoBytes,
    uint dictionaryId = 0,
    uint schemaHash = 0,
    bool compress = true,
    bool checksum = false,
    ZstdCompressor? compressor = null);

// ValueTask for performance
public ValueTask<Dictionary> LoadAsync(
    string filepath,
    CancellationToken cancellationToken = default);

// Pattern matching
var result = DecodeFrame(frame) switch
{
    { Metadata.CompressionEnabled: true } => "Compressed",
    { Metadata.DictionaryUsed: true } => "Dictionary used",
    _ => "Identity"
};
```

### Exception Types

```csharp
public class ZerocException : Exception { }
public class InvalidMagicException : ZerocException { }
public class UnsupportedVersionException : ZerocException { }
public class ChecksumMismatchException : ZerocException { }
public class TruncatedFrameException : ZerocException { }
public class InvalidDictionaryException : ZerocException { }
public class DictionaryIdMismatchException : ZerocException { }
```

### Data Structures

```csharp
public record FrameMetadata
{
    public byte Version { get; init; }
    public int MajorVersion { get; init; }
    public int MinorVersion { get; init; }
    public byte Flags { get; init; }
    public uint DictionaryId { get; init; }
    public uint SchemaHash { get; init; }
    public int CompressedSize { get; init; }
    public bool CompressionEnabled { get; init; }
    public bool DictionaryUsed { get; init; }
    public bool ChecksumIncluded { get; init; }
}

public record DictionaryMetadata
{
    public string Version { get; init; } = string.Empty;
    public string SchemaName { get; init; } = string.Empty;
    public uint DictionaryId { get; init; }
    public uint SampleCount { get; init; }
    public long Created { get; init; }
    public uint CompressionLevel { get; init; }
    public uint DictSize { get; init; }
    public uint MinSize { get; init; }
    public uint MaxSize { get; init; }
    public ulong SHA256Prefix { get; init; }
}

public sealed class Dictionary : IDisposable
{
    public DictionaryMetadata Metadata { get; }
    public ReadOnlyMemory<byte> Data { get; }

    public ZstdCompressor GetCompressor(int level = 3);
    public ZstdDecompressor GetDecompressor();
    public void Dispose();
}
```

## Testing

```bash
# Run all tests
dotnet test

# Run specific test
dotnet test --filter "FullyQualifiedName~WireFormatTests"

# Run with coverage
dotnet test --collect:"XPlat Code Coverage"

# Generate coverage report
dotnet tool install -g dotnet-reportgenerator-globaltool
reportgenerator -reports:coverage.cobertura.xml -targetdir:coveragereport
```

## Benchmarking

```csharp
using BenchmarkDotNet.Attributes;
using BenchmarkDotNet.Running;

[MemoryDiagnoser]
public class ZerocBenchmarks
{
    [Benchmark]
    public byte[] EncodeFrame() { /* ... */ }

    [Benchmark]
    public (byte[], FrameMetadata) DecodeFrame() { /* ... */ }

    [Benchmark]
    public byte[] EncodeWithDictionary() { /* ... */ }

    [Benchmark]
    public byte[] DecodeWithDictionary() { /* ... */ }
}
```

Expected performance on modern hardware:

```
|                Method |     Mean |   Error |  StdDev | Allocated |
|---------------------- |---------:|--------:|--------:|----------:|
|           EncodeFrame | 1.200 μs | 0.02 μs | 0.02 μs |     256 B |
|           DecodeFrame | 0.600 μs | 0.01 μs | 0.01 μs |     128 B |
| EncodeWithDictionary | 2.000 μs | 0.03 μs | 0.03 μs |     512 B |
| DecodeWithDictionary | 1.000 μs | 0.02 μs | 0.02 μs |     256 B |
```

## ASP.NET Core Integration

```csharp
// Startup.cs or Program.cs
builder.Services.AddZeroc(options =>
{
    options.DictionaryPath = "dictionaries";
    options.EnableCaching = true;
    options.CompressionLevel = 3;
});

// Middleware
app.UseZerocCompression();

// Controller
[ApiController]
[Route("api/[controller]")]
public class OrdersController : ControllerBase
{
    [HttpPost]
    [Consumes("application/x-zeroc")]
    [Produces("application/x-zeroc")]
    public async Task<IActionResult> CreateOrder([FromBody] Order order)
    {
        // Automatic compression/decompression via middleware
        return Ok(order);
    }
}
```

## Contributing

See main repository [CONTRIBUTING.md](../../CONTRIBUTING.md).

## Related Documentation

- [Wire Format Specification](../../spec/WIRE_FORMAT.md)
- [Dictionary Format Specification](../../spec/DICTIONARY_FORMAT.md)
- [Protocol Specification](../../spec/PROTOCOL.md)
