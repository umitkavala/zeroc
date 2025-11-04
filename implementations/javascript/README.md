# Zeroc JavaScript/TypeScript Implementation

JavaScript and TypeScript implementation of the Zeroc compression protocol.

## Status

🚧 **Under Development** - Skeleton implementation

## Planned Features

- ✅ Wire format encoder/decoder
- ✅ Dictionary loader with validation
- ✅ CRC32C checksum support
- ✅ Dictionary caching
- ✅ Browser and Node.js support
- ✅ TypeScript type definitions
- ✅ Zero-dependency core (zstd via WASM optional)

## Requirements

- Node.js 20+ (LTS) or modern browser
- TypeScript 5.0+ (for development)

## Installation

### NPM

```bash
npm install @umitkavala/zeroc
```

### Yarn

```bash
yarn add @umitkavala/zeroc
```

## Dependencies

```json
{
  "dependencies": {
    "@zstd-js/wasm": "^1.0.0",
    "protobufjs": "^7.2.5"
  },
  "devDependencies": {
    "typescript": "^5.3.0",
    "@types/node": "^20.10.0",
    "vitest": "^1.0.0"
  }
}
```

## Planned API

### Wire Format

```typescript
import { encodeFrame, decodeFrame, decompressPayload } from '@umitkavala/zeroc';

// Encode
const protoBytes = order.serializeBinary();
const frame = await encodeFrame({
  protoBytes,
  dictionaryId: 0,
  schemaHash: 0,
  compress: true,
  checksum: true,
  compressor: null, // optional
});

// Decode
const { payload, metadata } = await decodeFrame(frame);

// Decompress
const decompressed = await decompressPayload(
  payload,
  metadata.dictionaryId,
  null // decompressor (optional)
);
```

### Dictionary Loader

```typescript
import { DictionaryLoader } from '@umitkavala/zeroc';

// Load dictionary
const loader = new DictionaryLoader();
const dict = await loader.load('dictionaries/Order-1.0.0.zdict');

// Get metadata
console.log(`Schema: ${dict.metadata.schemaName}`);
console.log(`Dictionary ID: 0x${dict.metadata.dictionaryId.toString(16)}`);

// Get compressor/decompressor
const compressor = await dict.getCompressor(3); // level 3
const decompressor = await dict.getDecompressor();
```

## Project Structure

```
implementations/javascript/
├── package.json                    # NPM configuration
├── tsconfig.json                   # TypeScript configuration
├── vite.config.ts                  # Vite configuration (for tests)
├── src/
│   ├── wire-format.ts             # Frame encoding/decoding
│   ├── dictionary-loader.ts       # Dictionary loading
│   ├── varint.ts                  # LEB128 encoding
│   ├── constants.ts               # Protocol constants
│   ├── types.ts                   # TypeScript types
│   ├── errors.ts                  # Error classes
│   └── index.ts                   # Main exports
├── test/
│   ├── wire-format.test.ts
│   ├── dictionary-loader.test.ts
│   └── varint.test.ts
├── examples/
│   ├── node-example.ts            # Node.js example
│   └── browser-example.html       # Browser example
└── README.md
```

## Build & Test

```bash
# Install dependencies
npm install

# Build
npm run build

# Run tests
npm test

# Run tests with coverage
npm run test:coverage

# Run in watch mode
npm run test:watch

# Type check
npm run typecheck

# Lint
npm run lint
```

## Usage Example

### Node.js

```typescript
import { DictionaryLoader, encodeFrame, decodeFrame } from '@umitkavala/zeroc';
import { Order } from './generated/api_pb';

async function main() {
  // Load dictionary
  const loader = new DictionaryLoader();
  const dict = await loader.load('dictionaries/Order-1.0.0.zdict');

  // Create protobuf message
  const order = new Order();
  order.setOrderId('ORD-123');
  order.setUserId(12345);
  order.setTimestamp(Date.now());

  const protoBytes = order.serializeBinary();

  // Get compressor
  const compressor = await dict.getCompressor(3);

  // Encode with dictionary
  const frame = await encodeFrame({
    protoBytes,
    dictionaryId: dict.metadata.dictionaryId,
    schemaHash: 0,
    compress: true,
    checksum: true,
    compressor,
  });

  console.log(`Protobuf size: ${protoBytes.length} bytes`);
  console.log(`Frame size: ${frame.length} bytes`);
  console.log(`Compression ratio: ${(protoBytes.length / frame.length).toFixed(2)}x`);

  // Decode
  const { payload, metadata } = await decodeFrame(frame);

  // Get decompressor
  const decompressor = await dict.getDecompressor();

  // Decompress
  const decompressed = await decompressor.decompress(payload);

  // Parse back
  const orderDecoded = Order.deserializeBinary(decompressed);
  console.log(`Order ID: ${orderDecoded.getOrderId()}`);
}

main();
```

### Browser

```html
<!DOCTYPE html>
<html>
<head>
  <title>Zeroc Example</title>
</head>
<body>
  <script type="module">
    import { DictionaryLoader, encodeFrame, decodeFrame } from './dist/zeroc.js';

    async function compress() {
      // Load dictionary from CDN or local file
      const loader = new DictionaryLoader();
      const dict = await loader.loadFromUrl(
        'https://cdn.example.com/dictionaries/Order-1.0.0.zdict'
      );

      // Create protobuf message
      const protoBytes = new Uint8Array([/* ... */]);

      // Compress
      const compressor = await dict.getCompressor(3);
      const frame = await encodeFrame({
        protoBytes,
        dictionaryId: dict.metadata.dictionaryId,
        compress: true,
        checksum: true,
        compressor,
      });

      console.log('Compressed:', frame.length, 'bytes');

      // Send via fetch
      const response = await fetch('/api/orders', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/x-zeroc',
          'Content-Encoding': 'zstd',
        },
        body: frame,
      });
    }

    compress();
  </script>
</body>
</html>
```

## Implementation Notes

### Browser Support

The implementation will support:
- Modern browsers (Chrome 120+, Firefox 120+, Safari 17+, Edge 120+)
- Node.js 20+
- Deno 1.40+
- Bun 1.0+

### WASM Integration

```typescript
// Lazy load WASM for zstd compression
import { init as initZstd } from '@zstd-js/wasm';

// Initialize once
await initZstd();

// Use zstd functions
```

### TypeScript Types

```typescript
export interface EncodeOptions {
  protoBytes: Uint8Array;
  dictionaryId?: number;
  schemaHash?: number;
  compress?: boolean;
  checksum?: boolean;
  compressor?: ZstdCompressor | null;
}

export interface FrameMetadata {
  version: number;
  majorVersion: number;
  minorVersion: number;
  flags: number;
  dictionaryId: number;
  schemaHash: number;
  compressedSize: number;
  compressionEnabled: boolean;
  dictionaryUsed: boolean;
  checksumIncluded: boolean;
}

export interface DictionaryMetadata {
  version: string;
  schemaName: string;
  dictionaryId: number;
  sampleCount: number;
  created: number;
  compressionLevel: number;
  dictSize: number;
  minSize: number;
  maxSize: number;
  sha256Prefix: bigint;
}

export class ZerocError extends Error {
  constructor(message: string);
}

export class InvalidMagicError extends ZerocError {}
export class UnsupportedVersionError extends ZerocError {}
export class ChecksumMismatchError extends ZerocError {}
export class TruncatedFrameError extends ZerocError {}
```

### Performance Optimizations

- ArrayBuffer pooling for frequent operations
- Lazy WASM initialization
- Dictionary caching with LRU eviction
- Streaming API for large payloads

## Testing

```bash
# Run all tests
npm test

# Run specific test
npm test -- wire-format

# Run with coverage
npm run test:coverage

# Run in browser
npm run test:browser
```

## Bundle Size

Target bundle sizes:
- Core (no zstd): ~5KB gzipped
- With zstd WASM: ~45KB gzipped
- Full bundle: ~50KB gzipped

## Browser Example with Service Worker

```typescript
// sw.js - Service Worker for automatic decompression
self.addEventListener('fetch', async (event) => {
  const response = await fetch(event.request);

  // Check if response is Zeroc encoded
  if (response.headers.get('Content-Type') === 'application/x-zeroc') {
    const { decodeFrame, decompressPayload } = await import('@umitkavala/zeroc');

    const frameBytes = new Uint8Array(await response.arrayBuffer());
    const { payload, metadata } = await decodeFrame(frameBytes);

    // Decompress
    const decompressed = await decompressPayload(payload, metadata.dictionaryId);

    return new Response(decompressed, {
      headers: { 'Content-Type': 'application/x-protobuf' },
    });
  }

  return response;
});
```

## Contributing

See main repository [CONTRIBUTING.md](../../CONTRIBUTING.md).

## Related Documentation

- [Wire Format Specification](../../spec/WIRE_FORMAT.md)
- [Dictionary Format Specification](../../spec/DICTIONARY_FORMAT.md)
- [Protocol Specification](../../spec/PROTOCOL.md)
