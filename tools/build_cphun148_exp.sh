#!/usr/bin/env bash
set -euo pipefail

bash tools/build_cphun147_ota_test.sh
python3 tools/cphun148_ota_release_patch.py

python3 - <<'PY'
from pathlib import Path
import re

bid = Path("src/CPHUNBuildId.h")
s = bid.read_text(encoding="utf-8")
s, n = re.subn(r'#define CPHUN_BUILD_ID "[^"]+"',
               '#define CPHUN_BUILD_ID "CPHUN-260921-148-EXP"', s, count=1)
if n != 1:
    raise SystemExit("CPHUN-148 build id replacement failed")
if re.search(r'^#define CPHUN_BUILD_DATE ', s, re.M):
    s = re.sub(r'^#define CPHUN_BUILD_DATE .*$', '#define CPHUN_BUILD_DATE "Sep-21 2026"', s, count=1, flags=re.M)
else:
    if not s.endswith("\n"):
        s += "\n"
    s += '#define CPHUN_BUILD_DATE "Sep-21 2026"\n'
bid.write_text(s, encoding="utf-8")

ota = Path("src/network/OtaUpdater.cpp").read_text(encoding="utf-8")
version = Path("src/activities/settings/CrossPointVersionActivity.cpp").read_text(encoding="utf-8")

required = [
    "https://api.github.com/repos/Matteo1965/crosspoint-reader/releases/latest",
    "const int currentBuild = parseCphunBuildId(CPHUN_BUILD_ID);",
    "Hungarian Edition OTA compare: current=%d latest=%d",
    "latestBuild > currentBuild",
]
for token in required:
    if token not in ota:
        raise SystemExit("CPHUN-148 OTA missing: " + token)

for forbidden in [
    "CPHUN_OTA_TEST_BASELINE_BUILD",
    "test-baseline",
    "force the comparison baseline to build 135",
]:
    if forbidden in ota:
        raise SystemExit("CPHUN-148 test-only OTA logic still present: " + forbidden)

if '#define CPHUN_BUILD_ID "CPHUN-260921-148-EXP"' not in bid.read_text(encoding="utf-8"):
    raise SystemExit("CPHUN-148 build id verification failed")

if "hungarianEditionLabel()" not in version:
    raise SystemExit("CPHUN-148 dynamic edition label missing")

print("CPHUN-148 production OTA semantic verification passed")
PY

git diff --check
