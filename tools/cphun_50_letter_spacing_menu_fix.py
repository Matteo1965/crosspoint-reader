from pathlib import Path

p = Path('src/activities/settings/TextSettingsActivity.cpp')
s = p.read_text()

# Restore the LetterSpacingCorrection picker that was lost when the Layout enum
# gained the row but confirmLayoutRow()/layoutValueText() were not extended.
anchor = '''    case LayoutRow::MinimumSpace: {
      const char* options[] = {"50%", "60%", "70%", "80%", "90%", "100%"};'''
if anchor not in s:
    raise SystemExit('MinimumSpace anchor not found')

letter_case = '''    case LayoutRow::LetterSpacingCorrection: {
      const char* options[] = {tr(STR_STATE_OFF), "10%", "20%", "30%", "40%", "50%", "60%", "70%"};
      const uint16_t v = SETTINGS.letterSpacingLimitPercent;
      const int cur = v == 0 ? 0 : std::clamp<int>((260 - std::clamp<int>(v, 120, 240)) / 20, 1, 7);
      optionPopup_.show(I18N.getLanguage() == Language::HU ? "Betűköz korrekció" : "Letter spacing correction",
                        options, 8, cur, [](int idx) {
                          SETTINGS.letterSpacingLimitPercent = idx == 0 ? 0 : static_cast<uint16_t>(260 - idx * 20);
                          SETTINGS.saveToFile();
                        });
      requestUpdate();
      break;
    }
'''

if 'case LayoutRow::LetterSpacingCorrection: {' not in s:
    # Put it immediately after MinimumSpace's complete case, before ShortHyphen.
    marker = '''    case LayoutRow::ShortHyphen:
'''
    if marker not in s:
        raise SystemExit('ShortHyphen marker not found')
    s = s.replace(marker, letter_case + marker, 1)

value_anchor = '''    case LayoutRow::ScreenMargin:
      return std::to_string(SETTINGS.screenMargin);
'''
value_case = '''    case LayoutRow::LetterSpacingCorrection: {
      const uint16_t v = SETTINGS.letterSpacingLimitPercent;
      if (v == 0) return tr(STR_STATE_OFF);
      const int displayPercent = (260 - std::clamp<int>(v, 120, 240)) / 2;
      return std::to_string(displayPercent) + "%";
    }
'''
if value_case not in s:
    if value_anchor not in s:
        raise SystemExit('layoutValueText ScreenMargin anchor not found')
    s = s.replace(value_anchor, value_case + value_anchor, 1)

# The Layout/Rendez. tab now has nine rows. Tighten only this tab; other tabs
# retain the active theme's normal row geometry.
spacing_anchor = '''  props.valueInset = 8;               // air between the value and the row edge
'''
spacing_patch = '''  props.valueInset = 8;               // air between the value and the row edge
  if (tab_ == Tab::Layout) {
    props.rowHeight = 26;
    props.rowGap = 0;
  }
'''
if 'props.rowHeight = 26;' not in s:
    if spacing_anchor not in s:
        raise SystemExit('ListProps valueInset anchor not found')
    s = s.replace(spacing_anchor, spacing_patch, 1)

p.write_text(s)
