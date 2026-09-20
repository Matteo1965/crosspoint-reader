#!/usr/bin/env bash
set -euo pipefail

bash tools/build_cphun145_exp.sh
python3 tools/cphun146_version_page_patch.py

python3 - <<'PY'
from pathlib import Path
import re

bid = Path("src/CPHUNBuildId.h")
s = bid.read_text(encoding="utf-8")
s, n = re.subn(r'#define CPHUN_BUILD_ID "[^"]+"',
               '#define CPHUN_BUILD_ID "CPHUN-260920-146-EXP"', s, count=1)
if n != 1:
    raise SystemExit("CPHUN-146 build id replacement failed")

if re.search(r'^#define CPHUN_BUILD_DATE ', s, re.M):
    s = re.sub(r'^#define CPHUN_BUILD_DATE .*$', '#define CPHUN_BUILD_DATE "Sep-20 2026"', s, count=1, flags=re.M)
else:
    if not s.endswith("\n"):
        s += "\n"
    s += '#define CPHUN_BUILD_DATE "Sep-20 2026"\n'
bid.write_text(s, encoding="utf-8")

version = Path("src/activities/settings/CrossPointVersionActivity.cpp").read_text(encoding="utf-8")

required = [
    "std::string hungarianEditionLabel()",
    'return "Hungarian Edition v." + buildId.substr',
    "const std::string editionLabel = hungarianEditionLabel();",
    '"- Üzemmód választó gomb"',
    '"- Lábjegyzetek közvetlen megnyitása"',
    '"- Alsó gombok 1×/2×/Hosszú nyomás"',
    '"- Jobb StarDict szótárkezelés"',
    '"Betűköz-optimalizálás"',
    '"Font- és betűpár-alapú korrekció, állítható optimalizációs küszöbbel."',
]
for token in required:
    if token not in version:
        raise SystemExit("CPHUN-146 version page missing: " + token)

for forbidden in [
    '"- Mód választó: Szótár / Megjelölés / Szerkesztés"',
    '"- Több lábjegyzet kezelése és közvetlen megnyitása"',
    '"- Alsó gombok: 1× / 2× / Hosszú nyomás"',
    '"- Továbbfejlesztett StarDict szótárkezelés"',
]:
    if forbidden in version:
        raise SystemExit("CPHUN-146 old page 5 text still present: " + forbidden)

if '#define CPHUN_BUILD_ID "CPHUN-260920-146-EXP"' not in bid.read_text(encoding="utf-8"):
    raise SystemExit("CPHUN-146 build id verification failed")

print("CPHUN-146 semantic verification passed")
PY

git diff --check
