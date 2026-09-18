#!/usr/bin/env bash
set -euo pipefail

bash tools/build_cphun136r1_safe.sh
python3 tools/cphun136r2_menu_unification_selector_verify_patch.py

python3 - <<'PY'
from pathlib import Path
import re

p = Path("src/CPHUNBuildId.h")
s = p.read_text(encoding="utf-8")
s, n = re.subn(r'#define CPHUN_BUILD_ID "[^"]+"',
               '#define CPHUN_BUILD_ID "CPHUN-260918-136R2-SAFE"', s, count=1)
if n != 1:
    raise SystemExit("CPHUN-136R2: build id replacement failed")
p.write_text(s, encoding="utf-8")
PY

git diff --check

python3 - <<'PY'
from pathlib import Path

hu = Path("lib/I18n/translations/hungarian.yaml").read_text(encoding="utf-8")
btn = Path("src/activities/settings/ButtonFunctionsActivity.cpp").read_text(encoding="utf-8")
menu = Path("src/activities/reader/EpubReaderMenuActivity.cpp").read_text(encoding="utf-8")
selector = Path("src/activities/reader/DictionaryWordSelectActivity.cpp").read_text(encoding="utf-8")
reader = Path("src/activities/reader/EpubReaderActivity.cpp").read_text(encoding="utf-8")

checks = [
    ('STR_NIGHT_MODE: "Sötét mód"', hu),
    ('STR_AUTO_TURN_PAGES_PER_MIN: "Auto. lapozás, lap/perc"', hu),
    ('"Olvasómenü"', btn),
    ('"Szótár"', btn),
    ('"Könyvjelző jelölés"', btn),
    ('"Sorköz +"', btn),
    ('"Sorköz −"', btn),
    ('"Sötét mód KI/BE"', btn),
    ('"Főoldal"', btn),
    ('"Auto. lapozás, lap/perc"', menu),
    ('"Keresés"', selector),
    ('"Megjelölés"', selector),
    ('"Szerkesztés"', selector),
]
for token, text in checks:
    if token not in text:
        raise SystemExit(f"CPHUN-136R2 semantic check missing: {token}")

for token in [
    "openDictionaryWordSelect(WordSelectionMode::Dictionary)",
    "openDictionaryWordSelect(WordSelectionMode::Highlight)",
    "openDictionaryWordSelect(WordSelectionMode::Edit)",
    "std::make_unique<DictionaryWordSelectActivity>",
]:
    if token not in reader:
        raise SystemExit(f"CPHUN-136R2 selector dispatch check missing: {token}")

print("CPHUN-136R2 semantic verification passed")
PY
