from pathlib import Path

base = Path('src/components/themes/BaseTheme.cpp')
s = base.read_text(encoding='utf-8')
old = 'drawBookmarkStatusIcon(renderer, renderer.getScreenWidth() - bookmarkStatusIconWidth, 0);'
new = 'drawBookmarkStatusIcon(renderer, 446, 4);'
assert s.count(old) == 1, s.count(old)
base.write_text(s.replace(old, new, 1), encoding='utf-8')

bid = Path('src/CPHUNBuildId.h')
i = bid.read_text(encoding='utf-8')
assert 'CPHUN-260912-105' in i
i = i.replace('CPHUN-260912-105', 'CPHUN-260912-106')
bid.write_text(i, encoding='utf-8')
