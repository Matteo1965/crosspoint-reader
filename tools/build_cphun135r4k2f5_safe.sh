#!/usr/bin/env bash
set -euo pipefail

# Crash-safe baseline: keep R4K2F3 resolver diagnostics, do NOT apply the
# R4K2F4 one-shot target allocation experiment.
bash tools/build_cphun135r4k2f3_diag.sh
python3 tools/cphun_logfiles_dir_patch.py
python3 tools/cphun135r4k2f5_current_page_safe_patch.py

python3 - <<'PY'
from pathlib import Path
import re
bid = Path('src/CPHUNBuildId.h')
b = bid.read_text(encoding='utf-8')
b, n = re.subn(r'#define CPHUN_BUILD_ID "[^"]+"',
               '#define CPHUN_BUILD_ID "CPHUN-260918-135R4K2F5-SAFE"', b, count=1)
if n != 1:
    raise SystemExit('R4K2F5 build ID define not found')
bid.write_text(b, encoding='utf-8')
PY

git diff --check
grep -F 'CPHUN-260918-135R4K2F5-SAFE' src/CPHUNBuildId.h
grep -F 'CURRENT_PAGE_FOOTNOTE_INDEX_EMPTY' src/activities/reader/EpubReaderActivity.cpp
grep -F 'footnote_index_error_' src/activities/reader/EpubReaderActivity.cpp
grep -F 'constexpr const char* LOG_DIR = "/logfiles";' src/activities/reader/EpubReaderActivity.cpp

python3 - <<'PY'
from pathlib import Path
reader = Path('src/activities/reader/EpubReaderActivity.cpp').read_text(encoding='utf-8')
parser = Path('lib/Epub/Epub/parsers/ChapterHtmlSlimParser.cpp').read_text(encoding='utf-8')
parser_h = Path('lib/Epub/Epub/parsers/ChapterHtmlSlimParser.h').read_text(encoding='utf-8')

menu_start = reader.find('void EpubReaderActivity::openReaderMenu')
menu_end = reader.find('\n}', menu_start)
if menu_start < 0:
    raise SystemExit('R4K2F5: openReaderMenu missing')
menu_snippet = reader[menu_start:menu_start + 2500]
if 'ensureBookFootnotes();' in menu_snippet:
    raise SystemExit('R4K2F5: openReaderMenu still scans footnotes')
if 'bookFootnotesIndexed = false;' in reader:
    raise SystemExit('R4K2F5: interactive current-spine rescan still present')
if 'openFootnotesList(true, true)' in reader:
    raise SystemExit('R4K2F5: book/current-spine footnote list still used by menu')
if 'CURRENT_PAGE_FOOTNOTE_INDEX_EMPTY' not in reader:
    raise SystemExit('R4K2F5: index-miss diagnostic missing')
if 'constexpr const char* LOG_DIR = "/logfiles";' not in reader:
    raise SystemExit('R4K2F5: /logfiles support missing')
if 'readItemContentsToBytes(targetHref' in reader:
    raise SystemExit('R4K2F5: R4K2F4 one-shot target allocation unexpectedly present')
if '__cphun_pb_' in parser or 'pendingExplicitBreakAlias' in parser_h:
    raise SystemExit('R4K2F5: unsafe page-break parser experiment returned')

print('R4K2F5 semantic verification passed')
PY
