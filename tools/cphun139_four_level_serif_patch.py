from pathlib import Path
import re

def change(path, old, new, description):
    p = Path(path)
    text = p.read_text(encoding="utf-8")
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"CPHUN-149 {description}: expected 1 anchor, got {count}")
    p.write_text(text.replace(old, new, 1), encoding="utf-8")

def regex_change(path, pattern, replacement, description):
    p = Path(path)
    text = p.read_text(encoding="utf-8")
    text, n = re.subn(pattern, replacement, text, count=1, flags=re.S)
    if n != 1:
        raise SystemExit(f"CPHUN-149 {description}: expected 1 anchor, got {n}")
    p.write_text(text, encoding="utf-8")

ui = "src/activities/settings/TextSettingsActivity.cpp"
cpp = "src/CrossPointSettings.cpp"
header = "lib/Epub/Epub/LetterSpacingOptimization.h"

# Four correction levels. Keep the old physical correction thresholds, not a
# falsely linear interpolation: 10%->550, 40%->460, 70%->280.
s = Path(ui).read_text(encoding="utf-8")
start = s.index("int letterSpacingUiIndex(")
end = s.index("\n}\n", start) + 3
helper = """
constexpr uint16_t CPHUN139_CORRECTION_VALUES[] = {0, 550, 460, 280};

int correctionLevelIndex(const uint16_t storedValue) {
  if (storedValue == 0) return 0;
  const int oldIndex = letterSpacingUiIndex(storedValue);
  if (oldIndex <= 2) return 1;
  if (oldIndex <= 5) return 2;
  return 3;
}

const char* correctionLevelLabel(const int index) {
  const bool hu = I18N.getLanguage() == Language::HU;
  constexpr const char* huLabels[] = {"KI", "Gyenge", "Közepes", "Erős"};
  constexpr const char* enLabels[] = {"Off", "Weak", "Medium", "Strong"};
  return (hu ? huLabels : enLabels)[std::clamp(index, 0, 3)];
}

const char* optimizationThresholdLabel(const uint8_t threshold) {
  if (threshold == 0) return correctionLevelLabel(0);
  if (threshold == 50) return correctionLevelLabel(1);
  if (threshold == 60) return correctionLevelLabel(2);
  return correctionLevelLabel(3);
}
"""
s = s[:end] + helper + s[end:]
Path(ui).write_text(s, encoding="utf-8")

change(ui,
       'const char* options[] = {tr(STR_STATE_OFF), "10%", "20%", "30%", "40%", "50%", "60%", "70%"};',
       'const char* options[] = {correctionLevelLabel(0), correctionLevelLabel(1),\n'
       '                              correctionLevelLabel(2), correctionLevelLabel(3)};',
       "four correction menu labels")
change(ui, "const int cur = letterSpacingUiIndex(v);",
       "const int cur = correctionLevelIndex(v);", "four correction current value")
change(ui, "options, 8, cur, [](int idx) {",
       "options, 4, cur, [](int idx) {", "four correction menu entries")
change(ui,
       "SETTINGS.letterSpacingLimitPercent = LETTER_SPACING_THRESHOLDS[std::clamp(idx, 0, 7)];",
       "SETTINGS.letterSpacingLimitPercent = CPHUN139_CORRECTION_VALUES[std::clamp(idx, 0, 3)];",
       "four correction stored values")
change(ui,
       "const int displayPercent = letterSpacingUiIndex(v) * 10;\n      return std::to_string(displayPercent) + \"%\";",
       "return correctionLevelLabel(correctionLevelIndex(v));",
       "four correction value labels")

# The existing explicit optimizer ON/OFF switch is retained, independently of
# the new threshold KI state. KI disables only pair-score filtering.
change(ui, 'const char* options[] = {"50", "55", "60", "65", "70", "75"};',
       'const char* options[] = {correctionLevelLabel(0), correctionLevelLabel(1),\n'
       '                              correctionLevelLabel(2), correctionLevelLabel(3)};',
       "four optimization threshold menu labels")
change(ui,
       "const int cur = std::clamp<int>((SETTINGS.letterSpacingOptimizationThreshold - 50) / 5, 0, 5);",
       "const uint8_t t = SETTINGS.letterSpacingOptimizationThreshold;\n"
       "      const int cur = t == 0 ? 0 : (t <= 55 ? 1 : (t <= 65 ? 2 : 3));",
       "optimization threshold current value")
change(ui,
       "options, 6, cur, [](int idx) {",
       "options, 4, cur, [](int idx) {",
       "four optimization threshold menu entries")
change(ui,
       "SETTINGS.letterSpacingOptimizationThreshold =\n"
       "                static_cast<uint8_t>(50 + std::clamp(idx, 0, 5) * 5);",
       "constexpr uint8_t values[] = {0, 50, 60, 70};\n"
       "            SETTINGS.letterSpacingOptimizationThreshold = values[std::clamp(idx, 0, 3)];",
       "four optimization threshold stored values")
change(ui,
       "return std::to_string(SETTINGS.letterSpacingOptimizationThreshold);",
       "return optimizationThresholdLabel(SETTINGS.letterSpacingOptimizationThreshold);",
       "optimization threshold value labels")

# Migrate legacy menu values and preserve settings on restart/sleep.
change(cpp,
       "  minimumSpacePercent = doc[\"minimumSpacePercent\"] | (uint8_t)100;",
       """  // Migrate previously saved 10..70% menu choices to 0/10/40/70.
  if (letterSpacingLimitPercent != 0 && letterSpacingLimitPercent != 550 &&
      letterSpacingLimitPercent != 460 && letterSpacingLimitPercent != 280) {
    constexpr uint16_t values[] = {550, 460, 280};
    uint16_t best = values[0];
    uint16_t diff = letterSpacingLimitPercent > best
                        ? letterSpacingLimitPercent - best : best - letterSpacingLimitPercent;
    for (uint16_t value : values) {
      const uint16_t d = letterSpacingLimitPercent > value
                             ? letterSpacingLimitPercent - value : value - letterSpacingLimitPercent;
      if (d < diff) { diff = d; best = value; }
    }
    letterSpacingLimitPercent = best;
    needsResave = true;
  }
  if (letterSpacingOptimizationThreshold != 0 &&
      letterSpacingOptimizationThreshold != 50 &&
      letterSpacingOptimizationThreshold != 60 &&
      letterSpacingOptimizationThreshold != 70) {
    const uint8_t previous = letterSpacingOptimizationThreshold;
    letterSpacingOptimizationThreshold = previous <= 55 ? 50 : (previous <= 65 ? 60 : 70);
    needsResave = true;
  }
  minimumSpacePercent = doc["minimumSpacePercent"] | (uint8_t)100;""",
       "legacy migration")
change(cpp,
       "if (letterSpacingOptimizationThreshold < 50 || letterSpacingOptimizationThreshold > 75 ||\n"
       "      letterSpacingOptimizationThreshold % 5 != 0) {",
       "if (letterSpacingOptimizationThreshold > 75 ||\n"
       "      (letterSpacingOptimizationThreshold != 0 && letterSpacingOptimizationThreshold < 50) ||\n"
       "      (letterSpacingOptimizationThreshold != 0 && letterSpacingOptimizationThreshold % 5 != 0)) {",
       "accept threshold zero")

# Known Serif names can use the transferred Bitter profile. Unknown/custom font
# names remain disabled, preventing accidental Sans optimization. Noto Serif 16
# continues to route through its own independently measured pair table.
change(cpp,
       """  const bool isNotoSerif16 =
      fontPointSize == 16 && sdFontFamilyName[0] == '\\0' && fontFamily == NOTOSERIF;
  const uint8_t optimizationThresholdCode =
      letterSpacingLimitPercent > 0 && letterSpacingOptimization &&
              (isBitterExperimentalSize || isNotoSerif16)
          ? static_cast<uint8_t>((letterSpacingOptimizationThreshold - 45u) / 5u)
          : 0;""",
       """  const bool isBuiltinSerif =
      sdFontFamilyName[0] == '\\0' && fontFamily == NOTOSERIF;
  const bool isNotoSerif16 = isBuiltinSerif && fontPointSize == 16;
  const bool knownSdSerif =
      sdFontFamilyName[0] != '\\0' &&
      (strstr(sdFontFamilyName, "Serif") || strstr(sdFontFamilyName, "Bitter") ||
       strstr(sdFontFamilyName, "Bookerly") || strstr(sdFontFamilyName, "Georgia") ||
       strstr(sdFontFamilyName, "Garamond") || strstr(sdFontFamilyName, "Palatino") ||
       strstr(sdFontFamilyName, "Literata") || strstr(sdFontFamilyName, "Merriweather") ||
       strstr(sdFontFamilyName, "Cambria") || strstr(sdFontFamilyName, "Times")) &&
      !strstr(sdFontFamilyName, "Sans");
  const bool supportedSerifSize =
      fontPointSize == 12 || fontPointSize == 14 ||
      fontPointSize == 16 || fontPointSize == 18;
  const bool useSerifProfile =
      supportedSerifSize && (isBuiltinSerif || knownSdSerif || isBitterExperimentalSize);
  const uint8_t optimizationThresholdCode =
      letterSpacingLimitPercent > 0 && letterSpacingOptimization && useSerifProfile
          ? (letterSpacingOptimizationThreshold == 0
                 ? 7u
                 : static_cast<uint8_t>((letterSpacingOptimizationThreshold - 45u) / 5u))
          : 0;""",
       "Serif eligibility and threshold KI encoding")

# Preserve old 1..6 bitfield codes; unused code 7 represents score-unfiltered
# optimization. Packed 0 still means optimization disabled.
change(header,
       "return code >= 1 && code <= 6 ? static_cast<uint8_t>(45u + code * 5u) : 60u;",
       "return code == 7 ? 0u : (code >= 1 && code <= 6\n"
       "                            ? static_cast<uint8_t>(45u + code * 5u) : 60u);",
       "score threshold KI decoding")
change(header,
       "if (thresholdCode < 1 || thresholdCode > 6 || budgetPx == 0) return 0;",
       "if (thresholdCode < 1 || thresholdCode > 7 || budgetPx == 0) return 0;",
       "score threshold KI packing")
change(header,
       "return code >= 1 && code <= 6;",
       "return code >= 1 && code <= 7;",
       "score threshold KI detection")
change(header,
       """    return BitterSpacingScores::scoreForPair(left, right, pointSize) >= threshold;""",
       """    const uint8_t score = BitterSpacingScores::scoreForPair(left, right, pointSize);
    return score > 0 && (threshold == 0 || score >= threshold);""",
       "Bitter score-unfiltered mode")

# The 60-point Noto Serif 16 table remains the measured reference. Other
# thresholds use the transferred Bitter score as an explicit experiment while
# respecting the 60-point table's ordered inclusion.
change(header,
       "  return lo < count && NOTOSERIF_16_OPTIMIZABLE_PAIRS[lo] == key;",
       """  const bool notoMeasured60 = lo < count && NOTOSERIF_16_OPTIMIZABLE_PAIRS[lo] == key;
  if (threshold == 60) return notoMeasured60;
  const uint8_t proxy = BitterSpacingScores::scoreForPair(left, right, pointSize);
  if (threshold == 0) return proxy > 0;
  if (threshold < 60) return notoMeasured60 || proxy >= threshold;
  return notoMeasured60 && proxy >= threshold;""",
       "Noto Serif measured profile plus score transfer")

change("src/CPHUNBuildId.h",
       '#define CPHUN_BUILD_ID "CPHUN-260921-148-EXP"',
       '#define CPHUN_BUILD_ID "CPHUN-260925-149-EXP"',
       "new build identifier")
print("CPHUN-149: four-level UI, score-unfiltered KI, Serif transfer applied.")
