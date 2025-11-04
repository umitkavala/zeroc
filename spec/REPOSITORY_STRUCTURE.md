# Repository Structure Proposal

## Executive Summary

**Recommendation: Monorepo with Language-Specific Packages**

A monorepo approach is recommended for the ProtoZstd compression protocol implementation for the following reasons:

1. **Single source of truth** for protocol specification and test data
2. **Atomic cross-language changes** when updating the protocol
3. **Shared tooling** for benchmarks, testing, and documentation
4. **Easier version synchronization** across language implementations
5. **Better developer experience** for contributors working across languages

## Repository Structure

```
protozstd/
├── README.md                          # Main project overview
├── LICENSE                            # Apache 2.0 or MIT
├── CONTRIBUTING.md                    # Contribution guidelines
├── CODE_OF_CONDUCT.md                 # Community guidelines
├── CHANGELOG.md                       # Version history
│
├── spec/                              # Protocol specification (canonical)
│   ├── PROTOCOL.md                    # Complete protocol spec
│   ├── WIRE_FORMAT.md                 # Binary format specification
│   ├── DICTIONARY_FORMAT.md           # Dictionary exchange format
│   ├── ERROR_CODES.md                 # Error code reference
│   └── VERSIONING.md                  # Version compatibility matrix
│
├── proto/                             # Protocol Buffer definitions
│   ├── protozstd/                     # Package namespace
│   │   ├── v1/                        # Version 1
│   │   │   ├── compression.proto      # Core compression messages
│   │   │   ├── dictionary.proto       # Dictionary metadata
│   │   │   └── errors.proto           # Error messages
│   │   └── v2/                        # Future version (when needed)
│   ├── buf.yaml                       # Buf configuration
│   ├── buf.gen.yaml                   # Code generation config
│   └── README.md                      # Proto usage guide
│
├── dictionaries/                      # Reference dictionaries
│   ├── formats/                       # Sample dictionaries
│   │   ├── ecommerce-orders-v1.0.0.zdict
│   │   ├── iot-telemetry-v1.0.0.zdict
│   │   └── api-logs-v1.0.0.zdict
│   ├── training/                      # Training data samples
│   │   └── sample-orders-10k.jsonl
│   └── README.md                      # Dictionary usage guide
│
├── test-data/                         # Shared test data
│   ├── golden/                        # Golden test files
│   │   ├── compressed/                # Pre-compressed test files
│   │   └── uncompressed/              # Original test files
│   ├── fixtures/                      # Test fixtures
│   │   ├── valid/                     # Valid payloads
│   │   ├── invalid/                   # Invalid/malicious payloads
│   │   └── edge-cases/                # Edge cases
│   └── README.md                      # Test data documentation
│
├── benchmarks/                        # Cross-language benchmarks
│   ├── datasets/                      # Benchmark datasets
│   ├── results/                       # Benchmark results
│   ├── runner/                        # Benchmark orchestration
│   └── README.md                      # Benchmark documentation
│
├── docs/                              # Documentation
│   ├── getting-started.md             # Quick start guide
│   ├── architecture.md                # Architecture overview
│   ├── implementation-guide.md        # Guide for new languages
│   ├── best-practices.md              # Best practices
│   ├── performance-tuning.md          # Performance optimization
│   ├── migration-guide.md             # Migration from other formats
│   └── api/                           # API documentation per language
│       ├── python.md
│       ├── java.md
│       ├── go.md
│       ├── javascript.md
│       └── csharp.md
│
├── implementations/                   # Language implementations
│   ├── python/                        # Python implementation
│   │   ├── protozstd/                 # Package
│   │   │   ├── __init__.py
│   │   │   ├── compressor.py
│   │   │   ├── decompressor.py
│   │   │   ├── dictionary.py
│   │   │   ├── protocol.py
│   │   │   └── errors.py
│   │   ├── tests/
│   │   ├── benchmarks/
│   │   ├── examples/
│   │   ├── setup.py
│   │   ├── pyproject.toml
│   │   └── README.md
│   │
│   ├── java/                          # Java implementation
│   │   ├── pom.xml                    # Maven config
│   │   ├── src/
│   │   │   ├── main/java/com/protozstd/
│   │   │   └── test/java/com/protozstd/
│   │   ├── benchmarks/
│   │   └── README.md
│   │
│   ├── go/                            # Go implementation
│   │   ├── go.mod
│   │   ├── compressor.go
│   │   ├── decompressor.go
│   │   ├── dictionary.go
│   │   ├── protocol.go
│   │   ├── compressor_test.go
│   │   ├── benchmarks/
│   │   └── README.md
│   │
│   ├── javascript/                    # JavaScript/TypeScript
│   │   ├── package.json
│   │   ├── tsconfig.json
│   │   ├── src/
│   │   │   ├── compressor.ts
│   │   │   ├── decompressor.ts
│   │   │   ├── dictionary.ts
│   │   │   └── protocol.ts
│   │   ├── test/
│   │   ├── benchmarks/
│   │   └── README.md
│   │
│   ├── csharp/                        # C# implementation
│   │   ├── ProtoZstd.sln
│   │   ├── ProtoZstd/
│   │   │   ├── ProtoZstd.csproj
│   │   │   ├── Compressor.cs
│   │   │   ├── Decompressor.cs
│   │   │   └── Dictionary.cs
│   │   ├── ProtoZstd.Tests/
│   │   └── README.md
│   │
│   └── README.md                      # Implementation overview
│
├── tools/                             # Shared tooling
│   ├── dict-trainer/                  # Dictionary training tool
│   │   ├── main.py
│   │   ├── requirements.txt
│   │   └── README.md
│   ├── validator/                     # Protocol validator
│   │   └── validate.py
│   ├── generator/                     # Test data generator
│   │   └── generate.py
│   └── bench-runner/                  # Benchmark runner
│       └── run.sh
│
├── scripts/                           # Build and CI scripts
│   ├── setup-dev.sh                   # Developer setup
│   ├── run-tests.sh                   # Run all tests
│   ├── generate-protos.sh             # Generate proto code
│   ├── run-benchmarks.sh              # Run benchmarks
│   └── release.sh                     # Release automation
│
├── .github/                           # GitHub configuration
│   ├── workflows/                     # CI/CD workflows
│   │   ├── ci.yml                     # Main CI
│   │   ├── release.yml                # Release workflow
│   │   ├── benchmark.yml              # Benchmark on PR
│   │   └── docs.yml                   # Documentation build
│   ├── ISSUE_TEMPLATE/
│   └── PULL_REQUEST_TEMPLATE.md
│
└── examples/                          # End-to-end examples
    ├── http-server/                   # HTTP server example
    ├── http-client/                   # HTTP client example
    ├── grpc-service/                  # gRPC service example
    └── README.md
```

## Rationale for Monorepo

### Advantages

1. **Protocol Evolution**
   - Protocol spec changes are atomic across all implementations
   - No risk of implementations drifting out of sync
   - Single version number for the entire project

2. **Testing**
   - Shared test data ensures all implementations are tested identically
   - Cross-language integration tests are easier
   - Golden file testing across languages

3. **Benchmarking**
   - Compare performance across languages with same datasets
   - Single source of truth for benchmark results
   - Easier to track performance regressions

4. **Documentation**
   - Single place for protocol documentation
   - Easier to keep docs in sync with code
   - Better for users who work with multiple languages

5. **Developer Experience**
   - Clone once, work on any language
   - Consistent tooling and scripts
   - Easier code reviews across languages

### Disadvantages and Mitigations

| Disadvantage | Mitigation |
|--------------|------------|
| Large repo size | Use Git LFS for binary test data |
| Complex CI/CD | Use path filters to only test changed implementations |
| Different build systems | Each implementation has its own build config |
| Release complexity | Use independent versioning per language package |

## Alternative: Polyrepo

If a monorepo doesn't work for your organization, use this structure:

```
protozstd-spec/                        # Specification repository
├── PROTOCOL.md
├── WIRE_FORMAT.md
├── proto/
└── test-data/

protozstd-python/                      # Python implementation
protozstd-java/                        # Java implementation
protozstd-go/                          # Go implementation
protozstd-js/                          # JavaScript implementation
protozstd-csharp/                      # C# implementation
```

**Trade-offs:**
- ✅ Smaller repositories, easier to navigate
- ✅ Language-specific CI/CD
- ❌ Protocol updates require coordinating multiple PRs
- ❌ Test data duplication or git submodules
- ❌ Harder to keep implementations in sync

## Package Naming Conventions

### Python (PyPI)
```
protozstd
```

### Java (Maven Central)
```xml
<groupId>com.protozstd</groupId>
<artifactId>protozstd</artifactId>
```

### Go (Go modules)
```
github.com/protozstd/protozstd-go
```

### JavaScript (npm)
```
@protozstd/core
```

### C# (NuGet)
```
ProtoZstd
```

## Versioning Strategy

### Protocol Version
- **Major.Minor** (e.g., 1.0, 1.1, 2.0)
- Major: Breaking wire format changes
- Minor: Backward-compatible additions

### Implementation Version
- **SemVer 2.0** (Major.Minor.Patch)
- Independent per language
- Indicates which protocol version(s) are supported

### Dictionary Version
- **SemVer 2.0** (Major.Minor.Patch)
- Major: Schema changes (incompatible)
- Minor: Retrained dictionary (compatible)
- Patch: Metadata/checksum fixes

## Build and Release Process

### Development Workflow
```bash
# 1. Clone repository
git clone https://github.com/yourorg/protozstd.git
cd protozstd

# 2. Set up development environment
./scripts/setup-dev.sh

# 3. Generate proto code
./scripts/generate-protos.sh

# 4. Run tests for specific language
cd implementations/python
pytest

# 5. Run all tests
./scripts/run-tests.sh

# 6. Run benchmarks
./scripts/run-benchmarks.sh
```

### CI/CD Pipeline
```yaml
# .github/workflows/ci.yml
on: [push, pull_request]

jobs:
  test-python:
    if: contains(github.event.paths, 'implementations/python/**')
    # ... Python tests

  test-java:
    if: contains(github.event.paths, 'implementations/java/**')
    # ... Java tests

  # ... other languages

  integration-tests:
    needs: [test-python, test-java, ...]
    # Cross-language integration tests

  benchmarks:
    # Run on PR comments or schedule
    # Compare performance across implementations
```

### Release Process
```bash
# 1. Update CHANGELOG.md
# 2. Tag protocol version
git tag -a v1.0.0 -m "Protocol v1.0.0"

# 3. Release language packages independently
cd implementations/python
python -m build
twine upload dist/*

cd ../java
mvn deploy

# ... etc
```

## Language-Specific Considerations

### Python
- Use `pyproject.toml` for modern packaging
- Type hints throughout
- Support Python 3.8+
- Publish to PyPI

### Java
- Maven for build (consider Gradle support)
- Support Java 11+
- Publish to Maven Central
- Include OSGi metadata

### Go
- Follow Go module conventions
- Use `buf` for proto generation
- Minimal dependencies
- Tag releases with `/implementations/go/v1.0.0`

### JavaScript/TypeScript
- ESM and CommonJS builds
- TypeScript definitions included
- Browser and Node.js support
- Publish to npm

### C#
- .NET Standard 2.0+
- NuGet package
- Support .NET Framework 4.6.1+
- Async/await throughout

## Recommendation Summary

**Use Monorepo** with the structure outlined above for:
- Easier protocol evolution
- Better testing and benchmarking
- Simpler developer experience
- Atomic cross-language changes

**Use path-based CI filtering** to keep CI fast and only test what changed.

**Use independent versioning** for each language package to allow flexibility in releases.

This structure has been successfully used by projects like:
- gRPC
- Protobuf
- FlatBuffers
- Apache Arrow

---

**Next Steps:**
1. Create repository with initial structure
2. Write protocol specification (PROTOCOL.md)
3. Define wire format (WIRE_FORMAT.md)
4. Implement Python reference implementation
5. Set up CI/CD
