#!/usr/bin/env bash
set -euo pipefail

bash tools/build_cphun142_exp.sh
python3 tools/cphun143_footnote_button_mapping_patch.py

python3 - <<'PY'
from pathlib import Path
import re

bid = Path("src/CPHUNBuildId.h")
s = bid.read_text(encoding="utf-8")
s, n = re.subn(r'#define CPHUN_BUILD_ID "[^"]+"',
               '#define CPHUN_BUILD_ID "CPHUN-260919-143-EXP"', s, count=1)
if n != 1:
    raise SystemExit("CPHUN-143: build id replacement failed")
bid.write_text(s, encoding="utf-8")

popup = Path("src/activities/reader/FootnotePopupActivity.cpp").read_text(encoding="utf-8")

required = [
    "MappedInputManager::Button::Up",
    "MappedInputManager::Button::Down",
    "MappedInputManager::Button::Left",
    "MappedInputManager::Button::Right",
    "mappedInput.isNavDirectionSwapped() ? 1 : -1",
    "mappedInput.isNavDirectionSwapped() ? -1 : 1",
]
for token in required:
    if token not in popup:
        raise SystemExit("CPHUN-143 missing token: " + token)

up_block = popup[popup.find("MappedInputManager::Button::Up"):
                 popup.find("MappedInputManager::Button::Down")]
if "FootnotePopupNavResult" in up_block:
    raise SystemExit("CPHUN-143: side Up still navigates footnotes")

down_pos = popup.find("MappedInputManager::Button::Down")
left_pos = popup.find("MappedInputManager::Button::Left", down_pos)
down_block = popup[down_pos:left_pos]
if "FootnotePopupNavResult" in down_block:
    raise SystemExit("CPHUN-143: side Down still navigates footnotes")

if "constexpr int POPUP_HEIGHT = 600;" not in popup:
    raise SystemExit("CPHUN-143 lost popup height")
if "std::max(0, (screenH - popupH) / 2 - 40)" not in popup:
    raise SystemExit("CPHUN-143 lost popup offset")

print("CPHUN-143 semantic verification passed")
PY

git diff --check
