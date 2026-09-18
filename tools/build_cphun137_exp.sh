#!/usr/bin/env bash
set -euo pipefail

bash tools/build_cphun136r3_safe.sh
python3 tools/cphun137_bitter_score_threshold_patch.py

python3 - <<'PY'
from pathlib import Path
import csv
import re

bid = Path("src/CPHUNBuildId.h")
s = bid.read_text(encoding="utf-8")
s, n = re.subn(r'#define CPHUN_BUILD_ID "[^"]+"',
               '#define CPHUN_BUILD_ID "CPHUN-260918-137-EXP"', s, count=1)
if n != 1:
    raise SystemExit("CPHUN-137: build id replacement failed")
bid.write_text(s, encoding="utf-8")

ui = Path("src/activities/settings/TextSettingsActivity.cpp").read_text(encoding="utf-8")
settings_h = Path("src/CrossPointSettings.h").read_text(encoding="utf-8")
settings_cpp = Path("src/CrossPointSettings.cpp").read_text(encoding="utf-8")
opt = Path("lib/Epub/Epub/LetterSpacingOptimization.h").read_text(encoding="utf-8")
parsed_h = Path("lib/Epub/Epub/ParsedText.h").read_text(encoding="utf-8")
parsed_cpp = Path("lib/Epub/Epub/ParsedText.cpp").read_text(encoding="utf-8")
render = Path("lib/Epub/Epub/blocks/TextBlock.cpp").read_text(encoding="utf-8")

for token in [
    "Optimalizációs küszöb",
    '"50", "55", "60", "65", "70", "75"',
    "letterSpacingOptimizationThreshold = 60",
]:
    haystack = ui + settings_h
    if token not in haystack:
        raise SystemExit("CPHUN-137 missing UI/settings token: " + token)

if 'doc["letterSpacingOptimizationThreshold"] = letterSpacingOptimizationThreshold;' not in settings_cpp:
    raise SystemExit("CPHUN-137 threshold persistence missing")
if "BitterSpacingScores::scoreForPair(left, right, pointSize) >= threshold" not in opt:
    raise SystemExit("CPHUN-137 Bitter score lookup missing")
if "NOTOSERIF_16_OPTIMIZABLE_PAIRS" not in opt:
    raise SystemExit("CPHUN-137 Noto Serif 16 table lost")
if "constexpr uint32_t OPTIMIZABLE_PAIRS[]" in opt:
    raise SystemExit("CPHUN-137 old fixed Bitter table still present")
if "unpackProfile" in opt + parsed_cpp + render:
    raise SystemExit("CPHUN-137 retired packed profile decoding still present")
if "letterSpacingOptimizationThresholdCode" not in parsed_h + parsed_cpp:
    raise SystemExit("CPHUN-137 threshold code not carried through ParsedText")
if opt.count("pointSizeForFont(") < 1 or parsed_cpp.count("pointSizeForFont(") < 2 or render.count("pointSizeForFont(") < 2:
    raise SystemExit("CPHUN-137 point-size-specific routing incomplete")

rows = list(csv.DictReader(Path("tools/data/Bitter12-18_spacing_scores.csv").open(encoding="utf-8")))
if len(rows) != 1225:
    raise SystemExit(f"CPHUN-137 score table row count={len(rows)}")
counts = {}
for size in (12, 14, 16, 18):
    vals = [int(r[f"score{size}"]) for r in rows]
    counts[size] = {t: sum(v >= t for v in vals) for t in (50,55,60,65,70,75)}
if counts[16][60] != 655:
    raise SystemExit(f"CPHUN-137 16pt/60 calibration broken: {counts[16][60]}")
print("CPHUN-137 calibrated counts:", counts)
print("CPHUN-137 semantic verification passed")
PY

git diff --check
