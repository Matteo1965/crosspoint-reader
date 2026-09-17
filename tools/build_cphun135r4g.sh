#!/usr/bin/env bash
set -euo pipefail

bash tools/build_cphun135r4f.sh
python3 tools/cphun135r4g_keyboard_corrections_patch.py

python3 - <<'PY'
from pathlib import Path
import re
bid = Path('src/CPHUNBuildId.h')
b = bid.read_text(encoding='utf-8')
b, n = re.subn(r'#define CPHUN_BUILD_ID "[^"]+"', '#define CPHUN_BUILD_ID "CPHUN-260917-135R4G-EXP"', b, count=1)
if n != 1:
    raise SystemExit('R4G build ID define not found')
bid.write_text(b, encoding='utf-8')
PY

git diff --check
grep -F 'CPHUN-260917-135R4G-EXP' src/CPHUNBuildId.h
grep -F 'Filtered book footnote index' src/activities/reader/EpubReaderActivity.cpp
grep -F 'openFootnotesList(true, true);' src/activities/reader/EpubReaderActivity.cpp
grep -F 'readItemContentsToStream(targetHref' src/activities/reader/EpubReaderActivity.cpp
grep -F 'HUK("+", "+", '\''+'\'')' src/activities/util/HungarianKeyboardLayout.h
grep -F 'HUK("*", "*", '\''*'\'')' src/activities/util/HungarianKeyboardLayout.h
grep -F 'HUK("<", "<", '\''<'\'')' src/activities/util/HungarianKeyboardLayout.h
grep -F 'HUK(">", ">", '\''>'\'')' src/activities/util/HungarianKeyboardLayout.h

python3 - <<'PY'
from pathlib import Path
import re
s = Path('src/activities/reader/EpubReaderActivity.cpp').read_text(encoding='utf-8')
menu_start = s.find('case EpubReaderMenuActivity::MenuAction::FOOTNOTES:')
if menu_start < 0:
    raise SystemExit('R4G FOOTNOTES menu action missing')
menu = s[menu_start:menu_start + 500]
if 'ensureBookFootnotes();' not in menu or 'openFootnotesList(true, true);' not in menu:
    raise SystemExit('R4G filtered whole-book footnote menu not wired')

k = Path('src/activities/util/HungarianKeyboardLayout.h').read_text(encoding='utf-8')
m = re.search(r'inline const fui::KeyboardKey SYMBOL_ROW3\[\]\s*=\s*\{(.*?)\};', k, re.S)
if not m:
    raise SystemExit('R4G SYMBOL_ROW3 missing')
body = m.group(1)
count = body.count('HUK(') + body.count('HUKW(') + body.count('HUKS(')
if count != 10:
    raise SystemExit(f'R4G SYMBOL_ROW3 key count is {count}, expected 10')
if 'QWERTY_KEY_BACKSPACE, 3)' not in body:
    raise SystemExit('R4G right-edge Backspace missing')
if 'HUKW("…", "…", 1404, 3)' not in body:
    raise SystemExit('R4G wide ellipsis missing')
print('R4G combined semantic verification passed')
PY
