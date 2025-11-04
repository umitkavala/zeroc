"""
Zeroc dictionary loader.

Loads and validates Zeroc dictionary files per spec/DICTIONARY_FORMAT.md
"""
import struct
import zlib
from pathlib import Path
from typing import Dict, Tuple
import zstandard as zstd


DICT_MAGIC = b'PZSTDICT'


def load_dictionary(filepath: str) -> Tuple[Dict[str, any], zstd.ZstdCompressionDict]:
    """
    Load Zeroc dictionary from file.

    Args:
        filepath: Path to .zdict file

    Returns:
        (metadata_dict, ZstdCompressionDict)

    Raises:
        ValueError: If dictionary format is invalid
        FileNotFoundError: If file doesn't exist
    """
    path = Path(filepath)
    if not path.exists():
        raise FileNotFoundError(f"Dictionary not found: {filepath}")

    with open(path, 'rb') as f:
        data = f.read()

    # 1. Check minimum size (132 byte header + dictionary data)
    if len(data) < 132:
        raise ValueError(f"Dictionary too small: {len(data)} bytes")

    # 2. Parse header (132 bytes)
    header_data = data[:132]

    magic = header_data[0:8]
    if magic != DICT_MAGIC:
        raise ValueError(f"Invalid magic: {magic!r}, expected {DICT_MAGIC!r}")

    version = header_data[8:20].rstrip(b'\0').decode('ascii')
    schema_name = header_data[20:84].rstrip(b'\0').decode('ascii')

    dict_id, sample_count, created, compression_level, dict_size, \
    min_size, max_size, sha256_prefix, reserved = struct.unpack(
        '>IIQIIIIQQ', header_data[84:132]
    )

    # 3. Extract Zstd dictionary data
    zstd_dict_data = data[132:]

    if len(zstd_dict_data) != dict_size:
        raise ValueError(
            f"Dictionary size mismatch: header says {dict_size}, got {len(zstd_dict_data)}"
        )

    # 4. Verify dictionary ID
    expected_dict_id = zlib.crc32(zstd_dict_data) & 0xFFFFFFFF
    if expected_dict_id == 0:
        expected_dict_id = 0x00000001

    if expected_dict_id != dict_id:
        raise ValueError(
            f"Dictionary ID mismatch: header says 0x{dict_id:08x}, "
            f"calculated 0x{expected_dict_id:08x}"
        )

    # 5. Create Zstd dictionary object
    zstd_dict = zstd.ZstdCompressionDict(zstd_dict_data)

    # 6. Return metadata and dictionary
    metadata = {
        'version': version,
        'schema_name': schema_name,
        'dictionary_id': dict_id,
        'sample_count': sample_count,
        'created': created,
        'compression_level': compression_level,
        'dict_size': dict_size,
        'min_size': min_size,
        'max_size': max_size,
        'sha256_prefix': sha256_prefix,
    }

    return metadata, zstd_dict


class DictionaryLoader:
    """
    Dictionary loader with caching.

    Example:
        loader = DictionaryLoader()
        meta, dict_obj = loader.load("dictionaries/formats/Order-1.0.0.zdict")
        compressor = zstd.ZstdCompressor(dict_data=dict_obj)
    """

    def __init__(self):
        self._cache: Dict[str, Tuple[Dict, zstd.ZstdCompressionDict]] = {}

    def load(self, filepath: str) -> Tuple[Dict[str, any], zstd.ZstdCompressionDict]:
        """Load dictionary with caching."""
        if filepath in self._cache:
            return self._cache[filepath]

        metadata, dict_obj = load_dictionary(filepath)
        self._cache[filepath] = (metadata, dict_obj)
        return metadata, dict_obj

    def get_compressor(self, filepath: str, level: int = 3) -> zstd.ZstdCompressor:
        """Get compressor for dictionary."""
        _, dict_obj = self.load(filepath)
        return zstd.ZstdCompressor(dict_data=dict_obj, level=level)

    def get_decompressor(self, filepath: str) -> zstd.ZstdDecompressor:
        """Get decompressor for dictionary."""
        _, dict_obj = self.load(filepath)
        return zstd.ZstdDecompressor(dict_data=dict_obj)

    def clear_cache(self):
        """Clear dictionary cache."""
        self._cache.clear()
