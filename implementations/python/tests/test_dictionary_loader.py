"""
Tests for Zeroc dictionary loader.
"""
import pytest
import struct
import zlib
import hashlib
from pathlib import Path
from zeroc import DictionaryLoader, load_dictionary


@pytest.fixture
def dict_dir(tmp_path):
    """Create temporary dictionary directory."""
    return tmp_path / "dictionaries"


@pytest.fixture
def sample_dictionary(dict_dir):
    """Create a sample valid dictionary file."""
    dict_dir.mkdir(parents=True, exist_ok=True)

    # Create fake zstd dictionary data
    zstd_dict_data = b"FAKE_ZSTD_DICTIONARY_DATA" * 100

    # Calculate dict ID
    dict_id = zlib.crc32(zstd_dict_data) & 0xFFFFFFFF
    if dict_id == 0:
        dict_id = 0x00000001

    # Calculate SHA256 prefix
    sha256_full = hashlib.sha256(zstd_dict_data).digest()
    sha256_prefix = struct.unpack('>Q', sha256_full[:8])[0]

    # Build 132-byte header
    header = struct.pack(
        '>8s12s64sIIQIIIIQQ',
        b'PZSTDICT',                                      # Magic (8 bytes)
        b'1.0.0\x00\x00\x00\x00\x00\x00\x00',            # Version (12 bytes)
        b'ecommerce.v1.Order\x00' * 3,                   # Schema (64 bytes, padded)
        dict_id,                                         # Dictionary ID (4 bytes)
        10000,                                           # Sample count (4 bytes)
        1704067200,                                      # Created timestamp (8 bytes)
        3,                                               # Compression level (4 bytes)
        len(zstd_dict_data),                             # Dictionary size (4 bytes)
        100,                                             # Min protobuf size (4 bytes)
        500,                                             # Max protobuf size (4 bytes)
        sha256_prefix,                                   # SHA256 prefix (8 bytes)
        0                                                # Reserved (8 bytes)
    )

    # Write dictionary file
    dict_path = dict_dir / "test-dict.zdict"
    with open(dict_path, 'wb') as f:
        f.write(header + zstd_dict_data)

    return dict_path


class TestDictionaryFormat:
    """Test dictionary file format parsing."""

    def test_load_valid_dictionary(self, sample_dictionary):
        """Test loading a valid dictionary file."""
        metadata, dict_obj = load_dictionary(str(sample_dictionary))

        assert metadata['version'] == '1.0.0'
        assert metadata['schema_name'].startswith('ecommerce.v1.Order')
        assert metadata['sample_count'] == 10000
        assert metadata['compression_level'] == 3
        assert metadata['min_size'] == 100
        assert metadata['max_size'] == 500
        assert dict_obj is not None

    def test_dictionary_not_found(self):
        """Test loading non-existent dictionary."""
        with pytest.raises(FileNotFoundError):
            load_dictionary("/nonexistent/dict.zdict")

    def test_dictionary_too_small(self, tmp_path):
        """Test loading dictionary that's too small."""
        small_dict = tmp_path / "small.zdict"
        with open(small_dict, 'wb') as f:
            f.write(b"TOO_SHORT")

        with pytest.raises(ValueError, match="Dictionary too small"):
            load_dictionary(str(small_dict))

    def test_invalid_magic(self, tmp_path):
        """Test loading dictionary with invalid magic."""
        bad_dict = tmp_path / "bad.zdict"
        header = b"BADMAGIC" + b"\x00" * 124 + b"X" * 100
        with open(bad_dict, 'wb') as f:
            f.write(header)

        with pytest.raises(ValueError, match="Invalid magic"):
            load_dictionary(str(bad_dict))

    def test_size_mismatch(self, tmp_path):
        """Test dictionary with header/data size mismatch."""
        dict_path = tmp_path / "mismatch.zdict"

        # Header claims 1000 bytes but only provide 100
        zstd_dict_data = b"X" * 100
        dict_id = zlib.crc32(zstd_dict_data) & 0xFFFFFFFF
        if dict_id == 0:
            dict_id = 0x00000001

        sha256_prefix = struct.unpack('>Q', hashlib.sha256(zstd_dict_data).digest()[:8])[0]

        header = struct.pack(
            '>8s12s64sIIQIIIIQQ',
            b'PZSTDICT',
            b'1.0.0\x00\x00\x00\x00\x00\x00\x00',
            b'test\x00' * 16,
            dict_id,
            1000,
            1704067200,
            3,
            1000,  # Claims 1000 bytes
            10,
            100,
            sha256_prefix,
            0
        )

        with open(dict_path, 'wb') as f:
            f.write(header + zstd_dict_data)  # Only 100 bytes

        with pytest.raises(ValueError, match="Dictionary size mismatch"):
            load_dictionary(str(dict_path))

    def test_invalid_dict_id(self, tmp_path):
        """Test dictionary with incorrect ID."""
        dict_path = tmp_path / "bad_id.zdict"

        zstd_dict_data = b"DICTIONARY_DATA"
        wrong_dict_id = 0x99999999  # Wrong ID

        sha256_prefix = struct.unpack('>Q', hashlib.sha256(zstd_dict_data).digest()[:8])[0]

        header = struct.pack(
            '>8s12s64sIIQIIIIQQ',
            b'PZSTDICT',
            b'1.0.0\x00\x00\x00\x00\x00\x00\x00',
            b'test\x00' * 16,
            wrong_dict_id,  # Wrong ID
            1000,
            1704067200,
            3,
            len(zstd_dict_data),
            10,
            100,
            sha256_prefix,
            0
        )

        with open(dict_path, 'wb') as f:
            f.write(header + zstd_dict_data)

        with pytest.raises(ValueError, match="Dictionary ID mismatch"):
            load_dictionary(str(dict_path))


class TestDictionaryLoader:
    """Test DictionaryLoader class with caching."""

    def test_loader_caching(self, sample_dictionary):
        """Test dictionary caching behavior."""
        loader = DictionaryLoader()

        # First load
        meta1, dict1 = loader.load(str(sample_dictionary))

        # Second load should return cached version
        meta2, dict2 = loader.load(str(sample_dictionary))

        # Should be same objects (cached)
        assert meta1 is meta2
        assert dict1 is dict2

    def test_get_compressor(self, sample_dictionary):
        """Test getting compressor from loader."""
        loader = DictionaryLoader()

        compressor = loader.get_compressor(str(sample_dictionary), level=5)

        assert compressor is not None
        # Verify it can compress
        compressed = compressor.compress(b"test data")
        assert isinstance(compressed, bytes)

    def test_get_decompressor(self, sample_dictionary):
        """Test getting decompressor from loader."""
        loader = DictionaryLoader()

        compressor = loader.get_compressor(str(sample_dictionary))
        decompressor = loader.get_decompressor(str(sample_dictionary))

        # Round trip test
        original = b"test data to compress"
        compressed = compressor.compress(original)
        decompressed = decompressor.decompress(compressed)

        assert decompressed == original

    def test_clear_cache(self, sample_dictionary):
        """Test clearing dictionary cache."""
        loader = DictionaryLoader()

        # Load and cache
        loader.load(str(sample_dictionary))
        assert len(loader._cache) == 1

        # Clear cache
        loader.clear_cache()
        assert len(loader._cache) == 0

    def test_multiple_dictionaries(self, dict_dir):
        """Test loading multiple different dictionaries."""
        loader = DictionaryLoader()

        # Create two different dictionaries
        dict_paths = []
        for i in range(2):
            zstd_dict_data = f"DICT_{i}_DATA".encode() * 100
            dict_id = zlib.crc32(zstd_dict_data) & 0xFFFFFFFF
            if dict_id == 0:
                dict_id = 0x00000001

            sha256_prefix = struct.unpack('>Q', hashlib.sha256(zstd_dict_data).digest()[:8])[0]

            header = struct.pack(
                '>8s12s64sIIQIIIIQQ',
                b'PZSTDICT',
                f'{i}.0.0'.encode().ljust(12, b'\x00'),
                f'schema.v{i}'.encode().ljust(64, b'\x00'),
                dict_id,
                1000,
                1704067200,
                3,
                len(zstd_dict_data),
                10,
                100,
                sha256_prefix,
                0
            )

            dict_path = dict_dir / f"dict{i}.zdict"
            dict_dir.mkdir(parents=True, exist_ok=True)
            with open(dict_path, 'wb') as f:
                f.write(header + zstd_dict_data)

            dict_paths.append(str(dict_path))

        # Load both
        meta1, _ = loader.load(dict_paths[0])
        meta2, _ = loader.load(dict_paths[1])

        # Verify they're different
        assert meta1['version'] != meta2['version']
        assert meta1['schema_name'] != meta2['schema_name']

        # Verify both are cached
        assert len(loader._cache) == 2


class TestRealDictionaries:
    """Test with real trained dictionaries if available."""

    def test_load_order_dictionary(self):
        """Test loading the trained Order dictionary."""
        dict_path = Path(__file__).parent.parent.parent.parent / "dictionaries" / "formats" / "Order-1.0.0.zdict"

        if not dict_path.exists():
            pytest.skip("Order dictionary not found")

        metadata, dict_obj = load_dictionary(str(dict_path))

        assert metadata['version'] == '1.0.0'
        assert 'Order' in metadata['schema_name']
        assert metadata['dictionary_id'] == 0x6b2f8960
        assert dict_obj is not None

    def test_load_product_view_dictionary(self):
        """Test loading the trained ProductView dictionary."""
        dict_path = Path(__file__).parent.parent.parent.parent / "dictionaries" / "formats" / "ProductView-1.0.0.zdict"

        if not dict_path.exists():
            pytest.skip("ProductView dictionary not found")

        metadata, dict_obj = load_dictionary(str(dict_path))

        assert metadata['version'] == '1.0.0'
        assert 'ProductView' in metadata['schema_name']
        assert metadata['dictionary_id'] == 0x95d80527

    def test_load_search_dictionary(self):
        """Test loading the trained SearchRequest dictionary."""
        dict_path = Path(__file__).parent.parent.parent.parent / "dictionaries" / "formats" / "SearchRequest-1.0.0.zdict"

        if not dict_path.exists():
            pytest.skip("SearchRequest dictionary not found")

        metadata, dict_obj = load_dictionary(str(dict_path))

        assert metadata['version'] == '1.0.0'
        assert 'Search' in metadata['schema_name']
        assert metadata['dictionary_id'] == 0x1c88fdb0
