#!/usr/bin/env bash
set -euo pipefail

bash tools/build_cphun139_exp.sh
python3 tools/cphun140_footnote_popup_geometry_patch.py

python3 - <<'PY'
from pathlib import Path
import re

bid = Path("src/CPHUNBuildId.h")
s = bid.read_text(encoding="utf-8")
s, n = re.subn(r'#define CPHUN_BUILD_ID "[^"]+"',
               '#define CPHUN_BUILD_ID "CPHUN-260918-140-EXP"', s, count=1)
if n != 1:
    raise SystemExit("CPHUN-140: build id replacement failed")
bid.write_text(s, encoding="utf-8")

popup = Path("src/activities/reader/FootnotePopupActivity.cpp").read_text(encoding="utf-8")
for token in [
    "constexpr int POPUP_HEIGHT = 580;",
    "std::max(0, (screenH - popupH) / 2 - 30)",
    '"Lábjegyzet {" + label_ + "}"',
]:
    if token not in popup:
        raise SystemExit("CPHUN-140 semantic check missing: " + token)

reader = Path("src/activities/reader/EpubReaderActivity.cpp").read_text(encoding="utf-8")
if "openSearchFootnoteOrWordSelect(mode);" not in reader:
    raise SystemExit("CPHUN-140 lost CPHUN-139 Search flow")

menu = Path("src/activities/reader/EpubReaderMenuActivity.cpp").read_text(encoding="utf-8")
mode = menu.find('MenuAction::WORD_SELECTION_MODE')
auto = menu.find('MenuAction::AUTO_PAGE_TURN')
if not (0 <= mode < auto):
    raise SystemExit("CPHUN-140 lost CPHUN-139 menu order")

print("CPHUN-140 semantic verification passed")
PY

git diff --check
