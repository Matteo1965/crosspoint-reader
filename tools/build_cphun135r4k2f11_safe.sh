#!/usr/bin/env bash
set -euo pipefail

bash tools/build_cphun135r4k2f9_safe.sh
python3 tools/cphun135r4k2f10_tsv_utf8_bom_patch.py
python3 tools/cphun135r4k2f11_export_menu_order_patch.py

python3 - <<'PY'
from pathlib import Path
import re
bid = Path('src/CPHUNBuildId.h')
s = bid.read_text(encoding='utf-8')
s, n = re.subn(r'#define CPHUN_BUILD_ID "[^"]+"',
               '#define CPHUN_BUILD_ID "CPHUN-260918-135R4K2F11-SAFE"', s, count=1)
if n != 1:
    raise SystemExit('R4K2F11 build ID define not found')
bid.write_text(s, encoding='utf-8')
PY

git diff --check

python3 - <<'PY'
from pathlib import Path
menu = Path('src/activities/reader/EpubReaderMenuActivity.cpp').read_text(encoding='utf-8')
reader = Path('src/activities/reader/EpubReaderActivity.cpp').read_text(encoding='utf-8')

book_start = menu.find('std::vector<EpubReaderMenuActivity::MenuItem> EpubReaderMenuActivity::buildMoreItems')
book_end = menu.find('const std::vector<EpubReaderMenuActivity::MenuItem>&', book_start)
book = menu[book_start:book_end]
q = book.find('MenuAction::DISPLAY_QR')
e = book.find('MenuAction::EXPORT_EDITS')
s = book.find('MenuAction::SYNC')
if not (0 <= q < e < s):
    raise SystemExit('R4K2F11: QR -> export -> sync order incorrect')
if 'const uint8_t utf8Bom[] = {0xEF, 0xBB, 0xBF};' not in reader:
    raise SystemExit('R4K2F11: UTF-8 BOM patch missing')
if '"Sötét mód"' not in book:
    raise SystemExit('R4K2F11: Sötét mód missing')
print('R4K2F11 semantic verification passed')
PY
