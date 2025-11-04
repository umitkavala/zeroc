/**
 * Zeroc protocol constants.
 */

/** Magic bytes for Zeroc frames */
export const MAGIC_BYTES = new Uint8Array([0x50, 0x5a]); // 'PZ'

/** Protocol version (v1.0 = 0x10) */
export const PROTOCOL_VERSION = 0x10;

/** Major version number */
export const MAJOR_VERSION = 1;

/** Minor version number */
export const MINOR_VERSION = 0;

/** Flag: Compression enabled */
export const FLAG_COMPRESSION_ENABLED = 0x01;

/** Flag: Dictionary used */
export const FLAG_DICTIONARY_USED = 0x02;

/** Flag: Checksum included */
export const FLAG_CHECKSUM_INCLUDED = 0x04;

/** Dictionary magic bytes */
export const DICT_MAGIC = new TextEncoder().encode('PZSTDICT');

/** Dictionary header size in bytes */
export const DICT_HEADER_SIZE = 132;

/** Frame header size in bytes (before varint) */
export const FRAME_HEADER_SIZE = 12;
