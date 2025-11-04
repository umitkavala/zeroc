"""
Production dictionary manager with versioning, caching, and CDN support.
"""
import hashlib
import os
import time
from typing import Optional, Dict
from pathlib import Path
import zstandard as zstd
import requests
from threading import Lock
import logging

logger = logging.getLogger(__name__)


class DictionaryManager:
    """
    Manages compression dictionaries with versioning, caching, and CDN distribution.

    Features:
    - Version-based dictionary loading
    - In-memory caching with TTL
    - CDN/HTTP download with fallback
    - Integrity verification (SHA-256)
    - Thread-safe operations
    """

    def __init__(
        self,
        cache_dir: str = "/tmp/compression_dicts",
        cdn_base_url: Optional[str] = None,
        cache_ttl: int = 86400,  # 24 hours
        max_cache_size: int = 5  # Max number of versions to cache
    ) -> None:
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        self.cdn_base_url = cdn_base_url
        self.cache_ttl = cache_ttl
        self.max_cache_size = max_cache_size

        # In-memory cache: {version: (dict_data, timestamp, compressor, decompressor)}
        self._cache: Dict[str, tuple] = {}
        self._lock = Lock()

        logger.info(f"DictionaryManager initialized: cache_dir={cache_dir}, ttl={cache_ttl}s")

    def get_compressor(self, version: str) -> zstd.ZstdCompressor:
        """Get a compressor for the specified dictionary version."""
        dict_data = self._get_dictionary(version)

        with self._lock:
            cached = self._cache.get(version)
            if cached and cached[2]:  # Compressor exists
                return cached[2]

            compressor = zstd.ZstdCompressor(dict_data=dict_data)
            self._update_cache(version, dict_data, compressor=compressor)
            return compressor

    def get_decompressor(self, version: str) -> zstd.ZstdDecompressor:
        """Get a decompressor for the specified dictionary version."""
        dict_data = self._get_dictionary(version)

        with self._lock:
            cached = self._cache.get(version)
            if cached and cached[3]:  # Decompressor exists
                return cached[3]

            decompressor = zstd.ZstdDecompressor(dict_data=dict_data)
            self._update_cache(version, dict_data, decompressor=decompressor)
            return decompressor

    def _get_dictionary(self, version: str) -> zstd.ZstdCompressionDict:
        """Get dictionary data, using cache or downloading if necessary."""
        # Check in-memory cache first
        with self._lock:
            cached = self._cache.get(version)
            if cached:
                dict_data, timestamp, _, _ = cached
                if time.time() - timestamp < self.cache_ttl:
                    logger.debug(f"Dictionary {version} found in memory cache")
                    return dict_data
                else:
                    logger.debug(f"Dictionary {version} cache expired")

        # Check disk cache
        disk_path = self.cache_dir / f"dict_{version}.zdict"
        if disk_path.exists():
            age = time.time() - disk_path.stat().st_mtime
            if age < self.cache_ttl:
                logger.debug(f"Loading dictionary {version} from disk")
                return self._load_from_disk(disk_path, version)
            else:
                logger.debug(f"Disk cache for {version} expired (age={age:.0f}s)")

        # Download from CDN
        if self.cdn_base_url:
            try:
                return self._download_dictionary(version)
            except Exception as e:
                logger.error(f"Failed to download dictionary {version}: {e}")
                # Fall through to check if we have any cached version
                if disk_path.exists():
                    logger.warning(f"Using expired cached dictionary {version}")
                    return self._load_from_disk(disk_path, version)
                raise

        raise FileNotFoundError(f"Dictionary version {version} not found")

    def _load_from_disk(self, path: Path, version: str) -> zstd.ZstdCompressionDict:
        """Load dictionary from disk and update cache."""
        with open(path, 'rb') as f:
            data = f.read()

        dict_data = zstd.ZstdCompressionDict(data)

        with self._lock:
            self._update_cache(version, dict_data)

        return dict_data

    def _download_dictionary(self, version: str) -> zstd.ZstdCompressionDict:
        """Download dictionary from CDN."""
        url = f"{self.cdn_base_url}/dict_{version}.zdict"
        checksum_url = f"{self.cdn_base_url}/dict_{version}.zdict.sha256"

        logger.info(f"Downloading dictionary {version} from {url}")

        # Download dictionary
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        dict_bytes = response.content

        # Download and verify checksum
        try:
            checksum_response = requests.get(checksum_url, timeout=10)
            checksum_response.raise_for_status()
            expected_hash = checksum_response.text.strip()

            actual_hash = hashlib.sha256(dict_bytes).hexdigest()
            if actual_hash != expected_hash:
                raise ValueError(
                    f"Dictionary checksum mismatch: expected={expected_hash}, actual={actual_hash}"
                )
            logger.info(f"Dictionary {version} checksum verified")
        except requests.RequestException as e:
            logger.warning(f"Could not verify checksum for {version}: {e}")

        # Save to disk
        disk_path = self.cache_dir / f"dict_{version}.zdict"
        with open(disk_path, 'wb') as f:
            f.write(dict_bytes)
        logger.info(f"Dictionary {version} saved to {disk_path}")

        # Create dictionary object
        dict_data = zstd.ZstdCompressionDict(dict_bytes)

        # Update cache
        with self._lock:
            self._update_cache(version, dict_data)

        return dict_data

    def _update_cache(
        self,
        version: str,
        dict_data: zstd.ZstdCompressionDict,
        compressor: Optional[zstd.ZstdCompressor] = None,
        decompressor: Optional[zstd.ZstdDecompressor] = None
    ) -> None:
        """Update in-memory cache (assumes lock is held)."""
        # Get existing cached items or create new entry
        existing = self._cache.get(version)
        if existing:
            _, _, existing_comp, existing_decomp = existing
            compressor = compressor or existing_comp
            decompressor = decompressor or existing_decomp

        self._cache[version] = (dict_data, time.time(), compressor, decompressor)

        # Evict old entries if cache is too large
        if len(self._cache) > self.max_cache_size:
            # Remove oldest entry
            oldest_version = min(self._cache.keys(), key=lambda k: self._cache[k][1])
            del self._cache[oldest_version]
            logger.debug(f"Evicted dictionary {oldest_version} from cache")

    def preload_version(self, version: str) -> None:
        """Preload a dictionary version into cache."""
        logger.info(f"Preloading dictionary version {version}")
        self.get_compressor(version)
        self.get_decompressor(version)

    def clear_cache(self) -> None:
        """Clear in-memory cache."""
        with self._lock:
            self._cache.clear()
        logger.info("Dictionary cache cleared")

    def get_cache_stats(self) -> Dict[str, int]:
        """Get cache statistics."""
        with self._lock:
            return {
                "cached_versions": len(self._cache),
                "cache_size_bytes": sum(
                    len(item[0]) for item in self._cache.values()
                )
            }


# Singleton instance for easy access
_default_manager: Optional[DictionaryManager] = None


def get_dictionary_manager(**kwargs) -> DictionaryManager:
    """Get the default dictionary manager instance."""
    global _default_manager
    if _default_manager is None:
        _default_manager = DictionaryManager(**kwargs)
    return _default_manager
