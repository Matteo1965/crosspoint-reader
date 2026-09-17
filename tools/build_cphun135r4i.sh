#!/usr/bin/env bash
set -euo pipefail

bash tools/build_cphun135r4h.sh
python3 tools/cphun135r4i_current_spine_footnotes_patch.py

python3 - <<'PY'
from pathlib import Path
import re
bid = Path('src/CPHUNBuildId.h')
b = bid.read_text(encoding='utf-8')
b, n = re.subn(r'#define CPHUN_BUILD_ID "[^"]+"', '#define CPHUN_BUILD_ID "CPHUN-260917-135R4I-EXP"', b, count=1)
if n != 1:
    raise SystemExit('R4I build ID define not found')
bid.write_text(b, encoding='utf-8')
PY

git diff --check
grep -F 'CPHUN-260917-135R4I-EXP' src/CPHUNBuildId.h
grep -F 'Current-spine footnote index' src/activities/reader/EpubReaderActivity.cpp
grep -F 'bookFootnotesIndexed = false;' src/activities/reader/EpubReaderActivity.cpp
grep -F 'openFootnotesList(true, true);' src/activities/reader/EpubReaderActivity.cpp
grep -F 'readItemContentsToStream(item.href' src/activities/reader/EpubReaderActivity.cpp

python3 - <<'PY'
from pathlib import Path
s = Path('src/activities/reader/EpubReaderActivity.cpp').read_text(encoding='utf-8')
menu_start = s.find('case EpubReaderMenuActivity::MenuAction::FOOTNOTES:')
if menu_start < 0:
    raise SystemExit('R4I FOOTNOTES menu action missing')
menu = s[menu_start:menu_start + 900]
if 'bookFootnotesIndexed = false;' not in menu or 'ensureBookFootnotes();' not in menu:
    raise SystemExit('R4I current-spine rebuild not wired')
if 'openFootnotesList(true, true);' not in menu or 'openFootnotesList(false, true);' not in menu:
    raise SystemExit('R4I list/fallback routing missing')

fn_start = s.find('void EpubReaderActivity::ensureBookFootnotes()')
fn_end = s.find('std::string EpubReaderActivity::extractFootnoteText', fn_start)
if fn_start < 0 or fn_end < 0:
    raise SystemExit('R4I ensureBookFootnotes function missing')
fn = s[fn_start:fn_end]
if 'for (int spine = 0;' in fn:
    raise SystemExit('R4I unsafe whole-book spine loop still present')
if 'const auto item = epub->getSpineItem(currentSpineIndex);' not in fn:
    raise SystemExit('R4I current-spine source missing')
if 'MAX_SPINE_FOOTNOTES = 160' not in fn:
    raise SystemExit('R4I bounded note cap missing')
print('R4I current-spine footnote semantic verification passed')
PY
