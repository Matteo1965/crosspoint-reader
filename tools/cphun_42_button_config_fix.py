from pathlib import Path

# CPHUN-42: finalise the configurable bottom-button UI and gesture routing.

# 1) Bottom-button mapping UI: larger text and the user-tested X positions.
p = Path('src/activities/settings/ButtonFunctionsActivity.cpp')
t = p.read_text(encoding='utf-8')
t = t.replace('constexpr int kButtonX = 125;', 'constexpr int kButtonX = 135;')
t = t.replace('constexpr int kActionX = 235;', 'constexpr int kActionX = 255;')

# Restrict the picker to the approved 12 reader actions. This also keeps the
# modal safely below OptionPopup's 16-row limit.
actions_start = t.index('constexpr ReaderAction ACTIONS[] = {')
actions_end = t.index('};', actions_start) + 2
actions = '''constexpr ReaderAction ACTIONS[] = {
    ReaderAction::None,
    ReaderAction::PreviousPage,
    ReaderAction::NextPage,
    ReaderAction::OpenReaderMenu,
    ReaderAction::OpenTextSettings,
    ReaderAction::OpenLayoutMenu,
    ReaderAction::GoHome,
    ReaderAction::ScreenMarginDown,
    ReaderAction::ScreenMarginUp,
    ReaderAction::ToggleNightMode,
    ReaderAction::ToggleHyphenation,
    ReaderAction::ToggleSoftHyphen,
};'''
t = t[:actions_start] + actions + t[actions_end:]

# User-facing labels for the approved action set.
replacements = {
    'case ReaderAction::OpenReaderMenu: return hu ? "Olvasómenü" : "Reader menu";':
        'case ReaderAction::OpenReaderMenu: return hu ? "Olvasó menü" : "Reader menu";',
    'case ReaderAction::OpenLayoutMenu: return hu ? "Rendez." : "Layout";':
        'case ReaderAction::OpenLayoutMenu: return hu ? "Képernyőelrendezés" : "Screen layout";',
    'case ReaderAction::GoHome: return hu ? "Főoldal" : "Home";':
        'case ReaderAction::GoHome: return hu ? "Kezdőképernyő" : "Home";',
    'case ReaderAction::ScreenMarginUp: return hu ? "Margó +" : "Margin +";':
        'case ReaderAction::ScreenMarginUp: return hu ? "Margó növelése" : "Increase margin";',
    'case ReaderAction::ScreenMarginDown: return hu ? "Margó −" : "Margin -";':
        'case ReaderAction::ScreenMarginDown: return hu ? "Margó csökkentése" : "Decrease margin";',
    'case ReaderAction::ToggleNightMode: return hu ? "Éjszakai mód" : "Night mode";':
        'case ReaderAction::ToggleNightMode: return hu ? "Éjszakai mód KI/BE" : "Night mode on/off";',
    'case ReaderAction::ToggleHyphenation: return hu ? "Elválasztás" : "Hyphenation";':
        'case ReaderAction::ToggleHyphenation: return hu ? "Elválasztás KI/BE" : "Hyphenation on/off";',
    'case ReaderAction::ToggleSoftHyphen: return hu ? "Kiterjesztett elválasztás" : "Extended hyphenation";':
        'case ReaderAction::ToggleSoftHyphen: return hu ? "Kiterjesztett elválasztás KI/BE" : "Extended hyphenation on/off";',
}
for old, new in replacements.items():
    if old in t:
        t = t.replace(old, new, 1)

# Draw the three custom columns with UI_12_FONT_ID. Keep the vertical centring
# formula, but recalculate it from the actual 12pt font height.
t = t.replace('const int textHeight = renderer.getTextHeight(SMALL_FONT_ID);',
              'const int textHeight = renderer.getTextHeight(UI_12_FONT_ID);', 1)
t = t.replace('renderer.drawText(SMALL_FONT_ID, gestureX, textY, gesture, black);',
              'renderer.drawText(UI_12_FONT_ID, gestureX, textY, gesture, black);', 1)
t = t.replace('renderer.drawText(SMALL_FONT_ID, buttonX, textY, labels_[row].c_str(), black);',
              'renderer.drawText(UI_12_FONT_ID, buttonX, textY, labels_[row].c_str(), black);', 1)
t = t.replace('renderer.drawText(SMALL_FONT_ID, actionX, textY, values_[row].c_str(), black);',
              'renderer.drawText(UI_12_FONT_ID, actionX, textY, values_[row].c_str(), black);', 1)

# ButtonFunctionsActivity previously handled popup input but never drew the popup.
# Render it after the page/footer so the 12-action picker is visible and usable.
old = '''  UiListActivity::drawFooter();
}'''
new = '''  UiListActivity::drawFooter();
  if (optionPopup_.isActive()) optionPopup_.render(renderer);
}'''
if old not in t:
    raise SystemExit('CPHUN-42 popup-render anchor missing')
t = t.replace(old, new, 1)
p.write_text(t, encoding='utf-8')

# 2) Gesture routing: CPHUN-41 accidentally kept reading the Double slot from
# the generic Single/Double/Hold dispatcher. Read the actual gesture instead.
p = Path('src/activities/reader/EpubReaderActivity.cpp')
r = p.read_text(encoding='utf-8')
old = 'const ReaderAction configured = READER_BUTTONS.get(physical, ReaderButtonGesture::Double);'
new = 'const ReaderAction configured = READER_BUTTONS.get(physical, gesture);'
if old not in r:
    raise SystemExit('CPHUN-42 fixed-Double profile lookup anchor missing')
r = r.replace(old, new, 1)

# The CPHUN-39 compatibility shortcuts are valid only for a real double click.
# None on Single/Hold must fall through to the proven legacy input path.
old = '''    if (configured == ReaderAction::None) {
      // Compatibility fallback: preserve the four device-confirmed CPHUN-36 v2
      // double-click shortcuts until the user assigns an explicit 2x mapping.'''
new = '''    if (configured == ReaderAction::None) {
      if (gesture != ReaderButtonGesture::Double) return false;
      // Compatibility fallback: preserve the four device-confirmed CPHUN-36 v2
      // double-click shortcuts until the user assigns an explicit 2x mapping.'''
if old not in r:
    raise SystemExit('CPHUN-42 double-only fallback anchor missing')
r = r.replace(old, new, 1)
p.write_text(r, encoding='utf-8')

# Static verification.
ui = Path('src/activities/settings/ButtonFunctionsActivity.cpp').read_text(encoding='utf-8')
for s in [
    'constexpr int kGestureX = 40;',
    'constexpr int kButtonX = 135;',
    'constexpr int kActionX = 255;',
    'renderer.getTextHeight(UI_12_FONT_ID)',
    'renderer.drawText(UI_12_FONT_ID, gestureX',
    'renderer.drawText(UI_12_FONT_ID, buttonX',
    'renderer.drawText(UI_12_FONT_ID, actionX',
    'optionPopup_.isActive()',
    'optionPopup_.render(renderer)',
    'Kiterjesztett elválasztás KI/BE',
]:
    assert s in ui, s

approved = [
    'ReaderAction::None', 'ReaderAction::PreviousPage', 'ReaderAction::NextPage',
    'ReaderAction::OpenReaderMenu', 'ReaderAction::OpenTextSettings', 'ReaderAction::OpenLayoutMenu',
    'ReaderAction::GoHome', 'ReaderAction::ScreenMarginDown', 'ReaderAction::ScreenMarginUp',
    'ReaderAction::ToggleNightMode', 'ReaderAction::ToggleHyphenation', 'ReaderAction::ToggleSoftHyphen',
]
a = ui[ui.index('constexpr ReaderAction ACTIONS[] = {'):ui.index('};', ui.index('constexpr ReaderAction ACTIONS[] = {'))]
for s in approved:
    assert s in a, s
assert a.count('ReaderAction::') == 12, 'picker must expose exactly 12 actions'

reader = Path('src/activities/reader/EpubReaderActivity.cpp').read_text(encoding='utf-8')
start = reader.index('  const auto cphun36GestureAction')
end = reader.index('  const auto cphun36LegacyShort', start)
block = reader[start:end]
assert 'READER_BUTTONS.get(physical, gesture)' in block
assert 'if (gesture != ReaderButtonGesture::Double) return false;' in block
assert 'Button::Power' in reader and 'Button::PageBack' in reader and 'Button::PageForward' in reader

print('Applied CPHUN-42 larger button UI, visible 12-action picker, and corrected gesture routing')
