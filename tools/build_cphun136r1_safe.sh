#!/usr/bin/env bash
set -euo pipefail

bash tools/build_cphun136_safe.sh
python3 tools/cphun136r1_reader_menu_word_selector_patch.py

python3 - <<'PY'
from pathlib import Path
import re
bid = Path('src/CPHUNBuildId.h')
s = bid.read_text(encoding='utf-8')
s, n = re.subn(r'#define CPHUN_BUILD_ID "[^"]+"',
               '#define CPHUN_BUILD_ID "CPHUN-260918-136R1-SAFE"', s, count=1)
if n != 1:
    raise SystemExit('CPHUN-136R1 build ID define not found')
bid.write_text(s, encoding='utf-8')
PY

git diff --check

python3 - <<'PY'
from pathlib import Path

menu = Path('src/activities/reader/EpubReaderMenuActivity.cpp').read_text(encoding='utf-8')
menu_h = Path('src/activities/reader/EpubReaderMenuActivity.h').read_text(encoding='utf-8')
selector = Path('src/activities/reader/DictionaryWordSelectActivity.cpp').read_text(encoding='utf-8')
reader = Path('src/activities/reader/EpubReaderActivity.cpp').read_text(encoding='utf-8')

b = menu.find('std::vector<EpubReaderMenuActivity::MenuItem> EpubReaderMenuActivity::buildMoreItems')
e = menu.find('const std::vector<EpubReaderMenuActivity::MenuItem>&', b)
book = menu[b:e]
if 'MenuAction::GO_HOME' in book:
    raise SystemExit('CPHUN-136R1: GO_HOME still present on Könyv tab')

for token in ['"Szótár"', '"Megjelölés"', '"Szerkesztés"']:
    if token not in menu:
        raise SystemExit(f'CPHUN-136R1: direct mode menu label missing: {token}')

if 'dictionaryRowLabel = "Szótár: ";' not in menu or 'menuRowItems[i].value = nullptr;' not in menu:
    raise SystemExit('CPHUN-136R1: compact left-aligned dictionary row missing')
if 'std::string dictionaryRowLabel;' not in menu_h:
    raise SystemExit('CPHUN-136R1: dictionary row backing storage missing')

for token in ['"Keresés"', '"Megjelölés"', '"Szerkesztés"']:
    if token not in selector:
        raise SystemExit(f'CPHUN-136R1: selector confirm label missing: {token}')
if selector.count('mode == WordSelectionMode::Highlight || mode == WordSelectionMode::Edit') < 2:
    raise SystemExit('CPHUN-136R1: unified selector routing missing')

for token in [
    'openDictionaryWordSelect(WordSelectionMode::Dictionary)',
    'openDictionaryWordSelect(WordSelectionMode::Highlight)',
    'openDictionaryWordSelect(WordSelectionMode::Edit)',
]:
    if token not in reader:
        raise SystemExit(f'CPHUN-136R1: reader dispatch missing: {token}')

# Preserve CPHUN-136 features.
settings_ui = Path('src/activities/settings/TextSettingsActivity.cpp').read_text(encoding='utf-8')
if 'constexpr uint8_t MARGIN_VALUES[] = {5, 10, 12, 14, 16, 18, 20, 25};' not in settings_ui:
    raise SystemExit('CPHUN-136R1: CPHUN-136 margin scale lost')
if 'SETTINGS.letterSpacingOptimization = SETTINGS.letterSpacingOptimization ? 0 : 4;' not in settings_ui:
    raise SystemExit('CPHUN-136R1: CPHUN-136 spacing toggle lost')
if 'const uint8_t utf8Bom[] = {0xEF, 0xBB, 0xBF};' not in reader:
    raise SystemExit('CPHUN-136R1: UTF-8 BOM export lost')

print('CPHUN-136R1 semantic verification passed')
PY
