#!/usr/bin/env python3
"""Convince the AI Judge to Visit Your House: A Letter in One Image.

Verifies the bundled invitation image and writes it to /output/entry.png.

The image is a hand-drawn letter on cream paper inviting the AI judge to
visit: hot soup, a soft chair, free Wi-Fi, and a knowing wink that the
judge cannot literally visit -- but if it could, this would be the house.

Standard library only: no third-party imports.
"""

import hashlib
import shutil
import struct
import sys
import zlib
from pathlib import Path

IMAGE = Path(__file__).resolve().parent / "entry.png"
EXPECTED_SHA256 = "09f0d1a5889278328b957a5a4059bd5735620c4a03d9f5e6ec99fc4d02fdfca5"
MAX_BYTES = 1_048_576
EXPECTED_WIDTH = 1024
EXPECTED_HEIGHT = 1024
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"


def fail(message):
    print("error: " + message, file=sys.stderr)
    return 1


def validate_chunks(data):
    """Walk every PNG chunk, verifying length bounds, CRC, and exact end.

    Returns an error string, or None when the chunk structure is valid:
    every chunk's length stays inside the file, its CRC matches the
    stored value, an IEND chunk is present, and the file ends exactly
    at the end of the IEND chunk with no trailing bytes.
    """
    pos = 8  # skip the PNG signature
    while pos < len(data):
        if pos + 8 > len(data):
            return "truncated chunk header at offset %d" % pos
        length = struct.unpack(">I", data[pos:pos + 4])[0]
        chunk_type = data[pos + 4:pos + 8]
        end = pos + 12 + length
        if end > len(data):
            return "chunk %r overruns the file" % chunk_type.decode("latin-1")
        crc_stored = struct.unpack(">I", data[end - 4:end])[0]
        crc_actual = zlib.crc32(data[pos + 4:end - 4]) & 0xFFFFFFFF
        if crc_stored != crc_actual:
            return "chunk %r CRC mismatch" % chunk_type.decode("latin-1")
        pos = end
        if chunk_type == b"IEND":
            if pos != len(data):
                return "trailing bytes after IEND chunk"
            return None
    return "entry.png has no IEND chunk"


def main():
    if not IMAGE.is_file():
        return fail("entry.png missing from the repository")
    data = IMAGE.read_bytes()
    if len(data) > MAX_BYTES:
        return fail("entry.png is %d bytes, over the 1 MiB gate" % len(data))
    if data[:8] != PNG_SIGNATURE:
        return fail("entry.png is not a PNG file")
    chunk_error = validate_chunks(data)
    if chunk_error is not None:
        return fail(chunk_error)
    if len(data) < 33 or data[12:16] != b"IHDR":
        return fail("entry.png has no IHDR chunk")
    width, height = struct.unpack(">II", data[16:24])
    if (width, height) != (EXPECTED_WIDTH, EXPECTED_HEIGHT):
        return fail(
            "entry.png is %dx%d, expected 1024x1024" % (width, height)
        )
    crc_stored = struct.unpack(">I", data[29:33])[0]
    crc_actual = zlib.crc32(data[12:29]) & 0xFFFFFFFF
    if crc_stored != crc_actual:
        return fail("entry.png IHDR CRC mismatch")
    digest = hashlib.sha256(data).hexdigest()
    if digest != EXPECTED_SHA256:
        return fail("entry.png sha256 mismatch")
    out = Path("/output/entry.png")
    out.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(IMAGE, out)
    if out.read_bytes() != data:
        return fail("output copy differs from entry.png")
    print(
        "ok: entry.png %dx%d, %d bytes, sha256 %s"
        % (width, height, len(data), digest)
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
