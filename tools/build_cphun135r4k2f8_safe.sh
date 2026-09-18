#!/usr/bin/env bash
set -euo pipefail

bash tools/build_cphun135r4k2f7_safe.sh
python3 tools/cphun135r4k2f8_tsv_export_patch.py

python3 - <<'PY'
from pathlib import Path
import re
bid = Path('src/CPHUNBuildId.h')
b = bid.read_text(encoding='utf-8')
b, n = re.subn(r'#define CPHUN_BUILD_ID "[^"]+"',
               '#define CPHUN_BUILD_ID "CPHUN-260918-135R4K2F8-SAFE"', b, count=1)
if n != 1:
    raise SystemExit('R4K2F8 build ID define not found')
bid.write_text(b, encoding='utf-8')
PY

git diff --check
grep -F 'CPHUN-260918-135R4K2F8-SAFE' src/CPHUNBuildId.h
grep -F 'Szerkesztések exportálása' src/activities/reader/EpubReaderMenuActivity.cpp
grep -F 'version\tid\ttype\tbook_path' src/activities/reader/EpubReaderActivity.cpp
grep -F 'constexpr const char* EXPORT_DIR = "/edits";' src/activities/reader/EpubReaderActivity.cpp

python3 - <<'PY'
from pathlib import Path
menu = Path('src/activities/reader/EpubReaderMenuActivity.cpp').read_text(encoding='utf-8')
reader = Path('src/activities/reader/EpubReaderActivity.cpp').read_text(encoding='utf-8')
bookmarks = Path('src/activities/reader/EpubReaderBookmarksActivity.cpp').read_text(encoding='utf-8')
bookmarks_h = Path('src/activities/reader/EpubReaderBookmarksActivity.h').read_text(encoding='utf-8')

if 'MenuAction::EXPORT_EDITS' not in menu or 'Szerkesztések exportálása' not in menu:
    raise SystemExit('R4K2F8: Book-tab export menu item missing')
cover = menu.find('MenuAction::BOOK_COVER')
export = menu.find('MenuAction::EXPORT_EDITS')
if cover < 0 or export < cover:
    raise SystemExit('R4K2F8: export menu item is not after cover')
if 'bool EpubReaderActivity::exportEditsTsv()' not in reader:
    raise SystemExit('R4K2F8: TSV exporter missing')
for required in ['"MARK"', '"EDIT"', 'book_path', 'book_file', 'visible_offset',
                 'context_before', 'context_after', 'EXPORT_DIR = "/edits"']:
    if required not in reader:
        raise SystemExit('R4K2F8: TSV field missing: ' + required)
if 'Megjelölt szavak mentése' in bookmarks or 'exportMarkedWords' in bookmarks or 'RowKind::Export' in bookmarks:
    raise SystemExit('R4K2F8: legacy TXT export still present')
if 'Export' in bookmarks_h.split('enum class RowKind', 1)[1].split(';', 1)[0]:
    raise SystemExit('R4K2F8: legacy Export row kind still present')
if 'bookFootnotesIndexed = false;' in reader:
    raise SystemExit('R4K2F8: unsafe current-spine footnote rescan returned')
if 'footnoteResolverCachedTarget == targetHref' not in reader:
    raise SystemExit('R4K2F8: validated R4K2F7 resolver cache missing')

print('R4K2F8 semantic verification passed')
PY
