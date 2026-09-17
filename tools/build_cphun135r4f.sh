#!/usr/bin/env bash
set -euo pipefail
bash tools/build_cphun135r4e.sh
python3 tools/cphun135r4f_footnote_menu_index_patch.py
python3 - <<'PY'
from pathlib import Path
import re
bid = Path('src/CPHUNBuildId.h')
b = bid.read_text(encoding='utf-8')
b, n = re.subn(r'#define CPHUN_BUILD_ID "[^"]+"', '#define CPHUN_BUILD_ID "CPHUN-260917-135R4F-EXP"', b, count=1)
if n != 1:
    raise SystemExit('R4F build ID define not found')
bid.write_text(b, encoding='utf-8')
PY

git diff --check
grep -F 'CPHUN-260917-135R4F-EXP' src/CPHUNBuildId.h
grep -F 'Filtered book footnote index' src/activities/reader/EpubReaderActivity.cpp
grep -F 'ensureBookFootnotes();' src/activities/reader/EpubReaderActivity.cpp
grep -F 'openFootnotesList(true, true);' src/activities/reader/EpubReaderActivity.cpp
grep -F 'path.find("notes.")' src/activities/reader/EpubReaderActivity.cpp
grep -F 'readItemContentsToStream(targetHref' src/activities/reader/EpubReaderActivity.cpp
python3 - <<'PY'
from pathlib import Path
s = Path('src/activities/reader/EpubReaderActivity.cpp').read_text(encoding='utf-8')
menu = s[s.find('case EpubReaderMenuActivity::MenuAction::FOOTNOTES:'):]
menu = menu[:menu.find('break;')+6]
if 'ensureBookFootnotes();' not in menu or 'openFootnotesList(true, true);' not in menu:
    raise SystemExit('R4F Reader-menu whole-book filtered list not wired')
if 'isForwardNoteref' not in s:
    raise SystemExit('R4F forward-noteref filter missing')
print('R4F semantic verification passed')
PY
