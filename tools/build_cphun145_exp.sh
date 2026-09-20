#!/usr/bin/env bash
set -euo pipefail

bash tools/build_cphun144_exp.sh
python3 tools/cphun145_publish_candidate_patch.py

python3 - <<'PY'
from pathlib import Path
import re

bid = Path("src/CPHUNBuildId.h")
s = bid.read_text(encoding="utf-8")
s, n = re.subn(r'#define CPHUN_BUILD_ID "[^"]+"',
               '#define CPHUN_BUILD_ID "CPHUN-260920-145-EXP"', s, count=1)
if n != 1:
    raise SystemExit("CPHUN-145 build id replacement failed")

if re.search(r'^#define CPHUN_BUILD_DATE ', s, re.M):
    s = re.sub(r'^#define CPHUN_BUILD_DATE .*$', '#define CPHUN_BUILD_DATE "Sep-20 2026"', s, count=1, flags=re.M)
else:
    if not s.endswith("\n"):
        s += "\n"
    s += '#define CPHUN_BUILD_DATE "Sep-20 2026"\n'
bid.write_text(s, encoding="utf-8")

popup = Path("src/activities/reader/FootnotePopupActivity.cpp").read_text(encoding="utf-8")
version = Path("src/activities/settings/CrossPointVersionActivity.cpp").read_text(encoding="utf-8")

for token in [
    "constexpr int POPUP_HEIGHT = 680;",
    "constexpr int POPUP_TOP_REFERENCE_HEIGHT = 640;",
    "footnoteNumberOnly",
    '"Lábjegyzet {" + number + "}"',
    "visual continuation cue",
    "renderer.drawLine(arrowX - 5",
    "renderer.drawLine(arrowX + 5",
]:
    if token not in popup:
        raise SystemExit("CPHUN-145 popup missing: " + token)

for token in [
    "const int paragraphSpacing = currentPage == 0 ? bodyLineHeight : std::max(1, bodyLineHeight / 2);",
    '"Betűköz-optimalizálás"',
    '"Font- és betűpár-alapú korrekció, állítható optimalizációs küszöbbel."',
    '"- Megjelölés és Szerkesztés mód"',
    '"- Mód választó: Szótár / Megjelölés / Szerkesztés"',
    '"- Szerkesztések exportálása TSV fájlba"',
    '"- Továbbfejlesztett lábjegyzet-kezelés"',
    '"- Több lábjegyzet kezelése és közvetlen megnyitása"',
]:
    if token not in version:
        raise SystemExit("CPHUN-145 version page missing: " + token)

for forbidden in [
    "Előző / Következő lábjegyzet",
    "görgethető, sorkizárt és magyar elválasztású lábjegyzetszöveg",
]:
    if forbidden in version:
        raise SystemExit("CPHUN-145 forbidden version text present: " + forbidden)

print("CPHUN-145 semantic verification passed")
PY

git diff --check
