package zeroc

// Protocol constants
const (
	// MagicBytes are the magic bytes for Zeroc frames
	MagicBytes = "PZ"

	// ProtocolVersion is the current protocol version (v1.0 = 0x10)
	ProtocolVersion byte = 0x10

	// MajorVersion is the major version number
	MajorVersion = 1

	// MinorVersion is the minor version number
	MinorVersion = 0
)

// Flags
const (
	// FlagCompressionEnabled indicates compression is used
	FlagCompressionEnabled byte = 0x01

	// FlagDictionaryUsed indicates dictionary compression
	FlagDictionaryUsed byte = 0x02

	// FlagChecksumIncluded indicates CRC32C checksum is present
	FlagChecksumIncluded byte = 0x04
)

// Dictionary constants
const (
	// DictMagic is the magic bytes for Zeroc dictionary files
	DictMagic = "PZSTDICT"

	// DictHeaderSize is the size of the dictionary header in bytes
	DictHeaderSize = 132

	// FrameHeaderSize is the size of the frame header (before varint)
	FrameHeaderSize = 12
)
