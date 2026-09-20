#!/usr/bin/env bash
set -euo pipefail

# CPHUN-144 workflow trigger
bash tools/build_cphun143_exp.sh
python3 tools/cphun144_footnote_ux_stability_patch.py

python3 - <<'PY'
from pathlib import Path
import re

bid = Path("src/CPHUNBuildId.h")
s = bid.read_text(encoding="utf-8")
s, n = re.subn(r'#define CPHUN_BUILD_ID "[^"]+"',
               '#define CPHUN_BUILD_ID "CPHUN-260920-144-EXP"', s, count=1)
if n != 1:
    raise SystemExit("CPHUN-144: build id replacement failed")
bid.write_text(s, encoding="utf-8")

popup = Path("src/activities/reader/FootnotePopupActivity.cpp").read_text(encoding="utf-8")
popup_h = Path("src/activities/reader/FootnotePopupActivity.h").read_text(encoding="utf-8")
reader = Path("src/activities/reader/EpubReaderActivity.cpp").read_text(encoding="utf-8")
reader_h = Path("src/activities/reader/EpubReaderActivity.h").read_text(encoding="utf-8")

for token in [
    "constexpr int POPUP_HEIGHT = 640;",
    "EpdFontFamily::BOLD",
    "lineHeight / 2",
    'Hyphenator::breakOffsetsForLanguageExtended(source, false, "hu")',
    "lineJustified_",
]:
    if token not in popup and token not in popup_h:
        raise SystemExit("CPHUN-144 popup missing: " + token)

for token in [
    "openSearchFootnotePopup(mode, sourceSpine, 0);",
    "Shortcut: Vissza -> selected word mode, never the list.",
    "getCachedCurrentPageFootnoteText",
    "Extract begin note=",
    "Extract end note=",
    "FOOTNOTE_TEXT_CACHE_SLOTS = 8",
]:
    if token not in reader and token not in reader_h:
        raise SystemExit("CPHUN-144 reader missing: " + token)

if "std::make_unique<EpubReaderFootnotesActivity>(renderer, mappedInput, notes)" not in reader:
    raise SystemExit("CPHUN-144 lost Reader-menu list-first path")
if "openFootnotesList(wholeBook, returnToMenu, sourceSpineIndex);" not in reader:
    raise SystemExit("CPHUN-144 lost popup Back -> list on Reader-menu path")

for token in [
    "MappedInputManager::Button::Up",
    "MappedInputManager::Button::Down",
    "MappedInputManager::Button::Left",
    "MappedInputManager::Button::Right",
    "mappedInput.isNavDirectionSwapped() ? 1 : -1",
    "mappedInput.isNavDirectionSwapped() ? -1 : 1",
]:
    if token not in popup:
        raise SystemExit("CPHUN-144 lost #143 mapping: " + token)

print("CPHUN-144 semantic verification passed")
PY

git diff --check
