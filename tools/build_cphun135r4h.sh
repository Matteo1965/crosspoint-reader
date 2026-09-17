#!/usr/bin/env bash
set -euo pipefail

bash tools/build_cphun135r4g.sh
python3 tools/cphun135r4h_crashfix_patch.py

python3 - <<'PY'
from pathlib import Path
import re
bid = Path('src/CPHUNBuildId.h')
b = bid.read_text(encoding='utf-8')
b, n = re.subn(r'#define CPHUN_BUILD_ID "[^"]+"', '#define CPHUN_BUILD_ID "CPHUN-260917-135R4H-EXP"', b, count=1)
if n != 1:
    raise SystemExit('R4H build ID define not found')
bid.write_text(b, encoding='utf-8')
PY

git diff --check
grep -F 'CPHUN-260917-135R4H-EXP' src/CPHUNBuildId.h
grep -F '#define CPHUN_BUILD_DATE "Sep-17 2026"' src/CPHUNBuildId.h
grep -F 'openFootnotesList(false, true);' src/activities/reader/EpubReaderActivity.cpp
grep -F 'readItemContentsToStream(targetHref' src/activities/reader/EpubReaderActivity.cpp

python3 - <<'PY'
from pathlib import Path
s = Path('src/activities/reader/EpubReaderActivity.cpp').read_text(encoding='utf-8')
menu_start = s.find('case EpubReaderMenuActivity::MenuAction::FOOTNOTES:')
if menu_start < 0:
    raise SystemExit('R4H FOOTNOTES menu action missing')
menu = s[menu_start:menu_start + 700]
if 'ensureBookFootnotes();' in menu:
    raise SystemExit('R4H unsafe synchronous whole-book scan is still reachable from FOOTNOTES menu')
if 'openFootnotesList(false, true);' not in menu:
    raise SystemExit('R4H safe current-page footnote list not wired')

# Keep the heavy scanner code available for future incremental/background work,
# but it must not be called synchronously from the Reader menu in this build.
if 'void EpubReaderActivity::ensureBookFootnotes()' not in s:
    raise SystemExit('R4H expected scanner implementation missing')

print('R4H crash-fix semantic verification passed')
PY
