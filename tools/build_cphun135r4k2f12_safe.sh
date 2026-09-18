#!/usr/bin/env bash
set -euo pipefail

bash tools/build_cphun135r4k2f11_safe.sh
python3 tools/cphun135r4k2f12_letter_spacing_toggle_patch.py

python3 - <<'PY'
from pathlib import Path
import re
bid = Path('src/CPHUNBuildId.h')
s = bid.read_text(encoding='utf-8')
s, n = re.subn(r'#define CPHUN_BUILD_ID "[^"]+"',
               '#define CPHUN_BUILD_ID "CPHUN-260918-135R4K2F12-SAFE"', s, count=1)
if n != 1:
    raise SystemExit('R4K2F12 build ID define not found')
bid.write_text(s, encoding='utf-8')
PY

git diff --check

python3 - <<'PY'
from pathlib import Path
settings = Path('src/CrossPointSettings.cpp').read_text(encoding='utf-8')
ui = Path('src/activities/settings/TextSettingsActivity.cpp').read_text(encoding='utf-8')
header = Path('src/CrossPointSettings.h').read_text(encoding='utf-8')

if '(doc["letterSpacingOptimization"] | (uint8_t)0) ? 4 : 0' not in settings:
    raise SystemExit('R4K2F12: legacy profile migration missing')
if '&& letterSpacingOptimization' not in settings or '? 4' not in settings:
    raise SystemExit('R4K2F12: enabled optimization is not forced to profile 4')
if 'SETTINGS.letterSpacingOptimization = SETTINGS.letterSpacingOptimization ? 0 : 4;' not in ui:
    raise SystemExit('R4K2F12: direct OFF/ON toggle missing')
if 'const char* options[] = {tr(STR_STATE_OFF), "25%", "50%", "75%", "100%"};' in ui:
    raise SystemExit('R4K2F12: percentage picker still present')
if 'return SETTINGS.letterSpacingOptimization ? tr(STR_STATE_ON) : tr(STR_STATE_OFF);' not in ui:
    raise SystemExit('R4K2F12: OFF/ON display missing')
if '0=off, 4=on' not in header:
    raise SystemExit('R4K2F12: setting documentation missing')
print('R4K2F12 semantic verification passed')
PY
