from pathlib import Path
import re
import struct

bmp_path = Path("src/components/icons/NEW_DOGEAR_32x32.bmp")
data = bmp_path.read_bytes()

if data[:2] != b"BM":
    raise SystemExit("CPHUN-126: NEW_DOGEAR_32x32 is not a BMP file")

pixel_offset = struct.unpack_from("<I", data, 10)[0]
dib_size = struct.unpack_from("<I", data, 14)[0]
width = struct.unpack_from("<i", data, 18)[0]
height = struct.unpack_from("<i", data, 22)[0]
planes, bits_per_pixel = struct.unpack_from("<HH", data, 26)
compression = struct.unpack_from("<I", data, 30)[0]

if dib_size < 40 or width != 32 or abs(height) != 32:
    raise SystemExit(
        f"CPHUN-126: icon must be exactly 32x32 (got {width}x{height})"
    )
if planes != 1 or bits_per_pixel != 1 or compression != 0:
    raise SystemExit(
        "CPHUN-126: icon must be an uncompressed 1-bit BMP"
    )

# The renderer treats a set bit as white and a clear bit as black. Require the
# BMP palette to use the same polarity so the source pixels can be copied
# losslessly, without inversion, dithering, or resampling.
palette_offset = 14 + dib_size
palette = data[palette_offset:palette_offset + 8]
if palette != bytes((255, 255, 255, 0, 0, 0, 0, 0)):
    raise SystemExit(
        "CPHUN-126: expected palette index 0=white and index 1=black"
    )

row_stride = ((width * bits_per_pixel + 31) // 32) * 4
rows = []
for y in range(32):
    source_y = 31 - y if height > 0 else y
    start = pixel_offset + source_y * row_stride
    row = data[start:start + 4]
    if len(row) != 4:
        raise SystemExit("CPHUN-126: truncated BMP pixel data")
    rows.append(row)

icon_bytes = b"".join(rows)
if len(icon_bytes) != 128:
    raise SystemExit("CPHUN-126: native icon must contain exactly 128 bytes")

formatted_rows = [
    "    " + ", ".join(f"0x{value:02X}" for value in row)
    for row in rows
]
new_icon = (
    "// size: 32x32 — CPHUN-126 NEW_DOGEAR_32x32 bookmark marker\n"
    "static const uint8_t NEW_DOGEAR_32x32[] = {\n"
    + ",\n".join(formatted_rows)
    + "\n};"
)

icon_path = Path("src/components/icons/bookmark.h")
icon_text = icon_path.read_text(encoding="utf-8")
pattern = re.compile(
    r"// size: 32x32[^\n]*\n"
    r"static const uint8_t BookmarkStatusIcon\[\] = \{.*?\n\};",
    re.S,
)
icon_text, count = pattern.subn(new_icon, icon_text)
if count != 1:
    raise SystemExit(f"CPHUN-126: BookmarkStatusIcon block matches={count}")
icon_path.write_text(icon_text, encoding="utf-8")

theme_path = Path("src/components/themes/BaseTheme.cpp")
theme = theme_path.read_text(encoding="utf-8")
old_pixel_source = (
    "      const uint8_t byte = "
    "BookmarkStatusIcon[row * bytesPerRow + col / 8];"
)
new_pixel_source = (
    "      const uint8_t byte = "
    "NEW_DOGEAR_32x32[row * bytesPerRow + col / 8];"
)
if theme.count(old_pixel_source) != 1:
    raise SystemExit(
        f"CPHUN-126: bookmark pixel-source matches={theme.count(old_pixel_source)}"
    )
theme = theme.replace(old_pixel_source, new_pixel_source, 1)

old_position = "    drawBookmarkStatusIcon(renderer, 446, 4);"
new_position = "    drawBookmarkStatusIcon(renderer, 448, 2);"
if theme.count(old_position) != 1:
    raise SystemExit(
        f"CPHUN-126: bookmark-position anchor matches={theme.count(old_position)}"
    )
theme_path.write_text(theme.replace(old_position, new_position, 1), encoding="utf-8")

build_id_path = Path("src/CPHUNBuildId.h")
build_id = build_id_path.read_text(encoding="utf-8")
old_id = '#define CPHUN_BUILD_ID "CPHUN-260914-125"'
new_id = '#define CPHUN_BUILD_ID "CPHUN-260914-126"'
if build_id.count(old_id) != 1:
    raise SystemExit(f"CPHUN-126: build-id anchor matches={build_id.count(old_id)}")
build_id_path.write_text(build_id.replace(old_id, new_id, 1), encoding="utf-8")
