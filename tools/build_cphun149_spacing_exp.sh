#!/usr/bin/env bash
set -euo pipefail

# Preserve the tested CPHUN-148 OTA, footnote and UI patch chain.
bash tools/build_cphun148_exp.sh
python3 tools/cphun139_four_level_serif_patch.py

python3 - <<'PY'
from pathlib import Path
import csv

def require(path, token):
    content = Path(path).read_text(encoding="utf-8")
    if token not in content:
        raise SystemExit(f"CPHUN-149 missing {token} in {path}")
    return content

ui = require("src/activities/settings/TextSettingsActivity.cpp",
             "CPHUN139_CORRECTION_VALUES[] = {0, 550, 460, 280}")
require("src/activities/settings/TextSettingsActivity.cpp",
        'constexpr uint8_t values[] = {0, 50, 60, 70}')
require("src/activities/settings/TextSettingsActivity.cpp",
        '"Gyenge", "Közepes", "Erős"')
if '"50", "55", "60", "65", "70", "75"' in ui:
    raise SystemExit("CPHUN-149 obsolete threshold picker still present")

require("src/CrossPointSettings.cpp", "letterSpacingOptimizationThreshold == 0")
require("src/CrossPointSettings.cpp", "knownSdSerif")
require("src/CrossPointSettings.cpp", "isBuiltinSerif")
require("src/CrossPointSettings.cpp", "needsResave = true")
opt = require("lib/Epub/Epub/LetterSpacingOptimization.h", "code == 7 ? 0u")
require("lib/Epub/Epub/LetterSpacingOptimization.h", "notoMeasured60")
require("lib/Epub/Epub/LetterSpacingOptimization.h",
        "score > 0 && (threshold == 0 || score >= threshold)")
if "code >= 1 && code <= 6;" in opt:
    raise SystemExit("CPHUN-149 threshold bit-packing not upgraded")
require("lib/Epub/Epub/ParsedText.cpp", "pointSizeForFont(")
require("lib/Epub/Epub/blocks/TextBlock.cpp", "pointSizeForFont(")
require("src/CPHUNBuildId.h", "CPHUN-260925-149-EXP")

# Raw score table from earlier Bitter measurements is available in-repo;
# retain the previously calibrated 655 pairs at Bitter 16pt/60 points.
rows = list(csv.DictReader(Path("tools/data/Bitter12-18_spacing_scores.csv").open(encoding="utf-8")))
if len(rows) != 1225:
    raise SystemExit(f"Wrong number of Bitter pairs: {len(rows)}")
if sum(int(r["score16"]) >= 60 for r in rows) != 655:
    raise SystemExit("Original Bitter16/60 calibration changed")
for size in (12, 14, 16, 18):
    counts = [sum(int(r[f"score{size}"]) >= threshold for r in rows)
              for threshold in (50, 60, 70)]
    if counts[0] < counts[1] or counts[1] < counts[2]:
        raise SystemExit(f"Threshold monotonicity broken at {size} pt")
    print(f"Bitter {size}pt scores 50/60/70 => {counts}")
print("CPHUN-149 source assertions passed")
PY

git diff --check
