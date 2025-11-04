"""
Zeroc: High-Performance API Compression Protocol

Python reference implementation.
"""
from .wire_format import (
    encode_frame,
    decode_frame,
    decompress_payload,
    MAGIC_BYTES,
    PROTOCOL_VERSION,
    FLAG_COMPRESSION_ENABLED,
    FLAG_DICTIONARY_USED,
    FLAG_CHECKSUM_INCLUDED,
)
from .dictionary_loader import DictionaryLoader, load_dictionary

__version__ = "1.0.0"
__protocol_version__ = "1.0"

__all__ = [
    # Wire format
    "encode_frame",
    "decode_frame",
    "decompress_payload",

    # Constants
    "MAGIC_BYTES",
    "PROTOCOL_VERSION",
    "FLAG_COMPRESSION_ENABLED",
    "FLAG_DICTIONARY_USED",
    "FLAG_CHECKSUM_INCLUDED",

    # Dictionary
    "DictionaryLoader",
    "load_dictionary",
]
