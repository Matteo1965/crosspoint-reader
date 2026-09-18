#!/usr/bin/env bash
set -euo pipefail

bash tools/build_cphun136r2_safe.sh
python3 tools/cphun136r3_word_selector_mode_patch.py

python3 - <<'PY'
from pathlib import Path
import re

p = Path("src/CPHUNBuildId.h")
s = p.read_text(encoding="utf-8")
s, n = re.subn(r'#define CPHUN_BUILD_ID "[^"]+"',
               '#define CPHUN_BUILD_ID "CPHUN-260918-136R3-SAFE"', s, count=1)
if n != 1:
    raise SystemExit("CPHUN-136R3: build id replacement failed")
p.write_text(s, encoding="utf-8")
PY

git diff --check

python3 - <<'PY'
from pathlib import Path

menu = Path("src/activities/reader/EpubReaderMenuActivity.cpp").read_text(encoding="utf-8")
reader = Path("src/activities/reader/EpubReaderActivity.cpp").read_text(encoding="utf-8")
settings_h = Path("src/CrossPointSettings.h").read_text(encoding="utf-8")
settings_cpp = Path("src/CrossPointSettings.cpp").read_text(encoding="utf-8")

checks = [
    ('"Mód választó"', menu),
    ('{"Szótár", "Megjelölés", "Szerkesztés"}', menu),
    ('SETTINGS.wordSelectionMode = static_cast<uint8_t>(idx);', menu),
    ('uint8_t wordSelectionMode = 0;', settings_h),
    ('doc["wordSelectionMode"] = wordSelectionMode;', settings_cpp),
    ('SETTINGS.wordSelectionMode == 1', reader),
    ('SETTINGS.wordSelectionMode == 2', reader),
    ('openDictionaryWordSelect(mode)', reader),
]
for token, text in checks:
    if token not in text:
        raise SystemExit(f"CPHUN-136R3 semantic check missing: {token}")

# Direct Reader menu entries remain fixed modes; only hardware OpenDictionary follows the selector setting.
for token in [
    'openDictionaryWordSelect(WordSelectionMode::Dictionary)',
    'openDictionaryWordSelect(WordSelectionMode::Highlight)',
    'openDictionaryWordSelect(WordSelectionMode::Edit)',
]:
    if token not in reader:
        raise SystemExit(f"CPHUN-136R3 direct-mode regression: {token}")

print("CPHUN-136R3 semantic verification passed")
PY
