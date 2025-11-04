"""
Tests for Zeroc wire format encoding/decoding.
"""
import pytest
import zstandard as zstd
from zeroc import (
    encode_frame,
    decode_frame,
    decompress_payload,
    MAGIC_BYTES,
    PROTOCOL_VERSION,
    FLAG_COMPRESSION_ENABLED,
    FLAG_DICTIONARY_USED,
    FLAG_CHECKSUM_INCLUDED,
)


class TestVarintEncoding:
    """Test LEB128 varint encoding/decoding."""

    def test_small_values(self):
        """Test encoding/decoding small integers."""
        from zeroc.wire_format import encode_varint, decode_varint

        # Single byte values (0-127)
        for i in range(128):
            encoded = encode_varint(i)
            decoded, size = decode_varint(encoded)
            assert decoded == i
            assert size == 1
            assert len(encoded) == 1

    def test_two_byte_values(self):
        """Test two-byte varint values."""
        from zeroc.wire_format import encode_varint, decode_varint

        # 128 = 0x80 0x01
        encoded = encode_varint(128)
        assert encoded == b'\x80\x01'
        decoded, size = decode_varint(encoded)
        assert decoded == 128
        assert size == 2

        # 300 = 0xAC 0x02
        encoded = encode_varint(300)
        decoded, size = decode_varint(encoded)
        assert decoded == 300
        assert size == 2

    def test_large_values(self):
        """Test large varint values."""
        from zeroc.wire_format import encode_varint, decode_varint

        # 1MB
        value = 1024 * 1024
        encoded = encode_varint(value)
        decoded, size = decode_varint(encoded)
        assert decoded == value

        # 10MB
        value = 10 * 1024 * 1024
        encoded = encode_varint(value)
        decoded, size = decode_varint(encoded)
        assert decoded == value


class TestFrameEncoding:
    """Test Zeroc frame encoding."""

    def test_identity_frame(self):
        """Test uncompressed identity frame."""
        proto_bytes = b"Hello, Zeroc!"

        frame = encode_frame(proto_bytes, compress=False, checksum=False)

        # Check header
        assert frame[0:2] == MAGIC_BYTES
        assert frame[2] == PROTOCOL_VERSION
        assert frame[3] == 0  # No flags
        assert frame[4:8] == b'\x00\x00\x00\x00'  # Dict ID = 0
        assert frame[8:12] == b'\x00\x00\x00\x00'  # Schema hash = 0

        # Decode and verify
        decoded, metadata = decode_frame(frame)
        assert decoded == proto_bytes
        assert metadata['compression_enabled'] is False
        assert metadata['dictionary_used'] is False
        assert metadata['checksum_included'] is False

    def test_compressed_frame_no_dict(self):
        """Test compressed frame without dictionary."""
        proto_bytes = b"Hello, Zeroc!" * 100

        frame = encode_frame(proto_bytes, compress=True, checksum=False)

        # Check flags
        assert frame[3] & FLAG_COMPRESSION_ENABLED
        assert not (frame[3] & FLAG_DICTIONARY_USED)

        # Decode
        compressed, metadata = decode_frame(frame)
        assert metadata['compression_enabled'] is True

        # Decompress
        decompressed = decompress_payload(compressed, 0)
        assert decompressed == proto_bytes

    def test_compressed_frame_with_checksum(self):
        """Test compressed frame with CRC32C checksum."""
        proto_bytes = b"Hello, Zeroc!" * 100

        frame = encode_frame(proto_bytes, compress=True, checksum=True)

        # Check flags
        assert frame[3] & FLAG_COMPRESSION_ENABLED
        assert frame[3] & FLAG_CHECKSUM_INCLUDED

        # Decode (should validate checksum)
        compressed, metadata = decode_frame(frame)
        assert metadata['checksum_included'] is True

        decompressed = decompress_payload(compressed, 0)
        assert decompressed == proto_bytes

    def test_dictionary_compression(self):
        """Test compression with dictionary."""
        # Create sample data
        samples = [b"order_id: 12345, user_id: 678" for _ in range(100)]
        proto_bytes = samples[0]

        # Train dictionary
        dict_data = zstd.train_dictionary(100 * 1024, samples)
        compressor = zstd.ZstdCompressor(dict_data=dict_data, level=3)
        decompressor = zstd.ZstdDecompressor(dict_data=dict_data)

        # Encode with dictionary
        dict_id = 0x12345678
        schema_hash = 0xABCDEF00
        frame = encode_frame(
            proto_bytes,
            dictionary_id=dict_id,
            schema_hash=schema_hash,
            compress=True,
            checksum=True,
            compressor=compressor
        )

        # Check flags and IDs
        assert frame[3] & FLAG_COMPRESSION_ENABLED
        assert frame[3] & FLAG_DICTIONARY_USED
        assert frame[3] & FLAG_CHECKSUM_INCLUDED

        # Decode
        compressed, metadata = decode_frame(frame)
        assert metadata['dictionary_id'] == dict_id
        assert metadata['schema_hash'] == schema_hash
        assert metadata['dictionary_used'] is True

        # Decompress with dictionary
        decompressed = decompress_payload(compressed, dict_id, decompressor)
        assert decompressed == proto_bytes


class TestFrameDecoding:
    """Test Zeroc frame decoding error handling."""

    def test_truncated_frame(self):
        """Test decoding truncated frame."""
        with pytest.raises(ValueError, match="Frame too short"):
            decode_frame(b"PZ")

    def test_invalid_magic(self):
        """Test decoding frame with invalid magic."""
        frame = b"XX" + b"\x10\x00" + b"\x00" * 8
        with pytest.raises(ValueError, match="Invalid magic bytes"):
            decode_frame(frame)

    def test_unsupported_version(self):
        """Test decoding frame with unsupported version."""
        frame = MAGIC_BYTES + b"\x20" + b"\x00" + b"\x00" * 8
        with pytest.raises(ValueError, match="Unsupported protocol version"):
            decode_frame(frame)

    def test_truncated_payload(self):
        """Test decoding frame with truncated payload."""
        # Create frame claiming 1000 bytes payload but only has 10
        header = MAGIC_BYTES + bytes([PROTOCOL_VERSION, 0]) + b"\x00" * 8
        frame = header + b"\xe8\x07" + b"short"  # varint 1000 + 5 bytes

        with pytest.raises(ValueError, match="Truncated frame"):
            decode_frame(frame)

    def test_checksum_mismatch(self):
        """Test decoding frame with invalid checksum."""
        proto_bytes = b"Hello"

        # Create valid frame
        frame = encode_frame(proto_bytes, compress=False, checksum=True)

        # Corrupt the checksum (last 4 bytes)
        corrupted = frame[:-4] + b"\xFF\xFF\xFF\xFF"

        with pytest.raises(ValueError, match="Checksum mismatch"):
            decode_frame(corrupted)

    def test_missing_decompressor(self):
        """Test decompression without required decompressor."""
        compressed = b"fake_compressed_data"

        with pytest.raises(ValueError, match="Decompressor required"):
            decompress_payload(compressed, dictionary_id=0x12345678)


class TestRoundTrip:
    """Test complete encode → decode round trips."""

    def test_small_payload(self):
        """Test round trip with small payload."""
        proto_bytes = b"Small payload"

        frame = encode_frame(proto_bytes, compress=True, checksum=True)
        compressed, _ = decode_frame(frame)
        decompressed = decompress_payload(compressed, 0)

        assert decompressed == proto_bytes

    def test_large_payload(self):
        """Test round trip with large payload."""
        proto_bytes = b"Large payload content. " * 10000

        frame = encode_frame(proto_bytes, compress=True, checksum=True)
        compressed, metadata = decode_frame(frame)
        decompressed = decompress_payload(compressed, 0)

        assert decompressed == proto_bytes
        assert len(frame) < len(proto_bytes)  # Verify compression occurred

    def test_empty_payload(self):
        """Test round trip with empty payload."""
        proto_bytes = b""

        frame = encode_frame(proto_bytes, compress=False, checksum=False)
        decoded, _ = decode_frame(frame)

        assert decoded == proto_bytes
