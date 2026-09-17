#!/usr/bin/env bash
set -euo pipefail

bash tools/build_cphun135r4k2_safe.sh
python3 tools/cphun135r4k2f_footnote_session_patch.py

python3 - <<'PY'
from pathlib import Path
import re
bid = Path('src/CPHUNBuildId.h')
b = bid.read_text(encoding='utf-8')
b, n = re.subn(r'#define CPHUN_BUILD_ID "[^"]+"',
               '#define CPHUN_BUILD_ID "CPHUN-260918-135R4K2F-SAFE"', b, count=1)
if n != 1:
    raise SystemExit('R4K2F build ID define not found')
bid.write_text(b, encoding='utf-8')
PY

git diff --check
grep -F 'CPHUN-260918-135R4K2F-SAFE' src/CPHUNBuildId.h
grep -F 'sourceSpineIndex = -1' src/activities/reader/EpubReaderActivity.h
grep -F 'openFootnotesList(wholeBook, returnToMenu, sourceSpine)' src/activities/reader/EpubReaderActivity.cpp

python3 - <<'PY'
from pathlib import Path
reader = Path('src/activities/reader/EpubReaderActivity.cpp').read_text(encoding='utf-8')
parser = Path('lib/Epub/Epub/parsers/ChapterHtmlSlimParser.cpp').read_text(encoding='utf-8')
parser_h = Path('lib/Epub/Epub/parsers/ChapterHtmlSlimParser.h').read_text(encoding='utf-8')

if 'sourceSpineIndex >= 0 ? sourceSpineIndex : currentSpineIndex' not in reader:
    raise SystemExit('R4K2F: stable source-spine capture missing')
if 'openFootnotesList(wholeBook, returnToMenu, sourceSpine)' not in reader:
    raise SystemExit('R4K2F: popup return does not preserve source spine')
if '__cphun_pb_' in parser or 'pendingExplicitBreakAlias' in parser_h:
    raise SystemExit('R4K2F: unsafe parser page-break experiment returned')

print('R4K2F semantic verification passed')
PY
