#!/usr/bin/env bash
set -euo pipefail

bash tools/build_cphun135r4j.sh
python3 tools/cphun135r4k_toc_pagebreak_patch.py

python3 - <<'PY'
from pathlib import Path
import re
bid = Path('src/CPHUNBuildId.h')
b = bid.read_text(encoding='utf-8')
b, n = re.subn(r'#define CPHUN_BUILD_ID "[^"]+"',
               '#define CPHUN_BUILD_ID "CPHUN-260918-135R4K-EXP"', b, count=1)
if n != 1:
    raise SystemExit('R4K build ID define not found')
bid.write_text(b, encoding='utf-8')
PY

git diff --check
grep -F 'CPHUN-260918-135R4K-EXP' src/CPHUNBuildId.h
grep -F 'supplementTocWithMissingSpineFiles' lib/Epub/Epub/BookMetadataCache.cpp
grep -F '__cphun_pb_' lib/Epub/Epub/parsers/ChapterHtmlSlimParser.cpp
grep -F '128u * 1024u' src/activities/reader/EpubReaderActivity.cpp
grep -F 'MAX_GAP_PAGES = 24' src/activities/reader/EpubReaderActivity.cpp

python3 - <<'PY'
from pathlib import Path
import re

bmc = Path('lib/Epub/Epub/BookMetadataCache.cpp').read_text(encoding='utf-8')
bmc_h = Path('lib/Epub/Epub/BookMetadataCache.h').read_text(encoding='utf-8')
epub = Path('lib/Epub/Epub.cpp').read_text(encoding='utf-8')
parser = Path('lib/Epub/Epub/parsers/ChapterHtmlSlimParser.cpp').read_text(encoding='utf-8')
parser_h = Path('lib/Epub/Epub/parsers/ChapterHtmlSlimParser.h').read_text(encoding='utf-8')
reader = Path('src/activities/reader/EpubReaderActivity.cpp').read_text(encoding='utf-8')

if 'BOOK_CACHE_VERSION = 12' not in bmc:
    raise SystemExit('R4K: book cache version was not bumped')
if 'supplementTocWithMissingSpineFiles' not in bmc_h or 'supplementTocWithMissingSpineFiles' not in epub:
    raise SystemExit('R4K: partial TOC supplement wiring missing')
for excluded in ['footnote', 'endnote', 'notes.html']:
    if excluded not in bmc:
        raise SystemExit('R4K: notes exclusion missing: ' + excluded)
if 'pendingExplicitBreakAlias' not in parser_h or '__cphun_pb_' not in parser:
    raise SystemExit('R4K: explicit page-break anchor recording missing')
if 'page-break-before' not in parser or 'break-before' not in parser:
    raise SystemExit('R4K: explicit page-break detection missing')
if 'spineBytes >= (128u * 1024u)' not in reader:
    raise SystemExit('R4K: oversized physical-spine threshold missing')
if 'MAX_GAP_PAGES = 24' not in reader or 'TARGET_PAGES = 12' not in reader:
    raise SystemExit('R4K: layered virtual split policy missing')
if 'section->findAnchor("__cphun_pb_"' not in reader:
    raise SystemExit('R4K: page-break priority not connected to virtual chapter generation')

# Safety invariant from R4J/R4I: no whole-book eager footnote scan.
fn_start = reader.find('void EpubReaderActivity::ensureBookFootnotes()')
fn_end = reader.find('std::string EpubReaderActivity::extractFootnoteText', fn_start)
fn = reader[fn_start:fn_end]
if 'for (int spine = 0;' in fn:
    raise SystemExit('R4K: unsafe whole-book footnote scan returned')

print('R4K semantic verification passed')
PY
