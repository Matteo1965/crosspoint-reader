#!/usr/bin/env bash
set -euo pipefail

# Use the CPHUN-149 source and preserve all previously validated formatting,
# font-profile, input, sleep-state and OTA patches.
bash tools/build_cphun149_spacing_exp.sh
python3 tools/cphun150_cache_resume_patch.py

python3 - <<'PY'
from pathlib import Path
reader = Path("src/activities/reader/EpubReaderActivity.cpp").read_text(encoding="utf-8")
section = Path("lib/Epub/Epub/Section.cpp").read_text(encoding="utf-8")
bid = Path("src/CPHUNBuildId.h").read_text(encoding="utf-8")
assert reader.count("captureReaderLayout(buildViewportWidth, buildViewportHeight)") == 3
assert reader.count("readerLayoutMatches(before, buildViewportWidth, buildViewportHeight)") == 3
assert reader.count("retaining section") == 3
for field in ("fontId", "lineCompression", "extraParagraphSpacing", "paragraphAlignment",
              "viewportWidth", "viewportHeight", "hyphenationEnabled",
              "hungarianHyphenationExtended", "hangingPunctuationLimitPx",
              "shortHyphen", "fixedDialogueSpacing", "minimumSpacePercent",
              "letterSpacingLimitPercent", "embeddedStyle", "imageRendering",
              "focusReadingEnabled"):
    assert f"old.{field} == current.{field}" in reader, field
assert "CPHUN-150 cache mismatch" in section
assert "Section::~Section() { suspendBuild(); }" in section
assert "version != SECTION_FILE_VERSION && version != SECTION_FILE_PARTIAL_VERSION" in section
assert "CPHUN-260925-150-EXP" in bid
print("CPHUN-150 semantic regression checks passed")
PY
git diff --check
