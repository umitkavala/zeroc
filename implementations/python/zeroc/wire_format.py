"""
Zeroc wire format encoder/decoder.

Implements the binary wire format as specified in spec/WIRE_FORMAT.md
"""
import struct
import zstandard as zstd
from typing import Dict, Tuple, Optional
import crc32c


# Constants
MAGIC_BYTES = b'PZ'
PROTOCOL_VERSION = 0x10  # v1.0

# Flags
FLAG_COMPRESSION_ENABLED = 0x01
FLAG_DICTIONARY_USED = 0x02
FLAG_CHECKSUM_INCLUDED = 0x04


def encode_varint(value: int) -> bytes:
    """Encode integer as LEB128 varint."""
    result = bytearray()
    while value > 0x7F:
        result.append((value & 0x7F) | 0x80)
        value >>= 7
    result.append(value & 0x7F)
    return bytes(result)


def decode_varint(data: bytes) -> Tuple[int, int]:
    """
    Decode LEB128 varint.

    Returns:
        (value, bytes_consumed)
    """
    result = 0
    shift = 0
    pos = 0
    while True:
        if pos >= len(data):
            raise ValueError("Truncated varint")
        byte = data[pos]
        result |= (byte & 0x7F) << shift
        pos += 1
        if not (byte & 0x80):
            break
        shift += 7
    return result, pos


def encode_frame(
    proto_bytes: bytes,
    dictionary_id: int = 0,
    schema_hash: int = 0,
    compress: bool = True,
    checksum: bool = False,
    compressor: Optional[zstd.ZstdCompressor] = None
) -> bytes:
    """
    Encode protobuf as Zeroc frame.

    Args:
        proto_bytes: Protobuf binary data
        dictionary_id: Dictionary ID (CRC32), 0 for no dictionary
        schema_hash: Schema hash (CRC32)
        compress: Whether to compress (True) or send as identity (False)
        checksum: Whether to include CRC32C checksum
        compressor: ZstdCompressor instance (required if compress=True and dictionary_id > 0)

    Returns:
        Complete Zeroc frame

    Raises:
        ValueError: If parameters are invalid
    """
    # 1. Compress payload (if enabled)
    flags = 0
    if compress:
        if compressor:
            compressed = compressor.compress(proto_bytes)
            flags |= FLAG_COMPRESSION_ENABLED
            if dictionary_id > 0:
                flags |= FLAG_DICTIONARY_USED
        elif dictionary_id == 0:
            # Compress without dictionary
            compressed = zstd.compress(proto_bytes)
            flags |= FLAG_COMPRESSION_ENABLED
        else:
            raise ValueError("compressor required when dictionary_id > 0")
    else:
        compressed = proto_bytes

    # 2. Add checksum (if enabled)
    checksum_bytes = b''
    if checksum:
        flags |= FLAG_CHECKSUM_INCLUDED
        checksum_value = crc32c.crc32c(compressed)
        checksum_bytes = struct.pack('>I', checksum_value)

    # 3. Build header (12 bytes)
    header = struct.pack(
        '>2sBBII',  # Magic(2), Version(1), Flags(1), DictID(4), SchemaHash(4)
        MAGIC_BYTES,
        PROTOCOL_VERSION,
        flags,
        dictionary_id,
        schema_hash
    )

    # 4. Build frame
    payload_length = encode_varint(len(compressed))
    return header + payload_length + compressed + checksum_bytes


def decode_frame(frame: bytes) -> Tuple[bytes, Dict[str, any]]:
    """
    Decode Zeroc frame to protobuf bytes and metadata.

    Args:
        frame: Complete Zeroc frame

    Returns:
        (protobuf_bytes, metadata_dict)

    Raises:
        ValueError: If frame is invalid or malformed
    """
    # 1. Check minimum size
    if len(frame) < 12:
        raise ValueError(f"Frame too short: {len(frame)} bytes < 12 bytes minimum")

    # 2. Parse header (12 bytes)
    magic, version, flags, dict_id, schema_hash = struct.unpack(
        '>2sBBII', frame[0:12]
    )

    # 3. Validate magic
    if magic != MAGIC_BYTES:
        raise ValueError(f"Invalid magic bytes: {magic!r}, expected {MAGIC_BYTES!r}")

    # 4. Check version
    major = version >> 4
    minor = version & 0x0F
    if major != 1:
        raise ValueError(f"Unsupported protocol version: {major}.{minor}")

    # 5. Parse payload length
    try:
        payload_length, varint_size = decode_varint(frame[12:])
    except ValueError as e:
        raise ValueError(f"Failed to decode payload length: {e}")

    # 6. Extract compressed data
    payload_start = 12 + varint_size
    payload_end = payload_start + payload_length

    if payload_end > len(frame):
        raise ValueError(
            f"Truncated frame: payload ends at {payload_end} but frame is {len(frame)} bytes"
        )

    compressed = frame[payload_start:payload_end]

    # 7. Verify checksum (if present)
    if flags & FLAG_CHECKSUM_INCLUDED:
        checksum_start = payload_end
        checksum_end = checksum_start + 4

        if checksum_end > len(frame):
            raise ValueError("Truncated checksum")

        expected_checksum = struct.unpack('>I', frame[checksum_start:checksum_end])[0]
        actual_checksum = crc32c.crc32c(compressed)

        if expected_checksum != actual_checksum:
            raise ValueError(
                f"Checksum mismatch: expected 0x{expected_checksum:08x}, "
                f"got 0x{actual_checksum:08x}"
            )

    # 8. Decompress (if compressed)
    if flags & FLAG_COMPRESSION_ENABLED:
        # Decompressor will be provided externally based on dict_id
        # For now, just return the compressed data and let caller decompress
        proto_bytes = compressed  # Caller must decompress with proper dictionary
    else:
        proto_bytes = compressed

    # 9. Return protobuf bytes and metadata
    metadata = {
        'version': version,
        'major_version': major,
        'minor_version': minor,
        'flags': flags,
        'dictionary_id': dict_id,
        'schema_hash': schema_hash,
        'compressed_size': len(compressed),
        'compression_enabled': bool(flags & FLAG_COMPRESSION_ENABLED),
        'dictionary_used': bool(flags & FLAG_DICTIONARY_USED),
        'checksum_included': bool(flags & FLAG_CHECKSUM_INCLUDED),
    }

    return proto_bytes, metadata


def decompress_payload(
    compressed: bytes,
    dictionary_id: int,
    decompressor: Optional[zstd.ZstdDecompressor] = None
) -> bytes:
    """
    Decompress payload with optional dictionary.

    Args:
        compressed: Compressed bytes
        dictionary_id: Dictionary ID (0 for no dictionary)
        decompressor: ZstdDecompressor instance (required if dictionary_id > 0)

    Returns:
        Decompressed protobuf bytes

    Raises:
        ValueError: If decompressor required but not provided
    """
    if dictionary_id > 0:
        if not decompressor:
            raise ValueError(f"Decompressor required for dictionary_id 0x{dictionary_id:08x}")
        return decompressor.decompress(compressed)
    else:
        return zstd.decompress(compressed)
