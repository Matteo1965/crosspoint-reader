#!/usr/bin/env bash
set -euo pipefail

bash tools/build_cphun146_exp.sh
python3 tools/cphun147_ota_test_patch.py

python3 - <<'PY'
from pathlib import Path
import re

bid = Path("src/CPHUNBuildId.h")
s = bid.read_text(encoding="utf-8")
s, n = re.subn(r'#define CPHUN_BUILD_ID "[^"]+"',
               '#define CPHUN_BUILD_ID "CPHUN-260921-147-OTA-TEST"', s, count=1)
if n != 1:
    raise SystemExit("CPHUN-147 build id replacement failed")
if re.search(r'^#define CPHUN_BUILD_DATE ', s, re.M):
    s = re.sub(r'^#define CPHUN_BUILD_DATE .*$', '#define CPHUN_BUILD_DATE "Sep-21 2026"', s, count=1, flags=re.M)
else:
    if not s.endswith("\n"):
        s += "\n"
    s += '#define CPHUN_BUILD_DATE "Sep-21 2026"\n'
bid.write_text(s, encoding="utf-8")

ota = Path("src/network/OtaUpdater.cpp").read_text(encoding="utf-8")
parser_h = Path("lib/JsonParser/ReleaseJsonParser.h").read_text(encoding="utf-8")
parser_cpp = Path("lib/JsonParser/ReleaseJsonParser.cpp").read_text(encoding="utf-8")

required_ota = [
    "https://api.github.com/repos/Matteo1965/crosspoint-reader/releases/latest",
    "constexpr int CPHUN_OTA_TEST_BASELINE_BUILD = 135;",
    "Hungarian Edition v.",
    "latestBuild > currentBuild",
]
for token in required_ota:
    if token not in ota:
        raise SystemExit("CPHUN-147 OTA missing: " + token)

for token in [
    "getHungarianEditionBuild() const",
    "hungarianEditionBuild",
]:
    if token not in parser_h or token not in parser_cpp:
        raise SystemExit("CPHUN-147 parser missing: " + token)

if 'cphun-build-' not in parser_cpp:
    raise SystemExit("CPHUN-147 release marker parsing missing")

if '#define CPHUN_BUILD_ID "CPHUN-260921-147-OTA-TEST"' not in bid.read_text(encoding="utf-8"):
    raise SystemExit("CPHUN-147 build id verification failed")

print("CPHUN-147 OTA test semantic verification passed")
PY

git diff --check
