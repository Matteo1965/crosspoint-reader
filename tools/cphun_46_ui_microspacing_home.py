from pathlib import Path

# CPHUN-46: requested UI + typography bundle on top of CPHUN-45.

# 1) Bottom-button picker: 16 actions, replace line-spacing with Settings + Chapter selection,
# remove brackets from mapped values, move action column 2px left.
p = Path('src/activities/settings/ButtonFunctionsActivity.cpp')
t = p.read_text(encoding='utf-8')
a = t.index('constexpr ReaderAction ACTIONS[] = {')
b = t.index('};', a) + 2
t = t[:a] + '''constexpr ReaderAction ACTIONS[] = {
    ReaderAction::None,
    ReaderAction::PreviousPage,
    ReaderAction::NextPage,
    ReaderAction::OpenReaderMenu,
    ReaderAction::OpenTextSettings,
    ReaderAction::OpenDictionary,
    ReaderAction::GoHome,
    ReaderAction::ScreenMarginDown,
    ReaderAction::ScreenMarginUp,
    ReaderAction::ToggleBookmark,
    ReaderAction::OpenBookmarks,
    ReaderAction::ReaderBack,
    ReaderAction::FontSizeDown,
    ReaderAction::FontSizeUp,
    ReaderAction::OpenSettings,
    ReaderAction::OpenChapterSelection,
};''' + t[b:]
t = t.replace('constexpr int kActionX = 250;', 'constexpr int kActionX = 248;', 1)
t = t.replace('values_[row] = std::string("[") + actionLabel(READER_BUTTONS.get(buttonForRow(row), gestureForRow(row))) + "]";',
              'values_[row] = actionLabel(READER_BUTTONS.get(buttonForRow(row), gestureForRow(row)));', 1)
label_anchor = '    case ReaderAction::GoHome: return hu ? "Kezdőképernyő" : "Home";'
if label_anchor not in t:
    raise SystemExit('CPHUN-46 settings label anchor missing')
t = t.replace(label_anchor, label_anchor + '\n    case ReaderAction::OpenSettings: return hu ? "Beállítások" : "Settings";', 1)
p.write_text(t, encoding='utf-8')

# Persisted ReaderAction: append only, never renumber existing values.
p = Path('src/ReaderAction.h')
t = p.read_text(encoding='utf-8')
anchor = '  GoHome = 32,\n\n  COUNT'
if anchor not in t:
    raise SystemExit('CPHUN-46 ReaderAction append anchor missing')
t = t.replace(anchor, '  GoHome = 32,\n  OpenSettings = 33,\n\n  COUNT', 1)
# Settings is a menu action.
t = t.replace('    case ReaderAction::OpenStyleMenu:\n      return ReaderActionGroup::Menu;',
              '    case ReaderAction::OpenStyleMenu:\n    case ReaderAction::OpenSettings:\n      return ReaderActionGroup::Menu;', 1)
p.write_text(t, encoding='utf-8')

# Reader dispatcher: direct Settings and Chapter selection actions.
p = Path('src/activities/reader/EpubReaderActivity.cpp')
r = p.read_text(encoding='utf-8')
anchor = '    if (configured == ReaderAction::OpenDictionary) { openDictionaryWordSelect(); return true; }\n'
if anchor not in r:
    raise SystemExit('CPHUN-46 reader action anchor missing')
insert = anchor + '''    if (configured == ReaderAction::OpenSettings) { cphun36OpenSettings(); return true; }
    if (configured == ReaderAction::OpenChapterSelection) {
      onReaderMenuConfirm(EpubReaderMenuActivity::MenuAction::SELECT_CHAPTER);
      return true;
    }
'''
r = r.replace(anchor, insert, 1)
p.write_text(r, encoding='utf-8')

# 2) Compact OptionPopup one step so all 16 action rows fit. Keep font size unchanged.
p = Path('src/components/OptionPopup.h')
o = p.read_text(encoding='utf-8')
o = o.replace('const int16_t innerPadding = static_cast<int16_t>(metrics.optionPopupInnerPadding);',
              'const bool compact16 = count == MAX_OPTIONS;\n    const int16_t innerPadding = static_cast<int16_t>(compact16 ? std::max(0, metrics.optionPopupInnerPadding - 4)\n                                                               : metrics.optionPopupInnerPadding);', 1)
o = o.replace('props.gap = static_cast<int16_t>(metrics.optionPopupItemSpacing);',
              'props.gap = static_cast<int16_t>(compact16 ? std::max(0, metrics.optionPopupItemSpacing - 2)\n                                                    : metrics.optionPopupItemSpacing);', 1)
o = o.replace('fui::clampI16(target.lineHeight(fui::GfxRendererTarget::FONT_BODY) + metrics.optionPopupSelectionVPadding * 2);',
              'fui::clampI16(target.lineHeight(fui::GfxRendererTarget::FONT_BODY) +\n                      std::max(0, metrics.optionPopupSelectionVPadding - (compact16 ? 3 : 0)) * 2);', 1)
p.write_text(o, encoding='utf-8')

# 3) Typography microspacing: explicit hyphen +6 per adjacent boundary, punctuation +2.
p = Path('lib/Epub/Epub/ParsedText.cpp')
s = p.read_text(encoding='utf-8')
s = s.replace('static_cast<int>(hyphenMicroOpportunityCount) * 4',
              'static_cast<int>(hyphenMicroOpportunityCount) * 6', 1)
s = s.replace('static_cast<int>(punctuationMicroOpportunityCount));',
              'static_cast<int>(punctuationMicroOpportunityCount) * 2);', 1)
s = s.replace('const int micro = std::min(4, hyphenMicroRemaining);',
              'const int micro = std::min(6, hyphenMicroRemaining);', 1)
s = s.replace('xpos += 1;\n          punctuationMicroRemaining -= 1;',
              'const int micro = std::min(2, punctuationMicroRemaining);\n          xpos += micro;\n          punctuationMicroRemaining -= micro;', 1)
s = s.replace('Explicit ASCII hyphen: up to +4 px at each adjacent token boundary.',
              'Explicit ASCII hyphen: up to +6 px at each adjacent token boundary.', 1)
s = s.replace('. , ; : ! ? punctuation: up to +1 px at each adjacent token boundary.',
              '. , ; : ! ? punctuation: up to +2 px at each adjacent token boundary.', 1)
p.write_text(s, encoding='utf-8')

# 4) CrossPoint Version pages 2 and 4 requested wording.
p = Path('src/activities/settings/CrossPointVersionActivity.cpp')
v = p.read_text(encoding='utf-8')
v = v.replace('hu ? "357 egyedi szóalak-kezelési kiegészítés a pontosabb címszókereséshez."',
              'hu ? "Közel 400 egyedi szóalak kezelési kiegészítés és nyelvtani szabály a pontosabb címszókereséshez."', 1)
v = v.replace('hu ? "Optikai margó (Hanging punctuation)" : "Hanging punctuation",\n                hu ? "Az írásjelek margóba helyezésével egyenletesebb szövegszél alakítható ki."',
              'hu ? "Optikai margó - Hanging punctuation" : "Hanging punctuation",\n                hu ? "Az írásjelek margóba helyezésével egyenletesebb szövegszélek."', 1)
p.write_text(v, encoding='utf-8')

# 5) RoundedRaff home: two-line centered current-book title; shift content 4px down,
# remove gray cover-card background; move cover itself another 10px down.
p = Path('src/components/themes/roundedraff/RoundedRaffTheme.cpp')
h = p.read_text(encoding='utf-8')
old = '''    const int maxWidth = rect.width - 2 * RoundedRaffMetrics::values.headerSidePadding;
    const std::string homeTitle = renderer.truncatedText(kTitleFontId, title, maxWidth, EpdFontFamily::BOLD);
    renderer.drawText(kTitleFontId, rect.x + RoundedRaffMetrics::values.headerSidePadding, rect.y, homeTitle.c_str(),
                      true, EpdFontFamily::BOLD);
    return;'''
new = '''    const int maxWidth = rect.width - 2 * RoundedRaffMetrics::values.headerSidePadding;
    const int lineHeight = renderer.getLineHeight(kTitleFontId);
    std::string first;
    std::string second;
    std::string input(title);
    size_t pos = 0;
    while (pos < input.size()) {
      while (pos < input.size() && input[pos] == ' ') ++pos;
      if (pos >= input.size()) break;
      const size_t start = pos;
      while (pos < input.size() && input[pos] != ' ') ++pos;
      const std::string word = input.substr(start, pos - start);
      std::string& line = second.empty() ? first : second;
      const std::string candidate = line.empty() ? word : line + " " + word;
      if (renderer.getTextAdvanceX(kTitleFontId, candidate.c_str(), EpdFontFamily::BOLD) <= maxWidth) {
        line = candidate;
      } else if (second.empty()) {
        second = word;
      } else {
        second = renderer.truncatedText(kTitleFontId, (second + " " + word).c_str(), maxWidth, EpdFontFamily::BOLD);
        break;
      }
    }
    const int lines = second.empty() ? 1 : 2;
    int textY = rect.y + std::max(0, (rect.height - lines * lineHeight) / 2);
    for (const std::string* line : {&first, &second}) {
      if (line->empty()) continue;
      const int textW = renderer.getTextWidth(kTitleFontId, line->c_str(), EpdFontFamily::BOLD);
      renderer.drawText(kTitleFontId, rect.x + (rect.width - textW) / 2, textY, line->c_str(), true,
                        EpdFontFamily::BOLD);
      textY += lineHeight;
    }
    return;'''
if old not in h:
    raise SystemExit('CPHUN-46 home title anchor missing')
h = h.replace(old, new, 1)
h = h.replace('const int imgY = tileY + (tileHeight - RoundedRaffMetrics::values.homeCoverHeight) / 2;',
              'const int imgY = tileY + (tileHeight - RoundedRaffMetrics::values.homeCoverHeight) / 2 + 10;', 1)
# Remove the gray card/background around a real cover while retaining the empty-cover fallback itself.
for block in [
'''    renderer.fillRoundedRect(tileX, tileY, tileWidth, imgY - tileY, kRowRadius, true, true, false, false,
                             Color::LightGray);
    renderer.fillRectDither(tileX, imgY, (tileWidth - coverWidth) / 2, RoundedRaffMetrics::values.homeCoverHeight,
                            Color::LightGray);
    renderer.fillRectDither(tileX + (tileWidth + coverWidth) / 2, imgY, (tileWidth - coverWidth) / 2,
                            RoundedRaffMetrics::values.homeCoverHeight, Color::LightGray);
    renderer.fillRoundedRect(tileX, imgY + RoundedRaffMetrics::values.homeCoverHeight, tileWidth,
                             tileHeight - (imgY - tileY + RoundedRaffMetrics::values.homeCoverHeight), kRowRadius,
                             false, false, true, true, Color::LightGray);
''']:
    if block not in h:
        raise SystemExit('CPHUN-46 gray cover background anchor missing')
    h = h.replace(block, '', 1)
p.write_text(h, encoding='utf-8')

# Shift the home cover tile/menu content 4px down without changing global theme metrics.
p = Path('src/activities/home/HomeActivity.cpp')
home = p.read_text(encoding='utf-8')
home = home.replace('coverRectY = metrics.homeTopPadding;', 'coverRectY = metrics.homeTopPadding + 4;', 1)
home = home.replace('GUI.drawRecentBookCover(renderer, Rect{0, metrics.homeTopPadding, pageWidth, metrics.homeCoverTileHeight},',
                    'GUI.drawRecentBookCover(renderer, Rect{0, metrics.homeTopPadding + 4, pageWidth, metrics.homeCoverTileHeight},', 1)
home = home.replace('Rect{0, metrics.homeTopPadding + metrics.homeCoverTileHeight + metrics.homeMenuTopOffset, pageWidth,',
                    'Rect{0, metrics.homeTopPadding + 4 + metrics.homeCoverTileHeight + metrics.homeMenuTopOffset, pageWidth,', 1)
p.write_text(home, encoding='utf-8')

# Verification.
ui = Path('src/activities/settings/ButtonFunctionsActivity.cpp').read_text(encoding='utf-8')
picker = ui[ui.index('constexpr ReaderAction ACTIONS[] = {'):ui.index('};', ui.index('constexpr ReaderAction ACTIONS[] = {'))]
assert picker.count('ReaderAction::') == 16
for x in ['ReaderAction::OpenSettings', 'ReaderAction::OpenChapterSelection']:
    assert x in picker
for x in ['ReaderAction::LineSpacingPrevious', 'ReaderAction::LineSpacingNext']:
    assert x not in picker
assert 'constexpr int kActionX = 248;' in ui
assert 'std::string("[")' not in ui
assert '"Beállítások"' in ui and '"Fejezetválasztás"' in ui

action = Path('src/ReaderAction.h').read_text(encoding='utf-8')
assert 'GoHome = 32' in action and 'OpenSettings = 33' in action
reader = Path('src/activities/reader/EpubReaderActivity.cpp').read_text(encoding='utf-8')
assert 'configured == ReaderAction::OpenSettings' in reader
assert 'configured == ReaderAction::OpenChapterSelection' in reader
assert 'EpubReaderMenuActivity::MenuAction::SELECT_CHAPTER' in reader

popup = Path('src/components/OptionPopup.h').read_text(encoding='utf-8')
assert 'compact16 = count == MAX_OPTIONS' in popup
assert 'optionPopupSelectionVPadding - (compact16 ? 3 : 0)' in popup

parsed = Path('lib/Epub/Epub/ParsedText.cpp').read_text(encoding='utf-8')
assert 'hyphenMicroOpportunityCount) * 6' in parsed
assert 'punctuationMicroOpportunityCount) * 2' in parsed
assert 'std::min(6, hyphenMicroRemaining)' in parsed
assert 'std::min(2, punctuationMicroRemaining)' in parsed

version = Path('src/activities/settings/CrossPointVersionActivity.cpp').read_text(encoding='utf-8')
assert 'Közel 400 egyedi szóalak kezelési kiegészítés és nyelvtani szabály' in version
assert 'Optikai margó - Hanging punctuation' in version
assert 'egyenletesebb szövegszélek.' in version

rr = Path('src/components/themes/roundedraff/RoundedRaffTheme.cpp').read_text(encoding='utf-8')
assert 'const int lines = second.empty() ? 1 : 2;' in rr
assert '(rect.width - textW) / 2' in rr
assert 'homeCoverHeight) / 2 + 10' in rr
home = Path('src/activities/home/HomeActivity.cpp').read_text(encoding='utf-8')
assert 'coverRectY = metrics.homeTopPadding + 4;' in home
assert 'Rect{0, metrics.homeTopPadding + 4, pageWidth' in home

print('Applied CPHUN-46 UI, picker, +6/+2 microspacing, version text and home layout bundle')
