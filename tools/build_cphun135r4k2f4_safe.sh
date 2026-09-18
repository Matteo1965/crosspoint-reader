#!/usr/bin/env bash
set -euo pipefail

# Build from the R4K2F3 diagnostic baseline, then replace streaming resolver
# with bounded one-shot inflate for footnote targets.
bash tools/build_cphun135r4k2f3_diag.sh
python3 tools/cphun135r4k2f4_oneshot_footnote_patch.py

python3 - <<'PY'
from pathlib import Path
import re
bid = Path('src/CPHUNBuildId.h')
b = bid.read_text(encoding='utf-8')
b, n = re.subn(r'#define CPHUN_BUILD_ID "[^"]+"',
               '#define CPHUN_BUILD_ID "CPHUN-260918-135R4K2F4-SAFE"', b, count=1)
if n != 1:
    raise SystemExit('R4K2F4 build ID define not found')
bid.write_text(b, encoding='utf-8')
PY

git diff --check
grep -F 'CPHUN-260918-135R4K2F4-SAFE' src/CPHUNBuildId.h
grep -F 'MAX_FOOTNOTE_TARGET_BYTES' src/activities/reader/EpubReaderActivity.cpp
grep -F 'EPUB_ZIP_ONESHOT_FAILED' src/activities/reader/EpubReaderActivity.cpp
grep -F 'readItemContentsToBytes(targetHref' src/activities/reader/EpubReaderActivity.cpp

python3 - <<'PY'
from pathlib import Path
reader = Path('src/activities/reader/EpubReaderActivity.cpp').read_text(encoding='utf-8')
parser = Path('lib/Epub/Epub/parsers/ChapterHtmlSlimParser.cpp').read_text(encoding='utf-8')
parser_h = Path('lib/Epub/Epub/parsers/ChapterHtmlSlimParser.h').read_text(encoding='utf-8')

if 'readItemContentsToStream(targetHref' in reader:
    raise SystemExit('R4K2F4: streaming footnote resolver still present')
if 'readItemContentsToBytes(targetHref' not in reader:
    raise SystemExit('R4K2F4: one-shot footnote resolver missing')
if 'MAX_FOOTNOTE_TARGET_BYTES = 96u * 1024u' not in reader:
    raise SystemExit('R4K2F4: footnote target size guard missing')
if 'openFootnotesList(wholeBook, returnToMenu, sourceSpine)' not in reader:
    raise SystemExit('R4K2F4: stable source-spine fix missing')
if '__cphun_pb_' in parser or 'pendingExplicitBreakAlias' in parser_h:
    raise SystemExit('R4K2F4: unsafe page-break parser code returned')

print('R4K2F4 semantic verification passed')
PY
