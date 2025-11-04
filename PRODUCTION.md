# Production Deployment Guide

How to productionize the Proto + zstd compression system for real-world API services.

## 🏗️ Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                        Client Side                          │
├─────────────────────────────────────────────────────────────┤
│  Application → Compression Middleware → HTTP Client         │
│                      ↓                                       │
│         [JSON → Proto → zstd + Dictionary]                  │
│                      ↓                                       │
│         Headers: Content-Type, Content-Encoding             │
└─────────────────────────────────────────────────────────────┘
                           ↓ HTTPS
┌─────────────────────────────────────────────────────────────┐
│                        Server Side                          │
├─────────────────────────────────────────────────────────────┤
│  Load Balancer → API Gateway → Decompression Middleware     │
│                                        ↓                     │
│                      [zstd → Proto → JSON]                  │
│                                        ↓                     │
│                               Application Logic             │
└─────────────────────────────────────────────────────────────┘
```

## 🎯 Key Production Considerations

### 1. Dictionary Management

**Challenges:**
- Dictionary versioning across clients
- Rolling updates without breaking compatibility
- Dictionary distribution and caching
- Training on production data

**Solutions:**
- Use dictionary version in headers
- Maintain backward compatibility for N-1 versions
- CDN distribution for dictionaries
- Periodic retraining with anonymized production samples

### 2. Error Handling

**Must Handle:**
- Corrupted compressed data
- Missing dictionaries
- Version mismatches
- Protobuf schema evolution
- Fallback to JSON+gzip

### 3. Performance

**Optimizations:**
- Dictionary caching (in-memory)
- Connection pooling
- Async compression for large payloads
- CPU core affinity for compression threads

### 4. Monitoring

**Key Metrics:**
- Compression ratio (bytes_saved / bytes_original)
- Compression latency (p50, p95, p99)
- Error rates (by type)
- Dictionary hit rate
- CPU usage
- Memory usage

### 5. Security

**Considerations:**
- Dictionary poisoning attacks
- Compression bombs (zip bombs)
- Size limits on compressed/decompressed data
- Dictionary access control
- Secure dictionary distribution

## 📦 Production-Ready Implementation

See `production/` directory for:
- `middleware.py` - HTTP middleware with error handling
- `dictionary_manager.py` - Dictionary versioning and caching
- `metrics.py` - Prometheus/StatsD metrics
- `client.py` - Production client SDK
- `server.py` - FastAPI/Flask integration

## 🚀 Deployment Strategy

### Phase 1: Canary Deployment (1% traffic)
```
1. Deploy server with compression support (optional)
2. Enable on 1% of clients
3. Monitor for 48-72 hours
4. Check: error rates, latency, bandwidth savings
```

### Phase 2: Gradual Rollout (1% → 10% → 50% → 100%)
```
1. Increase to 10% if metrics look good
2. Monitor for another 48 hours
3. Ramp up: 25% → 50% → 75% → 100%
4. Each step: wait 24-48 hours, monitor metrics
```

### Phase 3: Optimization
```
1. Retrain dictionary on production data
2. Measure compression improvement
3. A/B test different dictionary sizes
4. Fine-tune zstd compression levels
```

## 🔧 Configuration

### Client Configuration
```yaml
compression:
  enabled: true
  algorithm: "proto-zstd"
  dictionary:
    url: "https://cdn.example.com/dict/v1.0.0.zdict"
    cache_ttl: 86400  # 24 hours
    version: "1.0.0"
  fallback:
    enabled: true
    algorithm: "gzip"  # Fall back to gzip on errors
  limits:
    max_payload_size: 10485760  # 10MB
    max_decompressed_size: 52428800  # 50MB
  timeout_ms: 1000
```

### Server Configuration
```yaml
compression:
  enabled: true
  supported_algorithms:
    - "proto-zstd"
    - "gzip"
    - "identity"
  dictionary:
    path: "/etc/api/dictionaries/"
    supported_versions:
      - "1.0.0"
      - "0.9.0"  # Support N-1 version
  limits:
    max_compressed_size: 10485760  # 10MB
    max_decompressed_size: 52428800  # 50MB
  monitoring:
    metrics_enabled: true
    sample_rate: 1.0  # 100% sampling
```

## 📊 Monitoring Dashboard

### Essential Metrics

**Compression Metrics:**
```
compression_ratio{endpoint="POST /orders", version="1.0.0"}
compression_latency_seconds{operation="encode", quantile="0.95"}
compression_errors_total{error_type="dictionary_missing"}
bandwidth_saved_bytes_total{endpoint="POST /orders"}
```

**Performance Metrics:**
```
http_request_duration_seconds{compressed="true"}
http_request_size_bytes{encoding="proto-zstd"}
http_response_size_bytes{encoding="proto-zstd"}
cpu_usage_percent{component="compression"}
memory_usage_bytes{component="dictionary_cache"}
```

**Alerts:**
```
# Alert if compression error rate > 1%
ALERT CompressionErrors
  IF rate(compression_errors_total[5m]) > 0.01
  FOR 5m

# Alert if compression latency > 10ms p95
ALERT SlowCompression
  IF compression_latency_seconds{quantile="0.95"} > 0.01
  FOR 5m

# Alert if dictionary cache miss rate > 10%
ALERT DictionaryCacheMiss
  IF rate(dictionary_cache_misses[5m]) / rate(dictionary_lookups[5m]) > 0.1
  FOR 5m
```

## 🧪 Testing Strategy

### Unit Tests
- Compression/decompression round-trip
- Error handling (corrupted data, missing dict)
- Dictionary versioning
- Size limits enforcement

### Integration Tests
- End-to-end client-server flow
- Dictionary updates
- Fallback to gzip
- Schema evolution

### Load Tests
```bash
# Using k6 or Apache Bench
k6 run --vus 100 --duration 5m compression_load_test.js

# Metrics to collect:
# - Requests/sec (with vs without compression)
# - p50, p95, p99 latency
# - Error rate
# - Bandwidth usage
```

### Chaos Testing
- Dictionary server down → Should fall back to gzip
- Corrupt dictionary → Should detect and use fallback
- Version mismatch → Should gracefully handle
- Memory pressure → Should not OOM

## 🔄 Dictionary Lifecycle

### Training Pipeline
```
Production Data → Sampling (anonymized) → Training → Validation → Deployment
     ↓                                                                ↓
  Every 24h                                                   Version bump
                                                                      ↓
                                                            Canary → Rollout
```

### Training Script
```bash
# Run nightly at 2 AM
0 2 * * * /opt/api/scripts/train_dictionary.sh

# Script:
# 1. Sample last 24h of production traffic
# 2. Anonymize sensitive data
# 3. Train new dictionary
# 4. Validate compression ratio improvement > 5%
# 5. If valid: version bump and deploy to CDN
# 6. Monitor canary deployment
```

### Versioning Strategy
```
Semantic Versioning: MAJOR.MINOR.PATCH

MAJOR: Breaking changes (schema changes)
MINOR: New fields, backward compatible
PATCH: Dictionary retraining, no schema changes

Example:
1.0.0 → 1.0.1 (retrained dict)
1.0.1 → 1.1.0 (new optional field added)
1.1.0 → 2.0.0 (field removed, breaking change)
```

## 🌐 Multi-Region Deployment

### Dictionary Distribution
```
Primary Region (us-east-1):
  - Train dictionaries
  - Push to S3/CDN

Other Regions:
  - Pull from CDN
  - Cache locally
  - TTL: 24 hours
  - Background refresh
```

### Considerations
- CDN caching (CloudFront, Cloudflare)
- Regional failover
- Dictionary sync lag (eventual consistency OK)
- Version skew handling

## 💾 Resource Requirements

### Server Requirements (per instance)
```
CPU: 2-4 cores (for compression threads)
Memory: 512MB - 1GB (for dictionary cache + buffers)
Disk: Minimal (<100MB for dictionaries)
Network: Standard (compression reduces outbound)
```

### Client Requirements
```
Memory: ~150MB (dictionary + compression buffers)
CPU: Minimal (sub-ms compression on modern CPUs)
Storage: ~100MB (dictionary cache)
```

## 🔒 Security Best Practices

### 1. Input Validation
```python
# Max payload sizes
MAX_COMPRESSED_SIZE = 10 * 1024 * 1024  # 10MB
MAX_DECOMPRESSED_SIZE = 50 * 1024 * 1024  # 50MB

# Validate before decompression
if len(compressed_data) > MAX_COMPRESSED_SIZE:
    raise PayloadTooLarge()

# Validate after decompression
decompressed = decompress(compressed_data)
if len(decompressed) > MAX_DECOMPRESSED_SIZE:
    raise DecompressionBomb()
```

### 2. Dictionary Integrity
```python
# Sign dictionaries
dictionary_hash = sha256(dictionary_bytes).hexdigest()

# Verify on load
if sha256(loaded_dict).hexdigest() != expected_hash:
    raise DictionaryCorrupted()
```

### 3. Rate Limiting
```
Limit compression errors per client:
- 10 errors/minute → Warning
- 100 errors/minute → Throttle
- 1000 errors/minute → Block
```

## 📈 Cost-Benefit Analysis

### Benefits
```
Bandwidth Savings:
  - 75-82% reduction
  - At 1TB/month: $30/month → $7/month (AWS)
  - ROI: $23/month per TB

Latency Improvement:
  - Smaller payloads = faster transfers
  - On 3G network: 356 bytes @ 1.5Mbps = 2ms
  - With compression: 63 bytes @ 1.5Mbps = 0.3ms
  - Savings: 1.7ms per request

User Experience:
  - Faster page loads
  - Better mobile experience
  - Reduced data plan usage
```

### Costs
```
Engineering:
  - Initial implementation: 2-4 weeks
  - Maintenance: 1-2 days/month

Infrastructure:
  - CPU overhead: +5-10% per instance
  - Memory: +512MB per instance
  - CDN: ~$1-5/month for dictionary distribution

Monitoring:
  - Metrics storage: ~$10-20/month
```

**Net Benefit:** Positive ROI at >100GB/month traffic

## 🎯 Migration Checklist

### Pre-deployment
- [ ] Implement compression middleware
- [ ] Add monitoring/metrics
- [ ] Set up dictionary CDN
- [ ] Create runbooks for incidents
- [ ] Load test at 2x expected traffic
- [ ] Train production dictionary
- [ ] Test fallback mechanisms
- [ ] Document API changes

### Deployment
- [ ] Deploy server-side support (optional mode)
- [ ] Enable for 1% of clients
- [ ] Monitor for 48 hours
- [ ] Gradual rollout to 100%
- [ ] Monitor compression metrics
- [ ] Optimize based on data

### Post-deployment
- [ ] Set up alerting
- [ ] Create compression dashboard
- [ ] Schedule dictionary retraining
- [ ] Document lessons learned
- [ ] Optimize compression settings
- [ ] Plan for schema evolution

## 📚 Additional Resources

- [Implementation Examples](./production/) - Production-ready code
- [API Specification](./API.md) - HTTP headers and protocols
- [Troubleshooting Guide](./TROUBLESHOOTING.md) - Common issues
- [Performance Tuning](./TUNING.md) - Optimization guide

---

**Next Steps:** See `production/` directory for production-ready implementation code.
