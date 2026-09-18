#!/usr/bin/env bash
set -euo pipefail

bash tools/build_cphun138_exp.sh
python3 tools/cphun139_footnote_search_ui_patch.py

python3 - <<'PY'
from pathlib import Path
import re

bid = Path("src/CPHUNBuildId.h")
s = bid.read_text(encoding="utf-8")
s, n = re.subn(r'#define CPHUN_BUILD_ID "[^"]+"',
               '#define CPHUN_BUILD_ID "CPHUN-260918-139-EXP"', s, count=1)
if n != 1:
    raise SystemExit("CPHUN-139: build id replacement failed")
bid.write_text(s, encoding="utf-8")

popup = Path("src/activities/reader/FootnotePopupActivity.cpp").read_text(encoding="utf-8")
reader = Path("src/activities/reader/EpubReaderActivity.cpp").read_text(encoding="utf-8")
reader_h = Path("src/activities/reader/EpubReaderActivity.h").read_text(encoding="utf-8")
menu = Path("src/activities/reader/EpubReaderMenuActivity.cpp").read_text(encoding="utf-8")

for token in [
    "constexpr int POPUP_HEIGHT = 530;",
    '"Lábjegyzet {" + label_ + "}"',
    "stripRepeatedFootnoteMarker",
]:
    if token not in popup:
        raise SystemExit("CPHUN-139 popup semantic check missing: " + token)

mode = menu.find('MenuAction::WORD_SELECTION_MODE')
auto = menu.find('MenuAction::AUTO_PAGE_TURN')
if not (0 <= mode < auto):
    raise SystemExit("CPHUN-139: Mód választó is not before Auto. lapozás")
if menu.count('MenuAction::WORD_SELECTION_MODE, StrId::STR_LOOKUP, "Mód választó"') != 1:
    raise SystemExit("CPHUN-139: Mód választó row count is not exactly one")

for token in [
    "void EpubReaderActivity::openSearchFootnoteOrWordSelect",
    "if (currentPageFootnotes.empty())",
    "std::make_unique<FootnotePopupActivity>(renderer, mappedInput, note.number, std::move(text), true)",
    "if (popupResult.isCancelled) openDictionaryWordSelect(mode);",
    "openSearchFootnoteOrWordSelect(mode);",
]:
    if token not in reader:
        raise SystemExit("CPHUN-139 Search flow semantic check missing: " + token)

if "void openSearchFootnoteOrWordSelect(WordSelectionMode mode);" not in reader_h:
    raise SystemExit("CPHUN-139 Search flow declaration missing")

# Explicit Reader-menu modes remain direct and do not inherit the footnote-first
# hardware Search behavior.
for token in [
    "openDictionaryWordSelect(WordSelectionMode::Dictionary);",
    "openDictionaryWordSelect(WordSelectionMode::Highlight);",
    "openDictionaryWordSelect(WordSelectionMode::Edit);",
]:
    if token not in reader:
        raise SystemExit("CPHUN-139 direct menu mode regression: " + token)

# #137/#138 features must remain present through the chain.
settings_ui = Path("src/activities/settings/TextSettingsActivity.cpp").read_text(encoding="utf-8")
if "Optimalizációs küszöb" not in settings_ui:
    raise SystemExit("CPHUN-139 lost #137 optimization threshold UI")
if "tab_ == Tab::Layout ? metrics_.buttonHintsHeight" not in settings_ui:
    raise SystemExit("CPHUN-139 lost #138 Layout list-height extension")

print("CPHUN-139 semantic verification passed")
PY

git diff --check
