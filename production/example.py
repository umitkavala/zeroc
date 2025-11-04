"""
End-to-end example of production compression system.

This example demonstrates:
1. Client making compressed requests
2. Server receiving and decompressing requests
3. Metrics collection
4. Error handling
"""
import asyncio
import logging
from typing import Dict, Any

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def example_client() -> None:
    """Example of using the compression client."""
    from production import CompressedAPIClient, CompressionConfig, MetricsBackend

    logger.info("=== CLIENT EXAMPLE ===")

    # Configure compression
    config = CompressionConfig(
        enabled=True,
        dictionary_version="1.0.0",
        cdn_url="https://cdn.example.com/dicts",  # In production: real CDN
        fallback_to_gzip=True,
        max_payload_size=10 * 1024 * 1024
    )

    # Create client
    client = CompressedAPIClient(
        base_url="http://localhost:8000",
        compression_config=config,
        metrics_backend=MetricsBackend.NOOP  # Use PROMETHEUS in production
    )

    # Example 1: Create an order
    logger.info("Sending compressed order...")

    order_data = {
        "order_id": "ORD-12345",
        "user_id": 1001,
        "timestamp": 1704067200,
        "items": [
            {"product_id": 42, "quantity": 2, "price": 29.99},
            {"product_id": 101, "quantity": 1, "price": 49.99}
        ],
        "shipping_address": {
            "street": "123 Main St",
            "city": "New York",
            "postal_code": "10001",
            "country": "USA"
        },
        "payment_method": "credit_card",
        "total_amount": 109.97
    }

    try:
        response = client.post(
            endpoint="/orders",
            data=order_data,
            data_type="order",
            timeout=30
        )
        logger.info(f"Order response: {response}")

    except Exception as e:
        logger.error(f"Error creating order: {e}")

    # Example 2: Track product view
    logger.info("Sending compressed product view...")

    view_data = {
        "user_id": 1001,
        "product_id": 42,
        "timestamp": 1704067200,
        "referrer": "google",
        "device_type": "mobile"
    }

    try:
        response = client.post(
            endpoint="/product_views",
            data=view_data,
            data_type="product_view"
        )
        logger.info(f"Product view response: {response}")

    except Exception as e:
        logger.error(f"Error tracking product view: {e}")

    # Example 3: Search request
    logger.info("Sending compressed search request...")

    search_data = {
        "user_id": 1001,
        "query": "laptop",
        "timestamp": 1704067200,
        "page": 1,
        "limit": 20,
        "filters": ["price_low_to_high", "rating"]
    }

    try:
        response = client.post(
            endpoint="/search",
            data=search_data,
            data_type="search"
        )
        logger.info(f"Search response: {response}")

    except Exception as e:
        logger.error(f"Error searching: {e}")

    client.close()
    logger.info("Client example completed")


def example_server() -> None:
    """Example of running the compression server."""
    from production import create_compression_app, CompressionConfig, MetricsBackend

    logger.info("=== SERVER EXAMPLE ===")

    # Create app with compression
    app = create_compression_app(
        compression_config=CompressionConfig(
            enabled=True,
            dictionary_version="1.0.0",
            fallback_to_gzip=True
        ),
        metrics_backend=MetricsBackend.PROMETHEUS  # Exposes /metrics endpoint
    )

    logger.info("Server created. Run with: uvicorn production.example:app")
    logger.info("Endpoints available:")
    logger.info("  - POST /orders")
    logger.info("  - POST /product_views")
    logger.info("  - POST /search")
    logger.info("  - GET /health")
    logger.info("  - GET /metrics (Prometheus)")

    return app


def example_metrics() -> None:
    """Example of using metrics directly."""
    from production import get_metrics, MetricsBackend, CompressionTimer

    logger.info("=== METRICS EXAMPLE ===")

    # Initialize metrics (using NOOP for example)
    metrics = get_metrics(backend=MetricsBackend.NOOP)

    # Example 1: Record compression manually
    logger.info("Recording compression metrics...")

    metrics.record_compression(
        original_size=1000,
        compressed_size=250,
        latency_seconds=0.002,
        endpoint="/orders",
        version="1.0.0",
        operation="encode"
    )

    # Example 2: Use timer context manager
    logger.info("Using compression timer...")

    with CompressionTimer(
        metrics,
        operation="encode",
        endpoint="/orders",
        version="1.0.0"
    ) as timer:
        # Simulate compression
        import time
        time.sleep(0.001)

        timer.set_sizes(original_size=1000, compressed_size=250)

    # Example 3: Record errors
    logger.info("Recording error metrics...")

    metrics.record_error(
        error_type="dictionary_missing",
        endpoint="/orders"
    )

    # Example 4: Record cache hits/misses
    metrics.record_cache_hit(version="1.0.0")
    metrics.record_cache_miss(version="1.1.0")

    logger.info("Metrics example completed")


def example_dictionary_manager() -> None:
    """Example of dictionary manager usage."""
    from production import DictionaryManager

    logger.info("=== DICTIONARY MANAGER EXAMPLE ===")

    # Create manager
    manager = DictionaryManager(
        cache_dir="/tmp/compression_dicts",
        cdn_base_url="https://cdn.example.com/dicts",  # In production: real CDN
        cache_ttl=86400,  # 24 hours
        max_cache_size=5   # Keep 5 versions
    )

    logger.info("Dictionary manager created")

    # Get compressor
    try:
        logger.info("Getting compressor for version 1.0.0...")
        # Note: This will try to download from CDN if not cached
        # For this example to work, you'd need a real CDN or local dict file
        # compressor = manager.get_compressor("1.0.0")
        # logger.info("Compressor obtained")

    except Exception as e:
        logger.warning(f"Could not get compressor: {e}")

    # Get cache stats
    stats = manager.get_cache_stats()
    logger.info(f"Cache stats: {stats}")

    # Preload version (for production warm-up)
    # manager.preload_version("1.0.0")

    logger.info("Dictionary manager example completed")


def example_error_handling() -> None:
    """Example of error handling."""
    from production import (
        CompressedAPIClient,
        CompressionConfig,
        CompressionError,
        PayloadTooLarge,
        DecompressionBomb,
        DictionaryNotFound
    )

    logger.info("=== ERROR HANDLING EXAMPLE ===")

    config = CompressionConfig(
        max_payload_size=1000,  # Very small for demo
        max_decompressed_size=5000
    )

    client = CompressedAPIClient(
        base_url="http://localhost:8000",
        compression_config=config
    )

    # Example 1: Payload too large
    logger.info("Testing payload too large...")

    large_order = {
        "order_id": "ORD-99999",
        "user_id": 1001,
        "timestamp": 1704067200,
        "items": [{"product_id": i, "quantity": 1, "price": 10.0} for i in range(1000)],
        "shipping_address": {
            "street": "123 Main St",
            "city": "New York",
            "postal_code": "10001",
            "country": "USA"
        },
        "payment_method": "credit_card",
        "total_amount": 10000.0
    }

    try:
        client.post("/orders", data=large_order, data_type="order")
    except PayloadTooLarge:
        logger.info("✓ PayloadTooLarge caught correctly")
    except Exception as e:
        logger.warning(f"Unexpected error: {e}")

    # Example 2: Dictionary not found
    logger.info("Testing dictionary not found...")

    bad_config = CompressionConfig(
        dictionary_version="99.99.99",  # Non-existent
        fallback_to_gzip=False  # Disable fallback
    )

    bad_client = CompressedAPIClient(
        base_url="http://localhost:8000",
        compression_config=bad_config
    )

    try:
        small_order = {
            "order_id": "ORD-123",
            "user_id": 1001,
            "timestamp": 1704067200,
            "items": [],
            "shipping_address": {
                "street": "123 Main St",
                "city": "New York",
                "postal_code": "10001",
                "country": "USA"
            },
            "payment_method": "credit_card",
            "total_amount": 0.0
        }
        bad_client.post("/orders", data=small_order, data_type="order")
    except (DictionaryNotFound, CompressionError) as e:
        logger.info(f"✓ Dictionary error caught: {type(e).__name__}")
    except Exception as e:
        logger.warning(f"Unexpected error: {e}")

    logger.info("Error handling example completed")


if __name__ == "__main__":
    logger.info("Production Compression System - Examples")
    logger.info("=" * 60)

    # Run examples
    example_metrics()
    print()

    example_dictionary_manager()
    print()

    example_error_handling()
    print()

    # Note: Client example requires server to be running
    # To run client example:
    # 1. In terminal 1: uvicorn production.example:app --reload
    # 2. In terminal 2: python production/example.py
    # example_client()

    logger.info("All examples completed!")
    logger.info("")
    logger.info("To run server:")
    logger.info("  uvicorn production.example:example_server --reload")
    logger.info("")
    logger.info("Then run client in another terminal:")
    logger.info("  python -c 'from production.example import example_client; example_client()'")

# Export app for uvicorn
app = example_server()
