from pathlib import Path

p = Path("src/activities/settings/TextSettingsActivity.cpp")
s = p.read_text(encoding="utf-8")

old = '''  const int tabTop = afterHeader + previewHeight;
  const int captionHeight = renderer.getTextHeight(UI_10_FONT_ID) + metrics_.verticalSpacing;
  screen.setContentMargin(
      fui::Insets{static_cast<int16_t>(tabTop), 0, static_cast<int16_t>(bottomReserved + captionHeight), 0});
'''

new = '''  const int tabTop = afterHeader + previewHeight;
  const int captionHeight = renderer.getTextHeight(UI_10_FONT_ID) + metrics_.verticalSpacing;

  // The Layout tab never renders the "not in preview" caption. Let its list
  // extend all the way down to the top edge of the physical button-hint band.
  // Other tabs retain the legacy caption reserve.
  const int contentBottomReserve =
      tab_ == Tab::Layout ? metrics_.buttonHintsHeight : bottomReserved + captionHeight;
  screen.setContentMargin(
      fui::Insets{static_cast<int16_t>(tabTop), 0, static_cast<int16_t>(contentBottomReserve), 0});
'''

if s.count(old) != 1:
    raise SystemExit(f"CPHUN-138 list-height anchor count={s.count(old)}")

p.write_text(s.replace(old, new, 1), encoding="utf-8")
print("CPHUN-138 applied: Layout list extends to the button-hint band")
