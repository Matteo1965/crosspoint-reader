from pathlib import Path


def replace_once(path: str, old: str, new: str) -> None:
    p = Path(path)
    text = p.read_text(encoding="utf-8")
    if text.count(old) != 1:
        raise SystemExit(f"Expected exactly one match in {path}, found {text.count(old)}")
    p.write_text(text.replace(old, new, 1), encoding="utf-8")


replace_once(
    "src/activities/settings/TextSettingsActivity.cpp",
    '''      // CPHUN-260828-28: gentler production scale. Higher UI percentage still
      // means more lines are eligible, but thresholds now span 360% down to 180%.
      const char* options[] = {tr(STR_STATE_OFF), "10%", "20%", "30%", "40%", "50%", "60%", "70%"};
      int cur = 0;
      if (SETTINGS.letterSpacingLimitPercent >= 180 && SETTINGS.letterSpacingLimitPercent <= 360 &&
          SETTINGS.letterSpacingLimitPercent % 30 == 0) {
        cur = 1 + (360 - SETTINGS.letterSpacingLimitPercent) / 30;
      }
      optionPopup_.show(I18N.getLanguage() == Language::HU ? "Betűköz korrekció" : "Letter spacing correction",
                        options, 8, cur, [](int idx) {
                          SETTINGS.letterSpacingLimitPercent = idx == 0 ? 0 : static_cast<uint16_t>(390 - idx * 30);
                          SETTINGS.saveToFile();
                        });''',
    '''      // CPHUN-260828-29: widen the low-strength range for font-sensitive faces.
      // Higher UI percentage means stronger/more frequent correction; the internal
      // activation threshold therefore decreases monotonically from 600% to 180%.
      const char* options[] = {tr(STR_STATE_OFF), "10%", "20%", "30%", "40%", "50%", "60%", "70%"};
      constexpr uint16_t thresholds[] = {0, 600, 500, 420, 360, 300, 240, 180};
      int cur = 0;
      for (int i = 1; i < 8; ++i) {
        if (SETTINGS.letterSpacingLimitPercent == thresholds[i]) {
          cur = i;
          break;
        }
      }
      optionPopup_.show(I18N.getLanguage() == Language::HU ? "Betűköz korrekció" : "Letter spacing correction",
                        options, 8, cur, [](int idx) {
                          constexpr uint16_t thresholds[] = {0, 600, 500, 420, 360, 300, 240, 180};
                          SETTINGS.letterSpacingLimitPercent = thresholds[idx];
                          SETTINGS.saveToFile();
                        });''',
)

replace_once(
    "src/activities/settings/TextSettingsActivity.cpp",
    '''    case LayoutRow::LetterSpacingCorrection:
      if (SETTINGS.letterSpacingLimitPercent >= 180 && SETTINGS.letterSpacingLimitPercent <= 360 &&
          SETTINGS.letterSpacingLimitPercent % 30 == 0) {
        return std::to_string((390 - SETTINGS.letterSpacingLimitPercent) / 3) + "%";
      }
      return tr(STR_STATE_OFF);''',
    '''    case LayoutRow::LetterSpacingCorrection: {
      constexpr uint16_t thresholds[] = {600, 500, 420, 360, 300, 240, 180};
      for (int i = 0; i < 7; ++i) {
        if (SETTINGS.letterSpacingLimitPercent == thresholds[i]) return std::to_string((i + 1) * 10) + "%";
      }
      return tr(STR_STATE_OFF);
    }''',
)

replace_once(
    "src/CrossPointSettings.cpp",
    '''  if (letterSpacingLimitPercent != 0 &&
      (letterSpacingLimitPercent < 180 || letterSpacingLimitPercent > 360 || letterSpacingLimitPercent % 30 != 0)) {
    letterSpacingLimitPercent = 0;
    needsResave = true;
  }''',
    '''  if (letterSpacingLimitPercent != 0 && letterSpacingLimitPercent != 180 && letterSpacingLimitPercent != 240 &&
      letterSpacingLimitPercent != 300 && letterSpacingLimitPercent != 360 && letterSpacingLimitPercent != 420 &&
      letterSpacingLimitPercent != 500 && letterSpacingLimitPercent != 600) {
    letterSpacingLimitPercent = 0;
    needsResave = true;
  }''',
)

print("CPHUN-260828-29 tracking scale patch applied")
