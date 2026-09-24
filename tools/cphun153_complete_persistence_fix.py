#!/usr/bin/env python3
"""Apply persistence fix AFTER the complete CPHUN-148/149/150 patch chain."""
from pathlib import Path
import re

settings = Path("src/CrossPointSettings.cpp")
ui = Path("src/activities/settings/TextSettingsActivity.cpp").read_text(encoding="utf-8")
reader = Path("src/activities/reader/EpubReaderActivity.cpp").read_text(encoding="utf-8")
s = settings.read_text(encoding="utf-8")

match = re.search(r'constexpr uint16_t LETTER_SPACING_THRESHOLDS\[\] = \{([^}]+)\};', ui)
if not match:
    raise SystemExit("CPHUN-153: post-149 correction table is missing")
values = [int(v.strip()) for v in match.group(1).split(",")]
expected = [0, 550, 520, 480, 430, 370, 300, 220]
if values != expected:
    raise SystemExit(f"CPHUN-153: unexpected active correction scale {values}")

old = '  constexpr uint16_t validLetterSpacingThresholds[] = {0, 550, 530, 500, 460, 410, 350, 280};'
new = '  constexpr uint16_t validLetterSpacingThresholds[] = {0, 550, 520, 480, 430, 370, 300, 220};'
if old not in s:
    raise SystemExit("CPHUN-153: loader threshold table anchor missing")
s = s.replace(old, new, 1)
settings.write_text(s, encoding="utf-8")

# Reader hardware actions must use exactly the same persisted scale as Text Settings.
reader_path = Path("src/activities/reader/EpubReaderActivity.cpp")
reader = reader_path.read_text(encoding="utf-8")
reader = reader.replace(
    "constexpr uint16_t values[] = {0, 360, 340, 320, 300, 280, 260, 240};",
    "constexpr uint16_t values[] = {0, 550, 520, 480, 430, 370, 300, 220};"
)
reader = reader.replace(
    "SETTINGS.letterSpacingLimitPercent = SETTINGS.letterSpacingLimitPercent == 360 ? 240 : 360;",
    "SETTINGS.letterSpacingLimitPercent = SETTINGS.letterSpacingLimitPercent == 550 ? 220 : 550;"
)
reader_path.write_text(reader, encoding="utf-8")
if "0, 550, 520, 480, 430, 370, 300, 220" not in reader:
    raise SystemExit("CPHUN-153: reader correction scale could not be aligned")

bid = Path("src/CPHUNBuildId.h")
t = bid.read_text(encoding="utf-8")
t, n = re.subn(r'#define CPHUN_BUILD_ID "[^"]+"',
               '#define CPHUN_BUILD_ID "CPHUN-260924-153-FULL"', t, count=1)
if n != 1:
    raise SystemExit("CPHUN-153: build ID missing")
bid.write_text(t, encoding="utf-8")
print("CPHUN-153: correction persistence and release ID applied")
