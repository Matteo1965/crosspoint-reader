#!/usr/bin/env bash
set -euo pipefail

bash tools/build_cphun135r4k1_safe.sh
python3 tools/cphun135r4k2_virtual_estimate_patch.py

python3 - <<'PY'
from pathlib import Path
import re
bid = Path('src/CPHUNBuildId.h')
b = bid.read_text(encoding='utf-8')
b, n = re.subn(r'#define CPHUN_BUILD_ID "[^"]+"',
               '#define CPHUN_BUILD_ID "CPHUN-260918-135R4K2-SAFE"', b, count=1)
if n != 1:
    raise SystemExit('R4K2 build ID define not found')
bid.write_text(b, encoding='utf-8')
PY

git diff --check
grep -F 'CPHUN-260918-135R4K2-SAFE' src/CPHUNBuildId.h
grep -F '__cphun_pct_' src/activities/reader/EpubReaderActivity.cpp
grep -F 'estimatedTotalPages()' src/activities/reader/EpubReaderActivity.cpp
grep -F 'progressPermille' src/activities/reader/EpubReaderChapterSelectionActivity.h

python3 - <<'PY'
from pathlib import Path

reader = Path('src/activities/reader/EpubReaderActivity.cpp').read_text(encoding='utf-8')
reader_h = Path('src/activities/reader/EpubReaderActivity.h').read_text(encoding='utf-8')
chapter_h = Path('src/activities/reader/EpubReaderChapterSelectionActivity.h').read_text(encoding='utf-8')
chapter_cpp = Path('src/activities/reader/EpubReaderChapterSelectionActivity.cpp').read_text(encoding='utf-8')
parser = Path('lib/Epub/Epub/parsers/ChapterHtmlSlimParser.cpp').read_text(encoding='utf-8')
parser_h = Path('lib/Epub/Epub/parsers/ChapterHtmlSlimParser.h').read_text(encoding='utf-8')

if 'pendingVirtualChapterJump' not in reader_h:
    raise SystemExit('R4K2: virtual jump state missing')
if 'estimatedTotalPages()' not in reader:
    raise SystemExit('R4K2: estimated total page generation missing')
if '__cphun_pct_' not in reader or '__cphun_pct_' not in chapter_cpp:
    raise SystemExit('R4K2: relative virtual target wiring missing')
if 'progressPermille' not in chapter_h:
    raise SystemExit('R4K2: virtual progress payload missing')
if 'PARAGRAPH_SEARCH_PAGES = 12' not in reader:
    raise SystemExit('R4K2: paragraph snap missing')
if '__cphun_pb_' in parser or 'pendingExplicitBreakAlias' in parser_h:
    raise SystemExit('R4K2: unsafe parser page-break experiment returned')
if 'page-break-before' in parser or 'break-before' in parser:
    raise SystemExit('R4K2: parser-side page-break detection returned')

fn_start = reader.find('void EpubReaderActivity::ensureBookFootnotes()')
fn_end = reader.find('std::string EpubReaderActivity::extractFootnoteText', fn_start)
if 'for (int spine = 0;' in reader[fn_start:fn_end]:
    raise SystemExit('R4K2: unsafe whole-book footnote scan returned')

print('R4K2 semantic verification passed')
PY
