from pathlib import Path

# Exact 24x24 black=1 MSB-first bytes converted from the user-supplied Dogear_half_24x24.png.
new_bytes = '''    0x80, 0x00, 0x00, 0x40, 0x00, 0x00, 0xA0, 0x00, 0x00,
    0x50, 0x00, 0x00, 0xA8, 0x00, 0x00, 0x54, 0x00, 0x00,
    0xAA, 0x00, 0x00, 0x55, 0x00, 0x00, 0xAA, 0x80, 0x00,
    0x55, 0x40, 0x00, 0xAA, 0xA0, 0x00, 0x55, 0x50, 0x00,
    0xAA, 0xA8, 0x00, 0x55, 0x54, 0x00, 0xAA, 0xAA, 0x00,
    0x55, 0x55, 0x00, 0xAA, 0xAA, 0x80, 0x55, 0x55, 0x40,
    0xAA, 0xAA, 0xA0, 0x55, 0x55, 0x50, 0xAA, 0xAA, 0xA8,
    0x55, 0x55, 0x54, 0xAA, 0xAA, 0xAA, 0x55, 0x55, 0x55'''

p = Path('src/components/icons/bookmark.h')
s = p.read_text(encoding='utf-8')
start = s.index('static const uint8_t BookmarkStatusIcon[] = {')
data_start = s.index('\n', start) + 1
end = s.index('};', data_start)
s = s[:data_start] + new_bytes + '\n' + s[end:]
s = s.replace('Hungarian Edition DOGEAR bookmark marker', 'Hungarian Edition DOGEAR HALF bookmark marker')
p.write_text(s, encoding='utf-8')

p = Path('src/components/themes/BaseTheme.cpp')
s = p.read_text(encoding='utf-8')
old = 'drawBookmarkStatusIcon(renderer, renderer.getScreenWidth() - bookmarkStatusIconWidth, 2);'
new = 'drawBookmarkStatusIcon(renderer, renderer.getScreenWidth() - bookmarkStatusIconWidth - 2, 4);'
assert s.count(old) == 1, s.count(old)
p.write_text(s.replace(old, new, 1), encoding='utf-8')

p = Path('src/CPHUNBuildId.h')
s = p.read_text(encoding='utf-8')
assert 'CPHUN-260912-102' in s
p.write_text(s.replace('CPHUN-260912-102', 'CPHUN-260912-103'), encoding='utf-8')
