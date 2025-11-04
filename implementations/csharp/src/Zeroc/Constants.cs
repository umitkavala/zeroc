namespace Umitkavala.Zeroc;

/// <summary>
/// Zeroc protocol constants.
/// </summary>
public static class Constants
{
    /// <summary>
    /// Magic bytes for Zeroc frames: "PZ"
    /// </summary>
    public static readonly byte[] MagicBytes = { 0x50, 0x5A }; // 'P', 'Z'

    /// <summary>
    /// Protocol version (v1.0 = 0x10)
    /// </summary>
    public const byte ProtocolVersion = 0x10;

    /// <summary>
    /// Major version number
    /// </summary>
    public const int MajorVersion = 1;

    /// <summary>
    /// Minor version number
    /// </summary>
    public const int MinorVersion = 0;

    /// <summary>
    /// Flag: Compression enabled
    /// </summary>
    public const byte FlagCompressionEnabled = 0x01;

    /// <summary>
    /// Flag: Dictionary used
    /// </summary>
    public const byte FlagDictionaryUsed = 0x02;

    /// <summary>
    /// Flag: Checksum included
    /// </summary>
    public const byte FlagChecksumIncluded = 0x04;

    /// <summary>
    /// Dictionary magic bytes: "PZSTDICT"
    /// </summary>
    public static readonly byte[] DictMagic = "PZSTDICT"u8.ToArray();

    /// <summary>
    /// Dictionary header size in bytes
    /// </summary>
    public const int DictHeaderSize = 132;

    /// <summary>
    /// Frame header size in bytes (before varint)
    /// </summary>
    public const int FrameHeaderSize = 12;
}
