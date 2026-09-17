#!/usr/bin/env bash
set -euo pipefail

bash tools/build_cphun135r4j.sh
python3 tools/cphun135r4k1_safe_patch.py

python3 - <<'PY'
from pathlib import Path
import re
bid = Path('src/CPHUNBuildId.h')
b = bid.read_text(encoding='utf-8')
b, n = re.subn(r'#define CPHUN_BUILD_ID "[^"]+"',
               '#define CPHUN_BUILD_ID "CPHUN-260918-135R4K1-SAFE"', b, count=1)
if n != 1:
    raise SystemExit('R4K1 build ID define not found')
bid.write_text(b, encoding='utf-8')
PY

git diff --check
grep -F 'CPHUN-260918-135R4K1-SAFE' src/CPHUNBuildId.h
grep -F 'supplementTocWithMissingSpineFiles' lib/Epub/Epub/BookMetadataCache.cpp
grep -F '128u * 1024u' src/activities/reader/EpubReaderActivity.cpp

python3 - <<'PY'
from pathlib import Path
bmc = Path('lib/Epub/Epub/BookMetadataCache.cpp').read_text(encoding='utf-8')
epub = Path('lib/Epub/Epub.cpp').read_text(encoding='utf-8')
reader = Path('src/activities/reader/EpubReaderActivity.cpp').read_text(encoding='utf-8')
parser = Path('lib/Epub/Epub/parsers/ChapterHtmlSlimParser.cpp').read_text(encoding='utf-8')
parser_h = Path('lib/Epub/Epub/parsers/ChapterHtmlSlimParser.h').read_text(encoding='utf-8')

if 'BOOK_CACHE_VERSION = 12' not in bmc:
    raise SystemExit('R4K1: book cache version not bumped')
if 'supplementTocWithMissingSpineFiles' not in epub:
    raise SystemExit('R4K1: TOC supplement not wired')
if 'spineBytes >= (128u * 1024u)' not in reader:
    raise SystemExit('R4K1: oversized-spine guard missing')
if '__cphun_pb_' in parser or 'pendingExplicitBreakAlias' in parser_h:
    raise SystemExit('R4K1: parser-side page-break experiment leaked into SAFE build')
if 'page-break-before' in parser or 'break-before' in parser:
    raise SystemExit('R4K1: explicit page-break parser logic leaked into SAFE build')

fn_start = reader.find('void EpubReaderActivity::ensureBookFootnotes()')
fn_end = reader.find('std::string EpubReaderActivity::extractFootnoteText', fn_start)
fn = reader[fn_start:fn_end]
if 'for (int spine = 0;' in fn:
    raise SystemExit('R4K1: unsafe whole-book footnote scan returned')

print('R4K1 SAFE semantic verification passed')
PY
