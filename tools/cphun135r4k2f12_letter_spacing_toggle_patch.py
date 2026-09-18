from pathlib import Path

# CPHUN-135r4k2f12
# Finalize letter-spacing optimization as OFF/ON.
# ON always maps to the existing 100% optimization profile (profile 4).
# Any legacy non-zero stored profile migrates to ON/100%.

def replace_once(path, old, new):
    p = Path(path)
    s = p.read_text(encoding="utf-8")
    count = s.count(old)
    if count != 1:
        raise SystemExit(f"R4K2F12: {path}: expected one match, found {count}: {old[:160]!r}")
    p.write_text(s.replace(old, new, 1), encoding="utf-8")

# Normalize persisted legacy profiles (1..4) to the final boolean-like representation:
# 0 = OFF, 4 = ON/100%.
replace_once(
    "src/CrossPointSettings.cpp",
    '''  letterSpacingOptimization =
      std::min<uint8_t>(doc["letterSpacingOptimization"] | (uint8_t)0, 4);''',
    '''  letterSpacingOptimization =
      (doc["letterSpacingOptimization"] | (uint8_t)0) ? 4 : 0;''',
)

# Keep the existing compact config transport, but force every enabled state to profile 4.
replace_once(
    "src/CrossPointSettings.cpp",
    '''  const uint8_t bitter16OptimizationProfile =
      letterSpacingLimitPercent > 0 && (isBitter16 || isNotoSerif16)
          ? std::min<uint8_t>(letterSpacingOptimization, 4)
          : 0;''',
    '''  const uint8_t bitter16OptimizationProfile =
      letterSpacingLimitPercent > 0 && (isBitter16 || isNotoSerif16) && letterSpacingOptimization
          ? 4
          : 0;''',
)

# Update setting documentation to match the final UI semantics.
replace_once(
    "src/CrossPointSettings.h",
    '''  // 0=off, 1=25%, 2=50%, 3=75%, 4=100% (Bitter 16 pt pilot).
  uint8_t letterSpacingOptimization = 0;''',
    '''  // Final UI semantics: 0=off, 4=on (fixed 100% optimization profile).
  // Legacy stored values 1..3 are normalized to 4 when settings are loaded.
  uint8_t letterSpacingOptimization = 0;''',
)

# Replace the five-choice percentage picker with a direct toggle.
replace_once(
    "src/activities/settings/TextSettingsActivity.cpp",
    '''    case LayoutRow::LetterSpacingOptimization: {
      if (SETTINGS.letterSpacingLimitPercent == 0) {
        requestUpdate();
        break;
      }
      const char* options[] = {tr(STR_STATE_OFF), "25%", "50%", "75%", "100%"};
      const int cur = std::clamp<int>(SETTINGS.letterSpacingOptimization, 0, 4);
      optionPopup_.show(
          I18N.getLanguage() == Language::HU ? "Betűköz optimalizálás" : "Letter spacing optimization",
          options, 5, cur, [](int idx) {
            SETTINGS.letterSpacingOptimization = static_cast<uint8_t>(std::clamp(idx, 0, 4));
            SETTINGS.saveToFile();
          });
      requestUpdate();
      break;
    }''',
    '''    case LayoutRow::LetterSpacingOptimization:
      if (SETTINGS.letterSpacingLimitPercent == 0) {
        requestUpdate();
        break;
      }
      SETTINGS.letterSpacingOptimization = SETTINGS.letterSpacingOptimization ? 0 : 4;
      SETTINGS.saveToFile();
      requestUpdate();
      break;''',
)

# Display only OFF/ON, never a percentage.
replace_once(
    "src/activities/settings/TextSettingsActivity.cpp",
    '''    case LayoutRow::LetterSpacingOptimization: {
      constexpr const char* labels[] = {"", "25%", "50%", "75%", "100%"};
      const uint8_t profile = std::min<uint8_t>(SETTINGS.letterSpacingOptimization, 4);
      return profile == 0 ? tr(STR_STATE_OFF) : labels[profile];
    }''',
    '''    case LayoutRow::LetterSpacingOptimization:
      return SETTINGS.letterSpacingOptimization ? tr(STR_STATE_ON) : tr(STR_STATE_OFF);''',
)

print("CPHUN-135r4k2f12 applied: Betűköz optimalizálás is now OFF/ON; ON=fixed 100%")
