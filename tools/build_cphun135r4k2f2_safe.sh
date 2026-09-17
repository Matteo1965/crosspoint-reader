#!/usr/bin/env bash
set -euo pipefail

bash tools/build_cphun135r4k2f_safe.sh
python3 tools/cphun135r4k2f2_unique_resolver_tmp_patch.py

python3 - <<'PY'
from pathlib import Path
import re
bid = Path('src/CPHUNBuildId.h')
b = bid.read_text(encoding='utf-8')
b, n = re.subn(r'#define CPHUN_BUILD_ID "[^"]+"',
               '#define CPHUN_BUILD_ID "CPHUN-260918-135R4K2F2-SAFE"', b, count=1)
if n != 1:
    raise SystemExit('R4K2F2 build ID define not found')
bid.write_text(b, encoding='utf-8')
PY

git diff --check
grep -F 'CPHUN-260918-135R4K2F2-SAFE' src/CPHUNBuildId.h
grep -F '.footnote_resolver_' src/activities/reader/EpubReaderActivity.cpp
grep -F 'footnoteResolverSequence' src/activities/reader/EpubReaderActivity.cpp

python3 - <<'PY'
from pathlib import Path
reader = Path('src/activities/reader/EpubReaderActivity.cpp').read_text(encoding='utf-8')
parser = Path('lib/Epub/Epub/parsers/ChapterHtmlSlimParser.cpp').read_text(encoding='utf-8')
parser_h = Path('lib/Epub/Epub/parsers/ChapterHtmlSlimParser.h').read_text(encoding='utf-8')

if '.footnote_resolver.tmp' in reader:
    raise SystemExit('R4K2F2: shared resolver temp path still present')
if 'footnoteResolverSequence' not in reader:
    raise SystemExit('R4K2F2: unique resolver sequence missing')
if 'openFootnotesList(wholeBook, returnToMenu, sourceSpine)' not in reader:
    raise SystemExit('R4K2F2: prior stable source-spine fix missing')
if '__cphun_pb_' in parser or 'pendingExplicitBreakAlias' in parser_h:
    raise SystemExit('R4K2F2: unsafe page-break parser code returned')
print('R4K2F2 semantic verification passed')
PY
