# Zeroc Java Implementation

Java implementation of the Zeroc compression protocol.

## Status

🚧 **Under Development** - Skeleton implementation

## Planned Features

- ✅ Wire format encoder/decoder
- ✅ Dictionary loader with validation
- ✅ CRC32C checksum support
- ✅ Dictionary caching
- ✅ Thread-safe operations
- ✅ Maven/Gradle support

## Requirements

- Java 21 or higher (LTS)
- Maven 3.9+ or Gradle 8.0+

## Dependencies

```xml
<dependencies>
    <!-- Zstandard compression -->
    <dependency>
        <groupId>com.github.luben</groupId>
        <artifactId>zstd-jni</artifactId>
        <version>1.5.5-11</version>
    </dependency>

    <!-- Protocol Buffers -->
    <dependency>
        <groupId>com.google.protobuf</groupId>
        <artifactId>protobuf-java</artifactId>
        <version>3.25.1</version>
    </dependency>

    <!-- Testing -->
    <dependency>
        <groupId>junit</groupId>
        <artifactId>junit</artifactId>
        <version>5.10.1</version>
        <scope>test</scope>
    </dependency>
</dependencies>
```

## Planned API

### Wire Format

```java
import io.github.umitkavala.zeroc.WireFormat;
import io.github.umitkavala.zeroc.Frame;
import io.github.umitkavala.zeroc.FrameMetadata;

// Encode
byte[] protoBytes = order.toByteArray();
byte[] frame = WireFormat.encodeFrame(
    protoBytes,
    0,              // dictionaryId
    0,              // schemaHash
    true,           // compress
    true,           // checksum
    null            // compressor (optional)
);

// Decode
Frame decoded = WireFormat.decodeFrame(frame);
FrameMetadata metadata = decoded.getMetadata();
byte[] payload = decoded.getPayload();

// Decompress
byte[] decompressed = WireFormat.decompressPayload(
    payload,
    metadata.getDictionaryId(),
    null  // decompressor (optional)
);
```

### Dictionary Loader

```java
import io.github.umitkavala.zeroc.DictionaryLoader;
import io.github.umitkavala.zeroc.Dictionary;
import io.github.umitkavala.zeroc.DictionaryMetadata;

// Load dictionary
DictionaryLoader loader = new DictionaryLoader();
Dictionary dict = loader.load("dictionaries/Order-1.0.0.zdict");

// Get metadata
DictionaryMetadata metadata = dict.getMetadata();
System.out.println("Schema: " + metadata.getSchemaName());
System.out.println("Dictionary ID: " + String.format("0x%08x", metadata.getDictionaryId()));

// Get compressor/decompressor
ZstdCompressor compressor = dict.getCompressor(3);  // level 3
ZstdDecompressor decompressor = dict.getDecompressor();
```

## Project Structure

```
implementations/java/
├── pom.xml                          # Maven configuration
├── build.gradle                     # Gradle configuration
├── src/
│   ├── main/
│   │   └── java/
│   │       └── com/
│   │           └── zeroc/
│   │               ├── WireFormat.java
│   │               ├── Frame.java
│   │               ├── FrameMetadata.java
│   │               ├── Dictionary.java
│   │               ├── DictionaryLoader.java
│   │               ├── DictionaryMetadata.java
│   │               ├── Constants.java
│   │               └── util/
│   │                   ├── Varint.java
│   │                   └── CRC32C.java
│   └── test/
│       └── java/
│           └── com/
│               └── zeroc/
│                   ├── WireFormatTest.java
│                   ├── DictionaryLoaderTest.java
│                   └── VarintTest.java
├── examples/
│   └── BasicUsage.java
└── README.md
```

## Build

### Maven

```bash
# Build
mvn clean package

# Run tests
mvn test

# Install locally
mvn install
```

### Gradle

```bash
# Build
./gradlew build

# Run tests
./gradlew test

# Install locally
./gradlew publishToMavenLocal
```

## Usage Example

```java
import io.github.umitkavala.zeroc.*;
import com.google.protobuf.ByteString;

public class Example {
    public static void main(String[] args) throws Exception {
        // Load dictionary
        DictionaryLoader loader = new DictionaryLoader();
        Dictionary dict = loader.load("dictionaries/Order-1.0.0.zdict");

        // Create protobuf message
        Order order = Order.newBuilder()
            .setOrderId("ORD-123")
            .setUserId(12345)
            .setTimestamp(System.currentTimeMillis())
            .build();

        byte[] protoBytes = order.toByteArray();

        // Encode with dictionary
        byte[] frame = WireFormat.encodeFrame(
            protoBytes,
            dict.getMetadata().getDictionaryId(),
            0,
            true,
            true,
            dict.getCompressor(3)
        );

        System.out.println("Protobuf size: " + protoBytes.length);
        System.out.println("Frame size: " + frame.length);
        System.out.println("Compression ratio: " +
            (float)protoBytes.length / frame.length);

        // Decode
        Frame decoded = WireFormat.decodeFrame(frame);
        byte[] decompressed = WireFormat.decompressPayload(
            decoded.getPayload(),
            decoded.getMetadata().getDictionaryId(),
            dict.getDecompressor()
        );

        // Parse back
        Order orderDecoded = Order.parseFrom(decompressed);
        assert orderDecoded.getOrderId().equals("ORD-123");
    }
}
```

## Implementation Notes

### Thread Safety

The Java implementation will be thread-safe:
- `DictionaryLoader` uses `ConcurrentHashMap` for caching
- `Dictionary` objects are immutable after loading
- `ZstdCompressor` and `ZstdDecompressor` are thread-safe

### Performance Optimizations

- Dictionary caching to avoid repeated file I/O
- Buffer pooling for frequent encode/decode operations
- Direct ByteBuffer support for zero-copy operations
- JMH benchmarks for performance testing

### Error Handling

```java
try {
    byte[] frame = WireFormat.decodeFrame(data);
} catch (InvalidMagicException e) {
    // Invalid magic bytes
} catch (UnsupportedVersionException e) {
    // Unsupported protocol version
} catch (ChecksumMismatchException e) {
    // Data corruption detected
} catch (TruncatedFrameException e) {
    // Incomplete frame
}
```

## Testing

```bash
# Run all tests
mvn test

# Run specific test
mvn test -Dtest=WireFormatTest

# Run with coverage
mvn test jacoco:report
```

## Contributing

See main repository [CONTRIBUTING.md](../../CONTRIBUTING.md).

## Related Documentation

- [Wire Format Specification](../../spec/WIRE_FORMAT.md)
- [Dictionary Format Specification](../../spec/DICTIONARY_FORMAT.md)
- [Protocol Specification](../../spec/PROTOCOL.md)
