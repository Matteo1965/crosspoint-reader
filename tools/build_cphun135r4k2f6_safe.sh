#!/usr/bin/env bash
set -euo pipefail

bash tools/build_cphun135r4k2f5_safe.sh
python3 tools/cphun135r4k2f6_footnote_popup_ux_patch.py

python3 - <<'PY'
from pathlib import Path
import re
bid = Path('src/CPHUNBuildId.h')
b = bid.read_text(encoding='utf-8')
b, n = re.subn(r'#define CPHUN_BUILD_ID "[^"]+"',
               '#define CPHUN_BUILD_ID "CPHUN-260918-135R4K2F6-SAFE"', b, count=1)
if n != 1:
    raise SystemExit('R4K2F6 build ID define not found')
bid.write_text(b, encoding='utf-8')
PY

git diff --check
grep -F 'CPHUN-260918-135R4K2F6-SAFE' src/CPHUNBuildId.h
grep -F 'canReturnToList_' src/activities/reader/FootnotePopupActivity.cpp
grep -F 'notes.size() == 1' src/activities/reader/EpubReaderActivity.cpp

python3 - <<'PY'
from pathlib import Path
reader = Path('src/activities/reader/EpubReaderActivity.cpp').read_text(encoding='utf-8')
popup = Path('src/activities/reader/FootnotePopupActivity.cpp').read_text(encoding='utf-8')

if 'ensureBookFootnotes();' in reader[reader.find('void EpubReaderActivity::openReaderMenu'):reader.find('void EpubReaderActivity::openReaderMenu')+2500]:
    raise SystemExit('R4K2F6: openReaderMenu footnote scan returned')
if 'bookFootnotesIndexed = false;' in reader:
    raise SystemExit('R4K2F6: interactive current-spine rescan returned')
if 'notes.size() == 1' not in reader:
    raise SystemExit('R4K2F6: direct one-note path missing')
if 'popupResult.isCancelled' not in reader:
    raise SystemExit('R4K2F6: popup Back/Close branching missing')
if 'canReturnToList_ ? "Vissza" : ""' not in popup:
    raise SystemExit('R4K2F6: direct-popup Back hint suppression missing')

print('R4K2F6 semantic verification passed')
PY
