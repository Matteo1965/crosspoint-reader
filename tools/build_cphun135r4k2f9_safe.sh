#!/usr/bin/env bash
set -euo pipefail

# Includes corrected R4K2F8 TSV base with legacy export prompt removed.

bash tools/build_cphun135r4k2f8_safe.sh
python3 tools/cphun135r4k2f9_dark_mode_menu_patch.py

python3 - <<'PY'
from pathlib import Path
import re
bid = Path('src/CPHUNBuildId.h')
b = bid.read_text(encoding='utf-8')
b, n = re.subn(r'#define CPHUN_BUILD_ID "[^"]+"',
               '#define CPHUN_BUILD_ID "CPHUN-260918-135R4K2F9-SAFE"', b, count=1)
if n != 1:
    raise SystemExit('R4K2F9 build ID define not found')
bid.write_text(b, encoding='utf-8')
PY

git diff --check
grep -F 'CPHUN-260918-135R4K2F9-SAFE' src/CPHUNBuildId.h
grep -F 'Sötét mód' src/activities/reader/EpubReaderMenuActivity.cpp

python3 - <<'PY'
from pathlib import Path
menu = Path('src/activities/reader/EpubReaderMenuActivity.cpp').read_text(encoding='utf-8')
a = menu.find('std::vector<EpubReaderMenuActivity::MenuItem> EpubReaderMenuActivity::buildReadingItems')
b = menu.find('std::vector<EpubReaderMenuActivity::MenuItem> EpubReaderMenuActivity::buildMoreItems')
c = menu.find('const std::vector<EpubReaderMenuActivity::MenuItem>&', b)
reading = menu[a:b]
book = menu[b:c]
if 'MenuAction::NIGHT_MODE' in reading:
    raise SystemExit('R4K2F9: NIGHT_MODE still on Olvasás tab')
if 'MenuAction::NIGHT_MODE' not in book or '"Sötét mód"' not in book:
    raise SystemExit('R4K2F9: Sötét mód missing from Könyv tab')
rot = book.find('MenuAction::ROTATE_SCREEN')
dark = book.find('MenuAction::NIGHT_MODE')
text_settings = book.find('MenuAction::TEXT_SETTINGS')
if not (0 <= rot < dark < text_settings):
    raise SystemExit('R4K2F9: requested Könyv ordering is wrong')
if 'Szerkesztések exportálása' not in book:
    raise SystemExit('R4K2F9: R4K2F8 TSV export menu item missing')
print('R4K2F9 semantic verification passed')
PY
