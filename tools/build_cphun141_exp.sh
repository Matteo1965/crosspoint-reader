#!/usr/bin/env bash
set -euo pipefail

bash tools/build_cphun140_exp.sh
python3 tools/cphun141_footnote_multilist_fix_patch.py

python3 - <<'PY'
from pathlib import Path
import re

bid = Path("src/CPHUNBuildId.h")
s = bid.read_text(encoding="utf-8")
s, n = re.subn(r'#define CPHUN_BUILD_ID "[^"]+"',
               '#define CPHUN_BUILD_ID "CPHUN-260919-141-EXP"', s, count=1)
if n != 1:
    raise SystemExit("CPHUN-141: build id replacement failed")
bid.write_text(s, encoding="utf-8")

popup = Path("src/activities/reader/FootnotePopupActivity.cpp").read_text(encoding="utf-8")
reader = Path("src/activities/reader/EpubReaderActivity.cpp").read_text(encoding="utf-8")

for token in [
    "constexpr int POPUP_HEIGHT = 600;",
    "std::max(0, (screenH - popupH) / 2 - 40)",
]:
    if token not in popup:
        raise SystemExit("CPHUN-141 popup semantic check missing: " + token)

for token in [
    "std::make_unique<EpubReaderFootnotesActivity>(renderer, mappedInput, currentPageFootnotes)",
    "std::find_if(currentPageFootnotes.begin(), currentPageFootnotes.end()",
]:
    if token not in reader:
        raise SystemExit("CPHUN-141 lifetime-safe multi-footnote path missing: " + token)

for forbidden in [
    "const auto notes = currentPageFootnotes;",
    "std::make_unique<EpubReaderFootnotesActivity>(renderer, mappedInput, notes)",
]:
    if forbidden in reader:
        raise SystemExit("CPHUN-141 dangling local footnote-list source still present: " + forbidden)

if "openSearchFootnoteOrWordSelect(mode);" not in reader:
    raise SystemExit("CPHUN-141 lost #139 Search flow")

print("CPHUN-141 semantic verification passed")
PY

git diff --check
