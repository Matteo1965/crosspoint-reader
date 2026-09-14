from pathlib import Path


def replace_once(path, old, new):
    path = Path(path)
    text = path.read_text(encoding="utf-8")
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"CPHUN-129: {path}: expected one match, found {count}: {old[:120]!r}")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


# Give only the Settings reader-category row the requested Hungarian name.
replace_once(
    "src/activities/settings/SettingsActivity.cpp",
    "    item.label = I18N.get(settings[i].nameId);",
    '''    item.label = settings[i].nameId == StrId::STR_DICTIONARY && I18N.getLanguage() == Language::HU
                     ? "Szótár beállítása"
                     : I18N.get(settings[i].nameId);''',
)

# Add the same dynamic dictionary picker to the Reading tab, after manual search.
replace_once(
    "src/activities/reader/EpubReaderMenuActivity.h",
    "    MANUAL_DICTIONARY_SEARCH,\n    BOOK_DESCRIPTION,",
    "    MANUAL_DICTIONARY_SEARCH,\n    DICTIONARY_SETTINGS,\n    BOOK_DESCRIPTION,",
)
replace_once(
    "src/activities/reader/EpubReaderMenuActivity.h",
    "#include <array>\n#include <string>",
    "#include <array>\n#include <functional>\n#include <string>",
)
replace_once(
    "src/activities/reader/EpubReaderMenuActivity.h",
    "  int currentPage = 0;",
    '''  std::vector<std::string> dictionaryOptionLabels;
  std::vector<const char*> dictionaryOptionPointers;
  std::function<void(uint8_t)> dictionarySetter;
  uint8_t selectedDictionaryOption = 0;
  int currentPage = 0;''',
)
replace_once(
    "src/activities/reader/EpubReaderMenuActivity.cpp",
    '#include "MappedInputManager.h"\n#include "ReaderUtils.h"',
    '#include "MappedInputManager.h"\n#include "ReaderUtils.h"\n#include "SettingsList.h"',
)
replace_once(
    "src/activities/reader/EpubReaderMenuActivity.cpp",
    '''      bookProgressPercent(bookProgressPercent) {
  rebuildMenuRowItems();
}''',
    '''      bookProgressPercent(bookProgressPercent) {
  std::vector<DictionaryEntry> dictionaries;
  DictionaryRegistry::discover(dictionaries);
  auto dictionarySetting = buildDictionarySetting(dictionaries);
  dictionaryOptionLabels = std::move(dictionarySetting.enumStringValues);
  dictionaryOptionPointers.reserve(dictionaryOptionLabels.size());
  for (const auto& label : dictionaryOptionLabels) dictionaryOptionPointers.push_back(label.c_str());
  selectedDictionaryOption = dictionarySetting.valueGetter ? dictionarySetting.valueGetter() : 0;
  dictionarySetter = std::move(dictionarySetting.valueSetter);
  rebuildMenuRowItems();
}''',
)
replace_once(
    "src/activities/reader/EpubReaderMenuActivity.cpp",
    '''  items.push_back({MenuAction::MANUAL_DICTIONARY_SEARCH, StrId::STR_LOOKUP, "Kézi keresés"});
  items.push_back({MenuAction::NIGHT_MODE, StrId::STR_NIGHT_MODE});''',
    '''  items.push_back({MenuAction::MANUAL_DICTIONARY_SEARCH, StrId::STR_LOOKUP, "Kézi keresés"});
  items.push_back({MenuAction::DICTIONARY_SETTINGS, StrId::STR_DICTIONARY, "Szótár beállítása"});
  items.push_back({MenuAction::NIGHT_MODE, StrId::STR_NIGHT_MODE});''',
)
replace_once(
    "src/activities/reader/EpubReaderMenuActivity.cpp",
    '''  if (selectedAction == MenuAction::NIGHT_MODE) {''',
    '''  if (selectedAction == MenuAction::DICTIONARY_SETTINGS) {
    if (!dictionaryOptionPointers.empty()) {
      optionPopup.show("Szótár beállítása", dictionaryOptionPointers.data(),
                       static_cast<int>(dictionaryOptionPointers.size()), selectedDictionaryOption,
                       [this](int idx) {
                         selectedDictionaryOption = static_cast<uint8_t>(idx);
                         if (dictionarySetter) dictionarySetter(selectedDictionaryOption);
                         SETTINGS.saveToFile();
                         requestUpdate();
                       });
      requestUpdate();
    }
    return;
  }

  if (selectedAction == MenuAction::NIGHT_MODE) {''',
)
replace_once(
    "src/activities/reader/EpubReaderMenuActivity.cpp",
    '''    } else if (action == MenuAction::NIGHT_MODE) {
      menuRowItems[i].value = I18N.get(SETTINGS.screenInverted ? StrId::STR_STATE_ON : StrId::STR_STATE_OFF);''',
    '''    } else if (action == MenuAction::DICTIONARY_SETTINGS) {
      menuRowItems[i].value = selectedDictionaryOption < dictionaryOptionPointers.size()
                                  ? dictionaryOptionPointers[selectedDictionaryOption]
                                  : nullptr;
    } else if (action == MenuAction::NIGHT_MODE) {
      menuRowItems[i].value = I18N.get(SETTINGS.screenInverted ? StrId::STR_STATE_ON : StrId::STR_STATE_OFF);''',
)

# Metadata body: use Noto Sans 14 consistently for measuring, wrapping and drawing.
book = Path("src/activities/reader/BookInfoActivity.cpp")
text = book.read_text(encoding="utf-8")
# limitTagsToTwoLines is metadata-only.
start = text.index("std::string limitTagsToTwoLines")
end = text.index("}  // namespace", start)
segment = text[start:end].replace("NOTOSERIF_14_FONT_ID", "NOTOSANS_14_FONT_ID")
text = text[:start] + segment + text[end:]
text = text.replace(
    "  renderer.setMissingGlyphFallbackFont(NOTOSERIF_14_FONT_ID);",
    "  renderer.setMissingGlyphFallbackFont(page_ == Page::Metadata ? NOTOSANS_14_FONT_ID : NOTOSERIF_14_FONT_ID);",
    1,
)
text = text.replace(
    "  return renderer.getTextAdvanceX(NOTOSERIF_14_FONT_ID, buf, EpdFontFamily::REGULAR);",
    "  return renderer.getTextAdvanceX(page_ == Page::Metadata ? NOTOSANS_14_FONT_ID : NOTOSERIF_14_FONT_ID, buf,\n                                  EpdFontFamily::REGULAR);",
    1,
)
# Exactly two body line-height sites.
old_lh = "  const int lineHeight = renderer.getLineHeight(NOTOSERIF_14_FONT_ID);"
if text.count(old_lh) != 2:
    raise SystemExit(f"CPHUN-129: BookInfo line-height matches={text.count(old_lh)}")
text = text.replace(
    old_lh,
    "  const int lineHeight = renderer.getLineHeight(page_ == Page::Metadata ? NOTOSANS_14_FONT_ID\n                                                                    : NOTOSERIF_14_FONT_ID);",
)
text = text.replace(
    "        renderer.drawText(NOTOSERIF_14_FONT_ID, x, y, labelBuf, true, EpdFontFamily::REGULAR);",
    "        renderer.drawText(NOTOSANS_14_FONT_ID, x, y, labelBuf, true, EpdFontFamily::REGULAR);",
    1,
)
text = text.replace(
    "        renderer.drawText(NOTOSERIF_14_FONT_ID, METADATA_VALUE_X, y, buf, true, EpdFontFamily::REGULAR);",
    "        renderer.drawText(NOTOSANS_14_FONT_ID, METADATA_VALUE_X, y, buf, true, EpdFontFamily::REGULAR);",
    1,
)

# Keep the themed header band, but render both BookInfo titles one available font step larger.
old_header = '''  GUI.drawHeader(renderer, Rect{contentX, headerY, contentWidth, metrics.headerHeight}, title);

  // BookInfo pages intentionally omit the standard header battery indicator.'''
new_header = '''  GUI.drawHeader(renderer, Rect{contentX, headerY, contentWidth, metrics.headerHeight}, "");

  // BookInfo pages intentionally omit the standard header battery indicator.'''
if text.count(old_header) != 1:
    raise SystemExit(f"CPHUN-129: header anchor matches={text.count(old_header)}")
text = text.replace(old_header, new_header, 1)
old_clear_end = '''  if (clearWidth > 0 && metrics.headerHeight > 1) {
    renderer.fillRect(clearX, headerY, clearWidth, metrics.headerHeight - 1, false);
  }

  if (totalPages_ > 1) {'''
new_clear_end = '''  if (clearWidth > 0 && metrics.headerHeight > 1) {
    renderer.fillRect(clearX, headerY, clearWidth, metrics.headerHeight - 1, false);
  }

  const int titleY = headerY + (metrics.headerHeight - renderer.getLineHeight(NOTOSANS_16_FONT_ID)) / 2;
  renderer.drawText(NOTOSANS_16_FONT_ID, contentX + SIDE_PADDING, titleY, title, true, EpdFontFamily::REGULAR);

  if (totalPages_ > 1) {'''
if text.count(old_clear_end) != 1:
    raise SystemExit(f"CPHUN-129: title insertion anchor matches={text.count(old_clear_end)}")
text = text.replace(old_clear_end, new_clear_end, 1)
book.write_text(text, encoding="utf-8")

replace_once(
    "src/CPHUNBuildId.h",
    '#define CPHUN_BUILD_ID "CPHUN-260914-128-EXP"',
    '#define CPHUN_BUILD_ID "CPHUN-260914-129-EXP"',
)
