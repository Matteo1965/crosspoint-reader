#!/usr/bin/env bash
set -euo pipefail

# R4F owns Reader-menu visibility/indexing. The R4E resolver patch still contains
# a stale exact-string visibility guard, so neutralize only that guard in the CI
# working tree before applying the otherwise unchanged R4E resolver.
python3 - <<'PY'
from pathlib import Path
import re
p = Path('tools/cphun135r4e_footnote_resolver_patch.py')
s = p.read_text(encoding='utf-8')
pat = re.compile(
    r'# Restore the Reader-menu item without reintroducing the synchronous whole-book\n'
    r'# scan\. The action itself remains current-page/bounded in the R4D guard\.\n'
    r'old_visible = .*?\n'
    r'new_visible = .*?\n'
    r'if old_visible in s:\n'
    r'    s = s\.replace\(old_visible, new_visible, 1\)\n'
    r'elif new_visible not in s:\n'
    r'    raise SystemExit\("CPHUN-135r4e: Footnotes menu visibility expression not found"\)\n',
    re.S,
)
replacement = '''# R4F: Reader-menu visibility is handled by the build prepatch and the R4F menu index patch.\n'''
s2, n = pat.subn(replacement, s, count=1)
if n != 1:
    raise SystemExit(f'R4F runner: stale R4E visibility guard not found: {n}')
p.write_text(s2, encoding='utf-8')
PY

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
grep -F 'openFootnotesList(true, true);' src/activities/reader/EpubReaderActivity.cpp
grep -F 'path.find("notes.")' src/activities/reader/EpubReaderActivity.cpp
grep -F 'readItemContentsToStream(targetHref' src/activities/reader/EpubReaderActivity.cpp
python3 - <<'PY'
from pathlib import Path
s = Path('src/activities/reader/EpubReaderActivity.cpp').read_text(encoding='utf-8')
menu_start = s.find('case EpubReaderMenuActivity::MenuAction::FOOTNOTES:')
if menu_start < 0:
    raise SystemExit('R4F FOOTNOTES menu action missing')
menu = s[menu_start:menu_start + 500]
if 'ensureBookFootnotes();' not in menu or 'openFootnotesList(true, true);' not in menu:
    raise SystemExit('R4F Reader-menu whole-book filtered list not wired')
if 'isForwardNoteref' not in s:
    raise SystemExit('R4F forward-noteref filter missing')
print('R4F semantic verification passed')
PY
