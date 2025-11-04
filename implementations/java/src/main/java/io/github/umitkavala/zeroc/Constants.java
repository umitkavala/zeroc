package io.github.umitkavala.zeroc;

/**
 * Zeroc protocol constants.
 */
public final class Constants {

    /** Magic bytes for Zeroc frames */
    public static final byte[] MAGIC_BYTES = new byte[]{'P', 'Z'};

    /** Protocol version (v1.0 = 0x10) */
    public static final byte PROTOCOL_VERSION = 0x10;

    /** Major version number */
    public static final int MAJOR_VERSION = 1;

    /** Minor version number */
    public static final int MINOR_VERSION = 0;

    /** Flag: Compression enabled */
    public static final byte FLAG_COMPRESSION_ENABLED = 0x01;

    /** Flag: Dictionary used */
    public static final byte FLAG_DICTIONARY_USED = 0x02;

    /** Flag: Checksum included */
    public static final byte FLAG_CHECKSUM_INCLUDED = 0x04;

    /** Dictionary magic bytes */
    public static final byte[] DICT_MAGIC = "PZSTDICT".getBytes();

    /** Dictionary header size */
    public static final int DICT_HEADER_SIZE = 132;

    /** Frame header size (before varint) */
    public static final int FRAME_HEADER_SIZE = 12;

    private Constants() {
        // Prevent instantiation
    }
}
