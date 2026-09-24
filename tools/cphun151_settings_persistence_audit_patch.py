#!/usr/bin/env python3
from pathlib import Path

def replace_once(path, old, new, label):
    p=Path(path); s=p.read_text(encoding="utf-8"); n=s.count(old)
    if n!=1: raise SystemExit(f"CPHUN-151 {label}: expected 1, found {n}")
    p.write_text(s.replace(old,new,1),encoding="utf-8")

# New correction scale must be accepted verbatim on wake/reboot.
replace_once(
 "src/CrossPointSettings.cpp",
 """  if (letterSpacingLimitPercent != 0 && letterSpacingLimitPercent != 200 && letterSpacingLimitPercent != 250 &&
      letterSpacingLimitPercent != 300 && letterSpacingLimitPercent != 350 && letterSpacingLimitPercent != 400 &&
      letterSpacingLimitPercent != 450 && letterSpacingLimitPercent != 500) {
    letterSpacingLimitPercent = 0;
    needsResave = true;
  }""",
 """  if (letterSpacingLimitPercent != 0 && letterSpacingLimitPercent != 550 && letterSpacingLimitPercent != 520 &&
      letterSpacingLimitPercent != 480 && letterSpacingLimitPercent != 430 && letterSpacingLimitPercent != 370 &&
      letterSpacingLimitPercent != 300 && letterSpacingLimitPercent != 220) {
    letterSpacingLimitPercent = 0;
    needsResave = true;
  }""",
 "letter-spacing correction load validation")

# Reader hardware actions must use exactly the same persisted scale as Text Settings.
p=Path("src/activities/reader/EpubReaderActivity.cpp")
s=p.read_text(encoding="utf-8")
s=s.replace("constexpr uint16_t values[] = {0, 360, 340, 320, 300, 280, 260, 240};",
            "constexpr uint16_t values[] = {0, 550, 520, 480, 430, 370, 300, 220};")
s=s.replace("SETTINGS.letterSpacingLimitPercent = SETTINGS.letterSpacingLimitPercent == 360 ? 240 : 360;",
            "SETTINGS.letterSpacingLimitPercent = SETTINGS.letterSpacingLimitPercent == 550 ? 220 : 550;")
p.write_text(s,encoding="utf-8")

# Semantic persistence audit for CPHUN-only/manual settings.
cpp=Path("src/CrossPointSettings.cpp").read_text(encoding="utf-8")
required_pairs={
 "letterSpacingLimitPercent": ['doc["letterSpacingLimitPercent"] = letterSpacingLimitPercent;',
                               'letterSpacingLimitPercent = doc["letterSpacingLimitPercent"] | (uint16_t)0;'],
 "letterSpacingOptimization": ['doc["letterSpacingOptimization"] = letterSpacingOptimization;',
                               'doc["letterSpacingOptimization"] | (uint8_t)0'],
 "letterSpacingOptimizationThreshold": ['doc["letterSpacingOptimizationThreshold"] = letterSpacingOptimizationThreshold;',
                                        'doc["letterSpacingOptimizationThreshold"] | (uint8_t)60'],
 "hyphenationThreshold": ['doc["hyphenationThreshold"] = hyphenationThreshold;',
                          'hyphenationThreshold = doc["hyphenationThreshold"] | (uint8_t)2;'],
 "wordSelectionMode": ['doc["wordSelectionMode"] = wordSelectionMode;',
                       'doc["wordSelectionMode"] | (uint8_t)0'],
 "shortHyphen": ['doc["shortHyphen"] = shortHyphen;', 'doc["shortHyphen"] | (uint8_t)0'],
 "fixedDialogueSpacing": ['doc["fixedDialogueSpacing"] = fixedDialogueSpacing;',
                          'doc["fixedDialogueSpacing"] | (uint8_t)0'],
 "softHyphenEnabled": ['doc["softHyphenEnabled"] = softHyphenEnabled;',
                       'doc["softHyphenEnabled"] | (uint8_t)0'],
 "minimumSpacePercent": ['doc["minimumSpacePercent"] = minimumSpacePercent;',
                         'doc["minimumSpacePercent"] | (uint8_t)100'],
 "hangingPunctuation": ['doc["hangingPunctuation"] = hangingPunctuation;',
                        'doc["hangingPunctuation"]'],
 "extraParagraphSpacingEnabled": ['doc["extraParagraphSpacingEnabled"] = extraParagraphSpacingEnabled;',
                                  'doc["extraParagraphSpacingEnabled"]'],
}
for name,tokens in required_pairs.items():
    for token in tokens:
        if token not in cpp:
            raise SystemExit(f"CPHUN-151 persistence audit failed for {name}: {token}")

# The remaining ordinary settings are persisted through SettingsListBase.
settings_list=Path("src/SettingsListBase.h").read_text(encoding="utf-8")
for field in [
 "screenMargin","lineSpacing","paragraphAlignment","embeddedStyle","focusReadingEnabled",
 "hyphenationEnabled","hungarianHyphenationExtended","textAntiAliasing","imageRendering",
 "orientation","screenInverted","sleepTimeoutMinutes","refreshFrequency"
]:
    if f"&CrossPointSettings::{field}" not in settings_list:
        raise SystemExit(f"CPHUN-151 generic persistence entry missing: {field}")

# New scale consistency across UI, hardware action and loader.
ui=Path("src/activities/settings/TextSettingsActivity.cpp").read_text(encoding="utf-8")
reader=Path("src/activities/reader/EpubReaderActivity.cpp").read_text(encoding="utf-8")
scale="0, 550, 520, 480, 430, 370, 300, 220"
if scale not in ui: raise SystemExit("CPHUN-151 Text Settings scale mismatch")
if scale not in reader: raise SystemExit("CPHUN-151 hardware action scale mismatch")
for v in ("550","520","480","430","370","300","220"):
    if f"letterSpacingLimitPercent != {v}" not in cpp:
        raise SystemExit(f"CPHUN-151 loader does not accept {v}")

print("CPHUN-151 persistence audit passed")
