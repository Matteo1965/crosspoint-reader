#!/usr/bin/env bash
set -euo pipefail

bash tools/build_cphun135r4k2f6_safe.sh
python3 tools/cphun135r4k2f7_reuse_target_patch.py

python3 - <<'PY'
from pathlib import Path
import re
bid = Path('src/CPHUNBuildId.h')
b = bid.read_text(encoding='utf-8')
b, n = re.subn(r'#define CPHUN_BUILD_ID "[^"]+"',
               '#define CPHUN_BUILD_ID "CPHUN-260918-135R4K2F7-SAFE"', b, count=1)
if n != 1:
    raise SystemExit('R4K2F7 build ID define not found')
bid.write_text(b, encoding='utf-8')
PY

git diff --check
grep -F 'CPHUN-260918-135R4K2F7-SAFE' src/CPHUNBuildId.h
grep -F 'footnoteResolverCachedTarget' src/activities/reader/EpubReaderActivity.cpp
grep -F 'reuse it instead of streaming' src/activities/reader/EpubReaderActivity.cpp

python3 - <<'PY'
from pathlib import Path
reader = Path('src/activities/reader/EpubReaderActivity.cpp').read_text(encoding='utf-8')
header = Path('src/activities/reader/EpubReaderActivity.h').read_text(encoding='utf-8')

if 'mutable std::string footnoteResolverCachedTarget;' not in header:
    raise SystemExit('R4K2F7: cached target member missing')
if 'if (footnoteResolverCachedTarget == targetHref)' not in reader:
    raise SystemExit('R4K2F7: cached target reuse path missing')
if 'notes.size() == 1' not in reader or 'popupResult.isCancelled' not in reader:
    raise SystemExit('R4K2F7: R4K2F6 popup UX missing')
if 'bookFootnotesIndexed = false;' in reader:
    raise SystemExit('R4K2F7: unsafe interactive current-spine rescan returned')

print('R4K2F7 semantic verification passed')
PY
