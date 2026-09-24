#!/usr/bin/env python3
"""CPHUN-152: fail CI if settings UI, JSON and validators diverge."""
from pathlib import Path
import re

root = Path(__file__).resolve().parent.parent
def read(path):
    return (root / path).read_text(encoding="utf-8")
header = read("src/CrossPointSettings.h")
cpp = read("src/CrossPointSettings.cpp")
ui = read("src/activities/settings/TextSettingsActivity.cpp")
generic = read("src/SettingsListBase.h")
reader = read("src/activities/reader/EpubReaderActivity.cpp")

def check(ok, reason):
    if not ok:
        raise SystemExit("CPHUN-152 persistence audit FAILED: " + reason)

# Check the actual active 10..70% UI formula, not values from an old patch.
m = re.search(r'const char\* options\[\] = \{tr\(STR_STATE_OFF\), "10%", "20%", "30%", "40%", "50%", "60%", "70%"\}', ui)
check(m is not None, "correction UI choices changed; update the audit")
check("static_cast<uint16_t>(260 - idx * 20)" in ui, "correction picker encoding changed")
check("(260 - std::clamp<int>(v, 120, 240)) / 2" in ui, "correction display encoding changed")
expected = [0] + [260 - i * 20 for i in range(1, 8)]
check(expected == [0, 240, 220, 200, 180, 160, 140, 120], "unexpected UI scale")
validator = re.search(r'if \(letterSpacingLimitPercent != 0 &&.*?\) \{\s*letterSpacingLimitPercent = 0;', cpp, re.S)
check(validator is not None, "correction validator not found")
allowed = {int(v) for v in re.findall(r'letterSpacingLimitPercent != (\d+)', validator.group())}
check(allowed == set(expected), f"UI/loader scale mismatch: {allowed} vs {set(expected)}")
check('doc["letterSpacingLimitPercent"] = letterSpacingLimitPercent;' in cpp and
      'letterSpacingLimitPercent = doc["letterSpacingLimitPercent"] | (uint16_t)0;' in cpp,
      "correction save/load pair missing")
for i in range(8):
    value = 0 if i == 0 else 260 - i * 20
    assert value in allowed
    assert (0 if value == 0 else (260 - value) // 2) == i * 10

# The core generic settings list serializes through the same getSettingsList()
# on both paths. Ensure its declared value fields still exist.
to_json = cpp.split("void CrossPointSettings::toJson(", 1)[1].split("bool CrossPointSettings::fromJson(", 1)[0]
from_json = cpp.split("bool CrossPointSettings::fromJson(", 1)[1].split("ReaderRenderSpec", 1)[0]
check("for (const auto& info : getSettingsList())" in to_json, "generic save loop missing")
check("for (const auto& info : getSettingsList())" in from_json, "generic load loop missing")
generic_fields = set(re.findall(r'&CrossPointSettings::(\w+)', generic))
for field in generic_fields:
    check(re.search(r'\b' + re.escape(field) + r'\b', header) is not None,
          "generic field missing from settings struct: " + field)

# Manually serialized fields must have a corresponding explicit load.
manual = (
 "frontButtonBack", "frontButtonConfirm", "frontButtonLeft", "frontButtonRight",
 "fontFamily", "fontSize", "hangingPunctuation", "shortHyphen",
 "fixedDialogueSpacing", "letterSpacingLimitPercent", "softHyphenEnabled",
 "minimumSpacePercent", "extraParagraphSpacingEnabled", "sdFontFamilyName",
 "dictionaryName", "language", "keyboardLayouts"
)
for field in manual:
    check('doc["' + field + '"]' in to_json, "manual save missing: " + field)
    check('doc["' + field + '"]' in from_json, "manual load missing: " + field)

for field in ("hangingPunctuation", "shortHyphen", "fixedDialogueSpacing",
              "softHyphenEnabled", "minimumSpacePercent", "extraParagraphSpacingEnabled"):
    check('SETTINGS.' + field in ui, "text-settings UI disconnected: " + field)
check("SETTINGS.saveToFile();" in ui, "UI no longer saves edited settings")
check("SETTINGS.saveToFile();" in reader, "reader actions no longer save settings")
check("minimumSpacePercent < 50 || minimumSpacePercent > 100 || minimumSpacePercent % 10 != 0" in cpp,
      "minimum-space validation changed")
check("extraParagraphSpacing != 25 && extraParagraphSpacing != 50" in cpp,
      "paragraph-spacing validation changed")
print(f"CPHUN-152 persistence audit passed: {len(generic_fields)} generic fields, "
      f"{len(manual)} manual fields and all 8 spacing correction choices.")
