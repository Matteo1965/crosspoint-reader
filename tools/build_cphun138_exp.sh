#!/usr/bin/env bash
set -euo pipefail

bash tools/build_cphun137_exp.sh
python3 tools/cphun138_layout_list_height_patch.py

python3 - <<'PY'
from pathlib import Path
import re

bid = Path("src/CPHUNBuildId.h")
s = bid.read_text(encoding="utf-8")
s, n = re.subn(r'#define CPHUN_BUILD_ID "[^"]+"',
               '#define CPHUN_BUILD_ID "CPHUN-260918-138-EXP"', s, count=1)
if n != 1:
    raise SystemExit("CPHUN-138: build id replacement failed")
bid.write_text(s, encoding="utf-8")

ui = Path("src/activities/settings/TextSettingsActivity.cpp").read_text(encoding="utf-8")
required = [
    "tab_ == Tab::Layout ? metrics_.buttonHintsHeight : bottomReserved + captionHeight",
    "Layout list",
]
for token in required:
    if token not in ui:
        raise SystemExit("CPHUN-138 semantic check missing: " + token)

if "Optimalizációs küszöb" not in ui:
    raise SystemExit("CPHUN-138 lost CPHUN-137 threshold UI")
print("CPHUN-138 semantic verification passed")
PY

git diff --check
