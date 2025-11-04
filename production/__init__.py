"""
Production-ready compression middleware for API services.

Example usage:

Client:
    from production import CompressedAPIClient, CompressionConfig

    config = CompressionConfig(
        dictionary_version="1.0.0",
        cdn_url="https://cdn.example.com/dicts"
    )

    with CompressedAPIClient("https://api.example.com", config) as client:
        response = client.post("/orders", data=order_data, data_type="order")

Server (FastAPI):
    from production import create_compression_app

    app = create_compression_app()

Server (Flask):
    from production import create_flask_compression_app

    app = create_flask_compression_app()
"""

from .middleware import (
    CompressionMiddleware,
    CompressionConfig,
    CompressionError,
    PayloadTooLarge,
    DecompressionBomb,
    DictionaryNotFound
)

from .dictionary_manager import (
    DictionaryManager,
    get_dictionary_manager
)

from .metrics import (
    CompressionMetrics,
    CompressionTimer,
    MetricsBackend,
    get_metrics
)

from .client import CompressedAPIClient

from .server import (
    create_compression_app,
    create_flask_compression_app
)

__all__ = [
    # Middleware
    'CompressionMiddleware',
    'CompressionConfig',
    'CompressionError',
    'PayloadTooLarge',
    'DecompressionBomb',
    'DictionaryNotFound',

    # Dictionary Management
    'DictionaryManager',
    'get_dictionary_manager',

    # Metrics
    'CompressionMetrics',
    'CompressionTimer',
    'MetricsBackend',
    'get_metrics',

    # Client
    'CompressedAPIClient',

    # Server
    'create_compression_app',
    'create_flask_compression_app',
]

__version__ = '1.0.0'
