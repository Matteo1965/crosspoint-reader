#!/usr/bin/env bash
set -euo pipefail

# IMPORTANT: build from R4K2F, not the broken R4K2F2 unique-temp experiment.
bash tools/build_cphun135r4k2f_safe.sh
python3 tools/cphun135r4k2f3_footnote_io_diag_patch.py

python3 - <<'PY'
from pathlib import Path
import re
bid = Path('src/CPHUNBuildId.h')
b = bid.read_text(encoding='utf-8')
b, n = re.subn(r'#define CPHUN_BUILD_ID "[^"]+"',
               '#define CPHUN_BUILD_ID "CPHUN-260918-135R4K2F3-DIAG"', b, count=1)
if n != 1:
    raise SystemExit('R4K2F3 build ID define not found')
bid.write_text(b, encoding='utf-8')
PY

git diff --check
grep -F 'CPHUN-260918-135R4K2F3-DIAG' src/CPHUNBuildId.h
grep -F 'EPUB_ITEM_SIZE_FAILED' src/activities/reader/EpubReaderActivity.cpp
grep -F 'TEMP_FILE_OPEN_FAILED' src/activities/reader/EpubReaderActivity.cpp
grep -F 'EPUB_ZIP_STREAM_FAILED' src/activities/reader/EpubReaderActivity.cpp
grep -F 'TEMP_FILE_READ_FAILED' src/activities/reader/EpubReaderActivity.cpp

python3 - <<'PY'
from pathlib import Path
reader = Path('src/activities/reader/EpubReaderActivity.cpp').read_text(encoding='utf-8')
parser = Path('lib/Epub/Epub/parsers/ChapterHtmlSlimParser.cpp').read_text(encoding='utf-8')
parser_h = Path('lib/Epub/Epub/parsers/ChapterHtmlSlimParser.h').read_text(encoding='utf-8')

required = [
    'Target size lookup:',
    'Target inflated size:',
    'EPUB_ITEM_SIZE_FAILED',
    'TEMP_FILE_OPEN_FAILED',
    'EPUB_ZIP_STREAM_FAILED',
    'TEMP_FILE_READ_FAILED',
]
for needle in required:
    if needle not in reader:
        raise SystemExit(f'R4K2F3: missing diagnostic marker: {needle}')

if '.footnote_resolver_' in reader:
    raise SystemExit('R4K2F3: broken unique-temp R4K2F2 code unexpectedly present')
if 'openFootnotesList(wholeBook, returnToMenu, sourceSpine)' not in reader:
    raise SystemExit('R4K2F3: stable source-spine fix missing')
if '__cphun_pb_' in parser or 'pendingExplicitBreakAlias' in parser_h:
    raise SystemExit('R4K2F3: unsafe parser page-break experiment returned')

print('R4K2F3 semantic verification passed')
PY
