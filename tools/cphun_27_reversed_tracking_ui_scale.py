from pathlib import Path

path = Path('src/activities/settings/TextSettingsActivity.cpp')
s = path.read_text(encoding='utf-8')

old_picker = '''    case LayoutRow::LetterSpacingCorrection: {
      const char* options[] = {tr(STR_STATE_OFF), "120%", "140%", "160%", "180%", "200%", "220%", "240%"};
      int cur = 0;
      if (SETTINGS.letterSpacingLimitPercent >= 120 && SETTINGS.letterSpacingLimitPercent <= 240) {
        cur = 1 + (SETTINGS.letterSpacingLimitPercent - 120) / 20;
      }
      optionPopup_.show(I18N.getLanguage() == Language::HU ? "Betűköz korrekció" : "Letter spacing correction",
                        options, 8, cur, [](int idx) {
                          SETTINGS.letterSpacingLimitPercent = idx == 0 ? 0 : static_cast<uint8_t>(100 + idx * 20);
                          SETTINGS.saveToFile();
                        });
      requestUpdate();
      break;
    }
'''

new_picker = '''    case LayoutRow::LetterSpacingCorrection: {
      // CPHUN-260827-27: expose correction strength in the intuitive direction:
      // higher UI percentage means more lines are eligible for +1 px tracking.
      // Internally we keep the proven CPHUN-26 activation thresholds unchanged.
      const char* options[] = {tr(STR_STATE_OFF), "10%", "20%", "30%", "40%", "50%", "60%", "70%"};
      int cur = 0;
      if (SETTINGS.letterSpacingLimitPercent >= 120 && SETTINGS.letterSpacingLimitPercent <= 240) {
        cur = 1 + (240 - SETTINGS.letterSpacingLimitPercent) / 20;
      }
      optionPopup_.show(I18N.getLanguage() == Language::HU ? "Betűköz korrekció" : "Letter spacing correction",
                        options, 8, cur, [](int idx) {
                          SETTINGS.letterSpacingLimitPercent = idx == 0 ? 0 : static_cast<uint8_t>(260 - idx * 20);
                          SETTINGS.saveToFile();
                        });
      requestUpdate();
      break;
    }
'''

old_value = '''    case LayoutRow::LetterSpacingCorrection:
      return SETTINGS.letterSpacingLimitPercent ? std::to_string(SETTINGS.letterSpacingLimitPercent) + "%"
                                                : tr(STR_STATE_OFF);
'''

new_value = '''    case LayoutRow::LetterSpacingCorrection:
      if (SETTINGS.letterSpacingLimitPercent >= 120 && SETTINGS.letterSpacingLimitPercent <= 240) {
        return std::to_string((260 - SETTINGS.letterSpacingLimitPercent) / 2) + "%";
      }
      return tr(STR_STATE_OFF);
'''

if s.count(old_picker) != 1:
    raise SystemExit(f'Expected exactly one old tracking picker block, found {s.count(old_picker)}')
if s.count(old_value) != 1:
    raise SystemExit(f'Expected exactly one old tracking value block, found {s.count(old_value)}')

s = s.replace(old_picker, new_picker, 1)
s = s.replace(old_value, new_value, 1)
path.write_text(s, encoding='utf-8')
print('Applied CPHUN-260827-27 reversed tracking UI scale')
