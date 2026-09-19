#!/usr/bin/env bash
set -euo pipefail

bash tools/build_cphun141_exp.sh
python3 tools/cphun142_footnote_navigation_patch.py

python3 - <<'PY'
from pathlib import Path
import re

bid=Path("src/CPHUNBuildId.h")
s=bid.read_text(encoding="utf-8")
s,n=re.subn(r'#define CPHUN_BUILD_ID "[^"]+"',
            '#define CPHUN_BUILD_ID "CPHUN-260919-142-EXP"',s,count=1)
if n!=1:
    raise SystemExit("CPHUN-142 build id replacement failed")
bid.write_text(s,encoding="utf-8")

ar=Path("src/activities/ActivityResult.h").read_text(encoding="utf-8")
popup_h=Path("src/activities/reader/FootnotePopupActivity.h").read_text(encoding="utf-8")
popup=Path("src/activities/reader/FootnotePopupActivity.cpp").read_text(encoding="utf-8")
reader_h=Path("src/activities/reader/EpubReaderActivity.h").read_text(encoding="utf-8")
reader=Path("src/activities/reader/EpubReaderActivity.cpp").read_text(encoding="utf-8")

for token in [
    "struct FootnotePopupNavResult",
    "FootnotePopupNavResult, FilePathResult",
]:
    if token not in ar:
        raise SystemExit("CPHUN-142 ActivityResult missing: "+token)

for token in [
    "bool canNavigateSiblings = false",
    "bool canNavigateSiblings_ = false",
]:
    if token not in popup_h:
        raise SystemExit("CPHUN-142 popup header missing: "+token)

for token in [
    'setResult(FootnotePopupNavResult{-1});',
    'setResult(FootnotePopupNavResult{1});',
    '"Előző"',
    '"Következő"',
]:
    if token not in popup:
        raise SystemExit("CPHUN-142 popup navigation missing: "+token)

for token in [
    "openFootnotePopupSession(bool wholeBook, bool returnToMenu, int sourceSpineIndex, int noteIndex)",
    "openSearchFootnoteList(WordSelectionMode mode, int sourceSpineIndex)",
    "openSearchFootnotePopup(WordSelectionMode mode, int sourceSpineIndex, int noteIndex)",
]:
    if token not in reader_h:
        raise SystemExit("CPHUN-142 reader declaration missing: "+token)

for token in [
    "void EpubReaderActivity::openFootnotePopupSession",
    "openFootnotesList(wholeBook, returnToMenu, sourceSpineIndex);",
    "std::get_if<FootnotePopupNavResult>",
    "openSearchFootnoteList(mode, sourceSpineIndex);  // Vissza -> list",
    "openDictionaryWordSelect(mode);  // Vissza from list -> selected word mode",
    "noteIndex + nav->delta",
]:
    if token not in reader:
        raise SystemExit("CPHUN-142 reader flow missing: "+token)

if "constexpr int POPUP_HEIGHT = 600;" not in popup:
    raise SystemExit("CPHUN-142 lost #141 popup height")
if "std::max(0, (screenH - popupH) / 2 - 40)" not in popup:
    raise SystemExit("CPHUN-142 lost #141 popup offset")

print("CPHUN-142 semantic verification passed")
PY

git diff --check
