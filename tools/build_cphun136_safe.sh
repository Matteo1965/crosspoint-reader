#!/usr/bin/env bash
set -euo pipefail

# Start from the latest known-good R4K2F11 chain (F12 was a failed patch-anchor experiment).
bash tools/build_cphun135r4k2f11_safe.sh
python3 tools/cphun136_finalize_spacing_and_margins_patch.py

python3 - <<'PY'
from pathlib import Path
import re
bid = Path('src/CPHUNBuildId.h')
s = bid.read_text(encoding='utf-8')
s, n = re.subn(r'#define CPHUN_BUILD_ID "[^"]+"',
               '#define CPHUN_BUILD_ID "CPHUN-260918-136-SAFE"', s, count=1)
if n != 1:
    raise SystemExit('CPHUN-136 build ID define not found')
bid.write_text(s, encoding='utf-8')
PY

git diff --check

python3 - <<'PY'
from pathlib import Path

ui = Path('src/activities/settings/TextSettingsActivity.cpp').read_text(encoding='utf-8')
settings_h = Path('src/CrossPointSettings.h').read_text(encoding='utf-8')
settings_cpp = Path('src/CrossPointSettings.cpp').read_text(encoding='utf-8')
reader = Path('src/activities/reader/EpubReaderActivity.cpp').read_text(encoding='utf-8')

# Letter-spacing optimization final semantics.
if 'SETTINGS.letterSpacingOptimization = SETTINGS.letterSpacingOptimization ? 0 : 4;' not in ui:
    raise SystemExit('CPHUN-136: OFF/ON letter-spacing toggle missing')
if '"25%", "50%", "75%", "100%"' in ui:
    raise SystemExit('CPHUN-136: retired optimization percentage picker still present')
if '(doc["letterSpacingOptimization"] | (uint8_t)0) ? 4 : 0' not in settings_cpp:
    raise SystemExit('CPHUN-136: legacy optimization migration missing')
if 'configured == ReaderAction::LetterSpacingOptimizationUp ? 4 : 0' not in reader:
    raise SystemExit('CPHUN-136: hardware optimization actions can still create intermediate profiles')

# Margin scale.
if 'constexpr uint8_t MARGIN_VALUES[] = {5, 10, 12, 14, 16, 18, 20, 25};' not in ui:
    raise SystemExit('CPHUN-136: requested margin scale missing')
if 'SCREEN_MARGIN_MIN = 5' not in settings_h or 'SCREEN_MARGIN_MAX = 25' not in settings_h:
    raise SystemExit('CPHUN-136: stored margin range not expanded to 5..25')

# Vertical rule.
rule = 'SETTINGS.screenMargin == 5 ? 4 : std::max(0, static_cast<int>(SETTINGS.screenMargin) - 6)'
if reader.count(rule) < 2:
    raise SystemExit('CPHUN-136: vertical margin rule missing from reader/selection paths')
if 'orientedMarginTop = std::max(0, orientedMarginTop - 6);' in reader:
    raise SystemExit('CPHUN-136: historical extra top -6 adjustment still present')
if 'orientedMarginBottom = std::max(0, orientedMarginBottom - 6);' in reader:
    raise SystemExit('CPHUN-136: historical extra bottom -6 adjustment still present')

# Preserve prior F10/F11 features.
if 'const uint8_t utf8Bom[] = {0xEF, 0xBB, 0xBF};' not in reader:
    raise SystemExit('CPHUN-136: TSV UTF-8 BOM fix missing')
menu = Path('src/activities/reader/EpubReaderMenuActivity.cpp').read_text(encoding='utf-8')
b = menu.find('std::vector<EpubReaderMenuActivity::MenuItem> EpubReaderMenuActivity::buildMoreItems')
e = menu.find('const std::vector<EpubReaderMenuActivity::MenuItem>&', b)
book = menu[b:e]
if not (0 <= book.find('MenuAction::DISPLAY_QR') < book.find('MenuAction::EXPORT_EDITS') < book.find('MenuAction::SYNC')):
    raise SystemExit('CPHUN-136: QR -> export -> sync ordering lost')

print('CPHUN-136 semantic verification passed')
PY
