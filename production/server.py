"""
Production server integration with FastAPI.
Demonstrates compression middleware on the server side.
"""
from typing import Any, Dict, Callable
import logging
from functools import wraps

from fastapi import FastAPI, Request, Response, HTTPException
from fastapi.responses import JSONResponse

from .middleware import (
    CompressionMiddleware,
    CompressionConfig,
    CompressionError,
    PayloadTooLarge,
    DecompressionBomb
)
from .metrics import MetricsBackend, get_metrics

logger = logging.getLogger(__name__)


def create_compression_app(
    compression_config: Optional[CompressionConfig] = None,  # type: ignore
    metrics_backend: MetricsBackend = MetricsBackend.PROMETHEUS
) -> FastAPI:
    """
    Create FastAPI app with compression middleware.

    Args:
        compression_config: Compression configuration
        metrics_backend: Metrics backend to use

    Returns:
        Configured FastAPI app
    """
    app = FastAPI(title="Compressed API", version="1.0.0")

    # Initialize compression
    config = compression_config or CompressionConfig(
        enabled=True,
        dictionary_version="1.0.0",
        fallback_to_gzip=True
    )

    metrics = get_metrics(backend=metrics_backend) if config.metrics_enabled else None
    compression = CompressionMiddleware(config=config, metrics=metrics)

    @app.middleware("http")
    async def compression_middleware(request: Request, call_next: Callable) -> Response:  # type: ignore
        """Middleware to handle compression/decompression."""
        # Decompress request if compressed
        if request.method in ["POST", "PUT", "PATCH"]:
            content_encoding = request.headers.get("Content-Encoding", "identity")

            if content_encoding != "identity":
                try:
                    # Read request body
                    body = await request.body()

                    # Decompress
                    decompressed = compression.decompress_response(
                        compressed_data=body,
                        headers=dict(request.headers),
                        endpoint=request.url.path
                    )

                    # Store decompressed data in request state
                    request.state.decompressed_data = decompressed

                except CompressionError as e:
                    logger.error(f"Decompression failed: {e}")
                    return JSONResponse(
                        status_code=400,
                        content={"error": "Invalid compressed data"}
                    )

        # Process request
        response = await call_next(request)

        # Compress response if client accepts it
        accept_encoding = request.headers.get("Accept-Encoding", "")
        if "proto-zstd" in accept_encoding or "gzip" in accept_encoding:
            # Check if response is JSON
            content_type = response.headers.get("Content-Type", "")
            if "application/json" in content_type:
                # Note: In production, you'd need to read the response body
                # and re-compress it. This is simplified for the example.
                logger.debug("Response compression would happen here")

        return response

    # Health check endpoint
    @app.get("/health")
    async def health() -> Dict[str, str]:
        """Health check endpoint."""
        return {"status": "healthy"}

    # Metrics endpoint
    @app.get("/metrics")
    async def metrics_endpoint() -> Response:
        """Prometheus metrics endpoint."""
        try:
            from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
            return Response(
                content=generate_latest(),
                media_type=CONTENT_TYPE_LATEST
            )
        except ImportError:
            return JSONResponse(
                status_code=501,
                content={"error": "Prometheus metrics not available"}
            )

    # Example endpoints
    @app.post("/orders")
    async def create_order(request: Request) -> Dict[str, Any]:
        """Create an order (example endpoint)."""
        # Get decompressed data if available
        if hasattr(request.state, "decompressed_data"):
            order_data = request.state.decompressed_data
        else:
            # Parse JSON from body
            body = await request.body()
            import json
            order_data = json.loads(body)

        # Process order (simplified)
        logger.info(f"Creating order: {order_data.get('order_id')}")

        # Return response
        return {
            "status": "created",
            "order_id": order_data.get("order_id"),
            "message": "Order created successfully"
        }

    @app.post("/product_views")
    async def track_product_view(request: Request) -> Dict[str, Any]:
        """Track product view (example endpoint)."""
        if hasattr(request.state, "decompressed_data"):
            view_data = request.state.decompressed_data
        else:
            body = await request.body()
            import json
            view_data = json.loads(body)

        logger.info(f"Tracking product view: user={view_data.get('user_id')}, product={view_data.get('product_id')}")

        return {
            "status": "tracked",
            "message": "Product view tracked"
        }

    @app.post("/search")
    async def search(request: Request) -> Dict[str, Any]:
        """Search endpoint (example)."""
        if hasattr(request.state, "decompressed_data"):
            search_data = request.state.decompressed_data
        else:
            body = await request.body()
            import json
            search_data = json.loads(body)

        query = search_data.get("query", "")
        logger.info(f"Search query: {query}")

        # Return mock results
        return {
            "query": query,
            "results": [
                {"id": 1, "name": "Product 1"},
                {"id": 2, "name": "Product 2"}
            ],
            "total": 2
        }

    # Error handlers
    @app.exception_handler(PayloadTooLarge)
    async def payload_too_large_handler(request: Request, exc: PayloadTooLarge) -> JSONResponse:
        """Handle payload too large errors."""
        return JSONResponse(
            status_code=413,
            content={"error": "Payload too large"}
        )

    @app.exception_handler(DecompressionBomb)
    async def decompression_bomb_handler(request: Request, exc: DecompressionBomb) -> JSONResponse:
        """Handle decompression bomb errors."""
        return JSONResponse(
            status_code=400,
            content={"error": "Decompressed payload exceeds size limit"}
        )

    return app


# Flask integration example
def create_flask_compression_app() -> Any:
    """
    Create Flask app with compression middleware (example).

    Returns:
        Configured Flask app
    """
    try:
        from flask import Flask, request, jsonify
    except ImportError:
        logger.error("Flask not installed")
        return None

    app = Flask(__name__)

    # Initialize compression
    config = CompressionConfig(
        enabled=True,
        dictionary_version="1.0.0"
    )
    compression = CompressionMiddleware(config=config)

    @app.before_request
    def decompress_request() -> None:
        """Decompress request if compressed."""
        if request.method in ["POST", "PUT", "PATCH"]:
            content_encoding = request.headers.get("Content-Encoding", "identity")

            if content_encoding != "identity":
                try:
                    decompressed = compression.decompress_response(
                        compressed_data=request.get_data(),
                        headers=dict(request.headers),
                        endpoint=request.path
                    )
                    request.decompressed_data = decompressed  # type: ignore

                except CompressionError as e:
                    logger.error(f"Decompression failed: {e}")
                    return jsonify({"error": "Invalid compressed data"}), 400

    @app.route("/health")
    def health() -> Any:
        """Health check."""
        return jsonify({"status": "healthy"})

    @app.route("/orders", methods=["POST"])
    def create_order() -> Any:
        """Create order endpoint."""
        if hasattr(request, "decompressed_data"):
            order_data = request.decompressed_data  # type: ignore
        else:
            order_data = request.get_json()

        logger.info(f"Creating order: {order_data.get('order_id')}")
        return jsonify({
            "status": "created",
            "order_id": order_data.get("order_id")
        })

    return app


# Run server
if __name__ == "__main__":
    import uvicorn
    import logging

    logging.basicConfig(level=logging.INFO)

    # Create app
    app = create_compression_app(
        compression_config=CompressionConfig(
            enabled=True,
            dictionary_version="1.0.0",
            fallback_to_gzip=True,
            cdn_url="https://cdn.example.com/dicts"
        ),
        metrics_backend=MetricsBackend.PROMETHEUS
    )

    # Run server
    uvicorn.run(app, host="0.0.0.0", port=8000)
