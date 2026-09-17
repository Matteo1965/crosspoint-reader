from pathlib import Path


def replace_once(path, old, new):
    p = Path(path)
    text = p.read_text(encoding="utf-8")
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"CPHUN-135r4b: {path}: expected one match, found {count}: {old[:180]!r}")
    p.write_text(text.replace(old, new, 1), encoding="utf-8")


def insert_after(path, marker, addition):
    replace_once(path, marker, marker + addition)


# -----------------------------------------------------------------------------
# 4-5) Empty replacement = intentional whole-word deletion, while preserving
# the stable spine/visible-offset identity and remembering the adjacent-space
# cleanup policy for the later physical EPUB rewrite. Reopening an edit must
# load the previous replacement even when that replacement is empty.
# -----------------------------------------------------------------------------
replace_once(
    "src/highlights/TextEditStore.h",
    '''  std::string originalText;\n  std::string replacementText;\n};''',
    '''  std::string originalText;\n  std::string replacementText;\n  bool trimAdjacentSpace = false;\n};''',
)
replace_once(
    "src/highlights/TextEditStore.cpp",
    '''    edit.originalText = item["original"] | "";\n    edit.replacementText = item["replacement"] | "";\n    edits_.push_back(std::move(edit));''',
    '''    edit.originalText = item["original"] | "";\n    edit.replacementText = item["replacement"] | "";\n    edit.trimAdjacentSpace = item["trimAdjacentSpace"] | false;\n    edits_.push_back(std::move(edit));''',
)
replace_once(
    "src/highlights/TextEditStore.cpp",
    '''    item["original"] = edit.originalText;\n    item["replacement"] = edit.replacementText;\n  }''',
    '''    item["original"] = edit.originalText;\n    item["replacement"] = edit.replacementText;\n    item["trimAdjacentSpace"] = edit.trimAdjacentSpace;\n  }''',
)
replace_once(
    "src/activities/reader/EpubReaderActivity.cpp",
    '''    if (const auto* old = textEditStore->find(selection.spineIndex, selection.visibleTextOffset)) {\n      if (!old->replacementText.empty()) initialText = old->replacementText;\n    }''',
    '''    if (const auto* old = textEditStore->find(selection.spineIndex, selection.visibleTextOffset)) {\n      initialText = old->replacementText;\n    }''',
)
replace_once(
    "src/activities/reader/EpubReaderActivity.cpp",
    '''          if (const auto* keyboard = std::get_if<KeyboardResult>(&result.data)) {\n            if (!keyboard->text.empty() && textEditStore) {\n              textEditStore->upsert({selection.spineIndex, selection.visibleTextOffset, selection.length,\n                                     selection.text, keyboard->text});\n            }\n          }''',
    '''          if (const auto* keyboard = std::get_if<KeyboardResult>(&result.data)) {\n            if (textEditStore) {\n              textEditStore->upsert({selection.spineIndex, selection.visibleTextOffset, selection.length,\n                                     selection.text, keyboard->text, keyboard->text.empty()});\n            }\n          }''',
)


# -----------------------------------------------------------------------------
# Footnote-linked word hyphenation. Footnote display text remains visually
# attached (TokenBoundary supplies zero-space punctuation handling), but it must
# not make the preceding lexical word an unbreakable continuation. This is the
# separate-DOM-node case: valóságot.<a ...>{12}</a>.
# -----------------------------------------------------------------------------
replace_once(
    "lib/Epub/Epub/parsers/ChapterHtmlSlimParser.cpp",
    '''      self->flushPartWordBuffer();\n      self->nextWordContinues = true;\n    }\n    self->insideFootnoteLink = true;''',
    '''      self->flushPartWordBuffer();\n      // CPHUN-135r4b: a following noteref must not suppress hyphenation of\n      // the lexical word immediately before the separate <a> node. The\n      // noteref punctuation still receives zero-space attachment in ParsedText.\n      self->nextWordContinues = false;\n    }\n    self->insideFootnoteLink = true;''',
)


# -----------------------------------------------------------------------------
# 6) fn layer: make both symbol layers five rows high, keep the number row on
# top with Backspace/Delete at its end, use an icon Shift key, add a useful
# punctuation row, and keep the lower-left mode key labelled/narrow as "fn".
# -----------------------------------------------------------------------------
layout = "src/activities/util/HungarianKeyboardLayout.h"
replace_once(
    layout,
    '''inline const fui::KeyboardKey SYMBOL_ROW1[] = {\n    HUK("1", "1", '1'), HUK("2", "2", '2'), HUK("3", "3", '3'), HUK("4", "4", '4'),\n    HUK("5", "5", '5'), HUK("6", "6", '6'), HUK("7", "7", '7'), HUK("8", "8", '8'),\n    HUK("9", "9", '9'), HUK("0", "0", '0'), HUK("-", "-", '-')};''',
    '''inline const fui::KeyboardKey SYMBOL_ROW1[] = {\n    HUK("1", "1", '1'), HUK("2", "2", '2'), HUK("3", "3", '3'), HUK("4", "4", '4'),\n    HUK("5", "5", '5'), HUK("6", "6", '6'), HUK("7", "7", '7'), HUK("8", "8", '8'),\n    HUK("9", "9", '9'), HUK("0", "0", '0'),\n    HUKS("Del", fui::KeyKind::Delete, fui::QWERTY_KEY_BACKSPACE, 2)};''',
)
insert_after(
    layout,
    '''inline const fui::KeyboardKey SYMBOL_ROW2[] = {\n    HUK("/", "/", '/'), HUK(":", ":", ':'), HUK(";", ";", ';'), HUK("(", "(", '('), HUK(")", ")", ')'),\n    HUK("€", "€", 1401), HUK("$", "$", '$'), HUK("&", "&", '&'), HUK("@", "@", '@'),\n    HUK("„", "„", 1402), HUK("”", "”", 1403)};\n''',
    '''inline const fui::KeyboardKey SYMBOL_EXTRA_ROW[] = {\n    HUK("[", "[", '['), HUK("]", "]", ']'), HUK("{", "{", '{'), HUK("}", "}", '}'),\n    HUK("–", "–", 1410), HUK("—", "—", 1411), HUK("…", "…", 1404), HUK("§", "§", 1413),\n    HUK("°", "°", 1414), HUK("«", "«", 1415), HUK("»", "»", 1416)};\n''',
)
replace_once(
    layout,
    '''inline const fui::KeyboardKey SYMBOL_ROW3[] = {\n    HUKS("#+=", fui::KeyKind::Shift, fui::QWERTY_KEY_SHIFT, 4), HUK(".", ".", '.'), HUK(",", ",", ','),\n    HUK("?", "?", '?'), HUK("!", "!", '!'), HUK("'", "'", '\\''), HUK("\\\"", "\\\"", '\"'),\n    HUK("#", "#", '#'), HUK("…", "…", 1404), HUKS("Del", fui::KeyKind::Delete, fui::QWERTY_KEY_BACKSPACE, 4)};''',
    '''inline const fui::KeyboardKey SYMBOL_ROW3[] = {\n    HUKS(nullptr, fui::KeyKind::Shift, fui::QWERTY_KEY_SHIFT, 3), HUK(".", ".", '.'), HUK(",", ",", ','),\n    HUK("?", "?", '?'), HUK("!", "!", '!'), HUK("'", "'", '\\''), HUK("\\\"", "\\\"", '\"'),\n    HUK("#", "#", '#'), HUK("…", "…", 1404), HUKW("€", "€", 1401, 3)};''',
)
replace_once(
    layout,
    '''inline const fui::KeyboardKey SYMBOL2_ROW3[] = {\n    HUKS("123", fui::KeyKind::Shift, fui::QWERTY_KEY_SHIFT, 4), HUK(".", ".", '.'), HUK(",", ",", ','),\n    HUK("?", "?", '?'), HUK("!", "!", '!'), HUK("'", "'", '\\''), HUK("\\\"", "\\\"", '\"'),\n    HUK(":", ":", ':'), HUK(";", ";", ';'), HUKS("Del", fui::KeyKind::Delete, fui::QWERTY_KEY_BACKSPACE, 4)};''',
    '''inline const fui::KeyboardKey SYMBOL2_ROW3[] = {\n    HUKS(nullptr, fui::KeyKind::Shift, fui::QWERTY_KEY_SHIFT, 3), HUK(".", ".", '.'), HUK(",", ",", ','),\n    HUK("?", "?", '?'), HUK("!", "!", '!'), HUK("'", "'", '\\''), HUK("\\\"", "\\\"", '\"'),\n    HUK(":", ":", ':'), HUK(";", ";", ';'), HUKW("±", "±", 1412, 3)};''',
)
replace_once(
    layout,
    '''inline const fui::KeyboardKey SYMBOL_BOTTOM[] = {\n    HUKS("ABC", fui::KeyKind::Mode, fui::QWERTY_KEY_MODE, 4), HUK(",", ",", ','),\n    HUKS("Space", fui::KeyKind::Space, fui::QWERTY_KEY_SPACE, 10), HUK(".", ".", '.'),\n    HUKS("OK", fui::KeyKind::Ok, fui::QWERTY_KEY_ENTER, 4)};''',
    '''inline const fui::KeyboardKey SYMBOL_BOTTOM[] = {\n    HUKS("fn", fui::KeyKind::Mode, fui::QWERTY_KEY_MODE, 2),\n    HUK("/", "/", '/'), HUK("?", "?", '?'),\n    HUKS("Space", fui::KeyKind::Space, fui::QWERTY_KEY_SPACE, 10),\n    HUK(",", ",", ','), HUK(".", ".", '.'),\n    HUKS("OK", fui::KeyKind::Ok, fui::QWERTY_KEY_ENTER, 2)};''',
)
replace_once(
    layout,
    '''inline const fui::KeyboardRow SYMBOL_ROWS[] = {\n    {SYMBOL_ROW1, 11, 0}, {SYMBOL_ROW2, 11, 0}, {SYMBOL_ROW3, 10, 0}, {SYMBOL_BOTTOM, 5, 0}};\ninline const fui::KeyboardRow SYMBOL2_ROWS[] = {\n    {SYMBOL2_ROW1, 11, 0}, {SYMBOL2_ROW2, 11, 0}, {SYMBOL2_ROW3, 10, 0}, {SYMBOL_BOTTOM, 5, 0}};''',
    '''inline const fui::KeyboardRow SYMBOL_ROWS[] = {\n    {SYMBOL_ROW1, 11, 0}, {SYMBOL_ROW2, 11, 0}, {SYMBOL_EXTRA_ROW, 11, 0}, {SYMBOL_ROW3, 10, 0},\n    {SYMBOL_BOTTOM, 7, 0}};\ninline const fui::KeyboardRow SYMBOL2_ROWS[] = {\n    {SYMBOL_ROW1, 11, 0}, {SYMBOL2_ROW1, 11, 0}, {SYMBOL2_ROW2, 11, 0}, {SYMBOL2_ROW3, 10, 0},\n    {SYMBOL_BOTTOM, 7, 0}};''',
)
replace_once(layout, "inline const fui::KeyboardLayout SYMBOL_LAYOUT{SYMBOL_ROWS, 4};", "inline const fui::KeyboardLayout SYMBOL_LAYOUT{SYMBOL_ROWS, 5};")
replace_once(layout, "inline const fui::KeyboardLayout SYMBOL2_LAYOUT{SYMBOL2_ROWS, 4};", "inline const fui::KeyboardLayout SYMBOL2_LAYOUT{SYMBOL2_ROWS, 5};")


# -----------------------------------------------------------------------------
# 8) Final Szerkesztés help text and +10 px from r4a (60 px total).
# -----------------------------------------------------------------------------
replace_once(
    "src/activities/util/KeyboardEntryActivity.cpp",
    '''    int y = (underlineBottom + kbRect.y) / 2 - 5 * tipsLh / 2 + 50;\n    drawTip("Tippek:", y);\n    y += tipsLh;\n    drawTip("KIJELÖLÉS: kijelölt billentyű használata", y);\n    y += tipsLh;\n    drawTip("Fel/le: billentyűsor váltása", y);\n    y += tipsLh;\n    drawTip("Fel hosszan: kurzor mód; Le: billentyűzet mód", y);\n    y += tipsLh;\n    drawTip("TÖRLÉS hosszan: teljes szöveg törlése", y);''',
    '''    int y = (underlineBottom + kbRect.y) / 2 - 5 * tipsLh / 2 + 60;\n    drawTip("Tippek:", y);\n    y += tipsLh;\n    drawTip("KIJELÖLÉS: aktuális gomb használata", y);\n    y += tipsLh;\n    drawTip("SHIFT: billentyűsor váltása", y);\n    y += tipsLh;\n    drawTip("FEL HOSSZAN: kurzor mód", y);\n    y += tipsLh;\n    drawTip("LE: billentyűzet mód", y);\n    y += tipsLh;\n    drawTip("TÖRLÉS HOSSZAN: teljes szó törlése", y);''',
)


# -----------------------------------------------------------------------------
# Dictionary value: always a single compact value string. Truncate by measured
# pixel width and append "..."; never let a long dictionary name increase the
# menu row height or wrap onto another line.
# -----------------------------------------------------------------------------
replace_once(
    "src/activities/reader/EpubReaderMenuActivity.h",
    '''  std::vector<std::string> dictionaryOptionLabels;\n  std::vector<const char*> dictionaryOptionPointers;''',
    '''  std::vector<std::string> dictionaryOptionLabels;\n  std::vector<const char*> dictionaryOptionPointers;\n  std::string dictionaryDisplayValue;''',
)
replace_once(
    "src/activities/reader/EpubReaderMenuActivity.cpp",
    '#include "SettingsList.h"',
    '#include "SettingsList.h"\n#include "fontIds.h"',
)
insert_after(
    "src/activities/reader/EpubReaderMenuActivity.cpp",
    "namespace fui = freeink::ui;\n",
    '''\nnamespace {\nstd::string fitDictionaryMenuValue(GfxRenderer& renderer, const char* raw) {\n  if (!raw) return {};\n  constexpr int MAX_VALUE_WIDTH = 170;\n  std::string value(raw);\n  if (renderer.getTextAdvanceX(NOTOSANS_14_FONT_ID, value.c_str(), EpdFontFamily::REGULAR) <= MAX_VALUE_WIDTH)\n    return value;\n  constexpr const char* dots = "...";\n  while (!value.empty()) {\n    const auto candidate = value + dots;\n    if (renderer.getTextAdvanceX(NOTOSANS_14_FONT_ID, candidate.c_str(), EpdFontFamily::REGULAR) <= MAX_VALUE_WIDTH)\n      return candidate;\n    size_t cut = value.size() - 1;\n    while (cut > 0 && (static_cast<unsigned char>(value[cut]) & 0xC0) == 0x80) --cut;\n    value.resize(cut);\n  }\n  return dots;\n}\n}  // namespace\n''',
)
replace_once(
    "src/activities/reader/EpubReaderMenuActivity.cpp",
    '''    } else if (action == MenuAction::DICTIONARY_SETTINGS) {\n      menuRowItems[i].value = selectedDictionaryOption < dictionaryOptionPointers.size()\n                                  ? dictionaryOptionPointers[selectedDictionaryOption]\n                                  : nullptr;''',
    '''    } else if (action == MenuAction::DICTIONARY_SETTINGS) {\n      const char* rawDictionary = selectedDictionaryOption < dictionaryOptionPointers.size()\n                                      ? dictionaryOptionPointers[selectedDictionaryOption]\n                                      : nullptr;\n      dictionaryDisplayValue = fitDictionaryMenuValue(renderer, rawDictionary);\n      menuRowItems[i].value = dictionaryDisplayValue.empty() ? nullptr : dictionaryDisplayValue.c_str();''',
)


# -----------------------------------------------------------------------------
# Footnotes: index the whole book lazily from XHTML noteref links, use the
# existing selectable list for all entries, and display the selected note in the
# reusable Noto Serif 14 popup instead of navigating away from the reading page.
# -----------------------------------------------------------------------------
replace_once(
    "src/activities/reader/EpubReaderActivity.h",
    "#include <atomic>\n#include <memory>",
    "#include <atomic>\n#include <memory>\n#include <string>",
)
replace_once(
    "src/activities/reader/EpubReaderActivity.h",
    '''  std::vector<FootnoteEntry> currentPageFootnotes;''',
    '''  std::vector<FootnoteEntry> currentPageFootnotes;\n  std::vector<FootnoteEntry> bookFootnotes;\n  bool bookFootnotesIndexed = false;\n  void ensureBookFootnotes();\n  std::string extractFootnoteText(const std::string& href, int sourceSpineIndex) const;\n  void openFootnotesList(bool wholeBook, bool returnToMenu);\n  void openFootnotePopup(const FootnoteEntry& footnote, int sourceSpineIndex);''',
)
replace_once(
    "src/activities/reader/EpubReaderActivity.cpp",
    "#include <algorithm>\n#include <functional>",
    "#include <algorithm>\n#include <cctype>\n#include <cstdlib>\n#include <cstring>\n#include <functional>",
)
replace_once(
    "src/activities/reader/EpubReaderActivity.cpp",
    '#include "EpubReaderFootnotesActivity.h"',
    '#include "EpubReaderFootnotesActivity.h"\n#include "FootnotePopupActivity.h"',
)
insert_after(
    "src/activities/reader/EpubReaderActivity.cpp",
    '''bool isInReadFolder(const std::string& path) {\n  constexpr size_t n = sizeof(READ_FOLDER) - 1;\n  return path.size() > n && path.compare(0, n, READ_FOLDER) == 0 && path[n] == '/';\n}\n''',
    '''\nstd::string trimPlain(std::string value) {\n  auto ws = [](unsigned char c) { return std::isspace(c) != 0; };\n  while (!value.empty() && ws(static_cast<unsigned char>(value.front()))) value.erase(value.begin());\n  while (!value.empty() && ws(static_cast<unsigned char>(value.back()))) value.pop_back();\n  return value;\n}\n\nstd::string htmlToPlain(const std::string& html) {\n  std::string out;\n  out.reserve(html.size());\n  bool inTag = false;\n  bool pendingSpace = false;\n  for (size_t i = 0; i < html.size(); ++i) {\n    const char c = html[i];\n    if (c == '<') { inTag = true; pendingSpace = !out.empty(); continue; }\n    if (c == '>') { inTag = false; continue; }\n    if (inTag) continue;\n    if (c == '&') {\n      const size_t semi = html.find(';', i + 1);\n      if (semi != std::string::npos && semi - i <= 8) {\n        const std::string entity = html.substr(i, semi - i + 1);\n        if (entity == "&nbsp;") { pendingSpace = true; i = semi; continue; }\n        if (entity == "&amp;") { if (pendingSpace && !out.empty()) out.push_back(' '); out.push_back('&'); pendingSpace = false; i = semi; continue; }\n        if (entity == "&quot;") { if (pendingSpace && !out.empty()) out.push_back(' '); out.push_back('\\"'); pendingSpace = false; i = semi; continue; }\n        if (entity == "&lt;") { if (pendingSpace && !out.empty()) out.push_back(' '); out.push_back('<'); pendingSpace = false; i = semi; continue; }\n        if (entity == "&gt;") { if (pendingSpace && !out.empty()) out.push_back(' '); out.push_back('>'); pendingSpace = false; i = semi; continue; }\n      }\n    }\n    if (std::isspace(static_cast<unsigned char>(c))) { pendingSpace = !out.empty(); continue; }\n    if (pendingSpace && !out.empty()) out.push_back(' ');\n    pendingSpace = false;\n    out.push_back(c);\n  }\n  return trimPlain(std::move(out));\n}\n\nstd::string htmlAttribute(const std::string& tag, const char* name) {\n  const std::string needle = std::string(name) + "=";\n  size_t p = tag.find(needle);\n  if (p == std::string::npos) return {};\n  p += needle.size();\n  while (p < tag.size() && std::isspace(static_cast<unsigned char>(tag[p]))) ++p;\n  if (p >= tag.size()) return {};\n  const char quote = tag[p];\n  if (quote != '\\'' && quote != '\\"') return {};\n  const size_t end = tag.find(quote, p + 1);\n  return end == std::string::npos ? std::string() : tag.substr(p + 1, end - p - 1);\n}\n\nbool looksLikeFootnoteLabel(const std::string& label) {\n  if (label.empty() || label.size() > 24) return false;\n  bool hasDigit = false;\n  for (unsigned char c : label) {\n    if (c >= '0' && c <= '9') { hasDigit = true; continue; }\n    if (std::isspace(c) || c == '{' || c == '}' || c == '[' || c == ']' || c == '(' || c == ')' || c == '.') continue;\n    return false;\n  }\n  return hasDigit;\n}\n''',
)

# Index before the reader menu decides whether the Footnotes row exists.
replace_once(
    "src/activities/reader/EpubReaderActivity.cpp",
    '''void EpubReaderActivity::openReaderMenu(const bool startOnBookTab) {\n  pendingManualTurn = 0;''',
    '''void EpubReaderActivity::openReaderMenu(const bool startOnBookTab) {\n  pendingManualTurn = 0;\n  ensureBookFootnotes();''',
)
replace_once(
    "src/activities/reader/EpubReaderActivity.cpp",
    '''                             SETTINGS.orientation, !currentPageFootnotes.empty(), !cachedBookmarks.empty(), startOnBookTab),''',
    '''                             SETTINGS.orientation, !bookFootnotes.empty(), !cachedBookmarks.empty(), startOnBookTab),''',
)

# Add implementation immediately before openReaderMenu.
insert_after(
    "src/activities/reader/EpubReaderActivity.cpp",
    '''  loadCachedBookmarks();\n  return true;\n}\n''',
    '''\nvoid EpubReaderActivity::ensureBookFootnotes() {\n  if (bookFootnotesIndexed || !epub) return;\n  bookFootnotesIndexed = true;\n  bookFootnotes.clear();\n  constexpr size_t MAX_SCAN_BYTES = 2 * 1024 * 1024;\n  constexpr size_t MAX_BOOK_FOOTNOTES = 1024;\n  for (int spine = 0; spine < epub->getSpineItemsCount() && bookFootnotes.size() < MAX_BOOK_FOOTNOTES; ++spine) {\n    const auto item = epub->getSpineItem(spine);\n    size_t size = 0;\n    if (!epub->getItemSize(item.href, &size) || size == 0 || size > MAX_SCAN_BYTES) continue;\n    uint8_t* bytes = epub->readItemContentsToBytes(item.href, &size, true);\n    if (!bytes) continue;\n    std::string html(reinterpret_cast<char*>(bytes), size);\n    free(bytes);\n    size_t pos = 0;\n    while ((pos = html.find("<a", pos)) != std::string::npos && bookFootnotes.size() < MAX_BOOK_FOOTNOTES) {\n      const size_t tagEnd = html.find('>', pos + 2);\n      if (tagEnd == std::string::npos) break;\n      const std::string tag = html.substr(pos, tagEnd - pos + 1);\n      std::string href = htmlAttribute(tag, "href");\n      const size_t close = html.find("</a>", tagEnd + 1);\n      if (close == std::string::npos) { pos = tagEnd + 1; continue; }\n      const std::string label = htmlToPlain(html.substr(tagEnd + 1, close - tagEnd - 1));\n      pos = close + 4;\n      if (href.empty() || href.find('#') == std::string::npos || !looksLikeFootnoteLabel(label)) continue;\n      if (!href.empty() && href[0] == '#') {\n        href = item.href + href;\n      } else if (href.find("://") == std::string::npos && href.find('/') == std::string::npos) {\n        const size_t slash = item.href.rfind('/');\n        if (slash != std::string::npos) href = item.href.substr(0, slash + 1) + href;\n      }\n      const bool duplicate = std::any_of(bookFootnotes.begin(), bookFootnotes.end(), [&](const FootnoteEntry& e) {\n        return href == e.href;\n      });\n      if (duplicate) continue;\n      FootnoteEntry entry;\n      std::strncpy(entry.number, label.c_str(), sizeof(entry.number) - 1);\n      entry.number[sizeof(entry.number) - 1] = '\\0';\n      std::strncpy(entry.href, href.c_str(), sizeof(entry.href) - 1);\n      entry.href[sizeof(entry.href) - 1] = '\\0';\n      bookFootnotes.push_back(entry);\n    }\n  }\n}\n\nstd::string EpubReaderActivity::extractFootnoteText(const std::string& href, const int sourceSpineIndex) const {\n  if (!epub || href.empty()) return {};\n  const size_t hash = href.find('#');\n  if (hash == std::string::npos || hash + 1 >= href.size()) return {};\n  const std::string anchor = href.substr(hash + 1);\n  int spine = href[0] == '#' ? sourceSpineIndex : epub->resolveHrefToSpineIndex(href);\n  if (spine < 0 && sourceSpineIndex >= 0) spine = sourceSpineIndex;\n  if (spine < 0 || spine >= epub->getSpineItemsCount()) return {};\n  const auto item = epub->getSpineItem(spine);\n  size_t size = 0;\n  uint8_t* bytes = epub->readItemContentsToBytes(item.href, &size, true);\n  if (!bytes) return {};\n  std::string html(reinterpret_cast<char*>(bytes), size);\n  free(bytes);\n\n  size_t idPos = html.find("id=\\\"" + anchor + "\\\"");\n  if (idPos == std::string::npos) idPos = html.find("id='" + anchor + "'");\n  if (idPos == std::string::npos) idPos = html.find("name=\\\"" + anchor + "\\\"");\n  if (idPos == std::string::npos) return {};\n  size_t startTag = html.rfind('<', idPos);\n  size_t tagEnd = html.find('>', idPos);\n  if (startTag == std::string::npos || tagEnd == std::string::npos) return {};\n  size_t nameStart = startTag + 1;\n  while (nameStart < tagEnd && std::isspace(static_cast<unsigned char>(html[nameStart]))) ++nameStart;\n  size_t nameEnd = nameStart;\n  while (nameEnd < tagEnd && (std::isalnum(static_cast<unsigned char>(html[nameEnd])) || html[nameEnd] == ':' || html[nameEnd] == '_')) ++nameEnd;\n  const std::string tagName = html.substr(nameStart, nameEnd - nameStart);\n  std::string plain;\n  if (!tagName.empty()) {\n    const std::string closeTag = "</" + tagName + ">";\n    const size_t close = html.find(closeTag, tagEnd + 1);\n    if (close != std::string::npos) plain = htmlToPlain(html.substr(tagEnd + 1, close - tagEnd - 1));\n    if (plain.empty() && close != std::string::npos) {\n      const size_t after = close + closeTag.size();\n      size_t stop = html.find("</p>", after);\n      const size_t stopLi = html.find("</li>", after);\n      const size_t stopDiv = html.find("</div>", after);\n      if (stop == std::string::npos || (stopLi != std::string::npos && stopLi < stop)) stop = stopLi;\n      if (stop == std::string::npos || (stopDiv != std::string::npos && stopDiv < stop)) stop = stopDiv;\n      if (stop == std::string::npos) stop = std::min(html.size(), after + 2048);\n      plain = htmlToPlain(html.substr(after, stop - after));\n    }\n  }\n  return trimPlain(std::move(plain));\n}\n\nvoid EpubReaderActivity::openFootnotePopup(const FootnoteEntry& footnote, const int sourceSpineIndex) {\n  std::string text = extractFootnoteText(footnote.href, sourceSpineIndex);\n  if (text.empty()) text = "A lábjegyzet szövege nem olvasható.";\n  startActivityForResult(std::make_unique<FootnotePopupActivity>(renderer, mappedInput, footnote.number, std::move(text)),\n                         [this](const ActivityResult&) { requestUpdate(); });\n}\n\nvoid EpubReaderActivity::openFootnotesList(const bool wholeBook, const bool returnToMenu) {\n  const auto& notes = wholeBook ? bookFootnotes : currentPageFootnotes;\n  if (notes.empty()) {\n    if (returnToMenu) openReaderMenu();\n    return;\n  }\n  const int sourceSpine = currentSpineIndex;\n  startActivityForResult(std::make_unique<EpubReaderFootnotesActivity>(renderer, mappedInput, notes),\n                         [this, wholeBook, returnToMenu, sourceSpine](const ActivityResult& result) {\n                           if (result.isCancelled) {\n                             if (returnToMenu) openReaderMenu();\n                             else requestUpdate();\n                             return;\n                           }\n                           const auto& selected = std::get<FootnoteResult>(result.data);\n                           FootnoteEntry note;\n                           std::strncpy(note.href, selected.href.c_str(), sizeof(note.href) - 1);\n                           note.href[sizeof(note.href) - 1] = '\\0';\n                           const auto& source = wholeBook ? bookFootnotes : currentPageFootnotes;\n                           auto it = std::find_if(source.begin(), source.end(), [&](const FootnoteEntry& e) { return selected.href == e.href; });\n                           if (it != source.end()) note = *it;\n                           std::string text = extractFootnoteText(note.href, sourceSpine);\n                           if (text.empty()) text = "A lábjegyzet szövege nem olvasható.";\n                           startActivityForResult(\n                               std::make_unique<FootnotePopupActivity>(renderer, mappedInput, note.number, std::move(text)),\n                               [this, wholeBook, returnToMenu](const ActivityResult&) { openFootnotesList(wholeBook, returnToMenu); });\n                         });\n}\n''',
)

# Physical footnote button: show popup for one, list+popup for many.
replace_once(
    "src/activities/reader/EpubReaderActivity.cpp",
    '''      if (currentPageFootnotes.size() == 1) {\n        navigateToHref(currentPageFootnotes[0].href, true);\n      } else if (currentPageFootnotes.size() > 1) {\n        startActivityForResult(\n            std::make_unique<EpubReaderFootnotesActivity>(renderer, mappedInput, currentPageFootnotes),\n            [this](const ActivityResult& result) {\n              if (!result.isCancelled) {\n                const auto& footnoteResult = std::get<FootnoteResult>(result.data);\n                navigateToHref(footnoteResult.href, true);\n              }\n              requestUpdate();\n            });\n      }''',
    '''      if (currentPageFootnotes.size() == 1) {\n        openFootnotePopup(currentPageFootnotes[0], currentSpineIndex);\n      } else if (currentPageFootnotes.size() > 1) {\n        openFootnotesList(false, false);\n      }''',
)

# Reader-menu Footnotes = all book footnotes, not just current page, and selection opens popup.
replace_once(
    "src/activities/reader/EpubReaderActivity.cpp",
    '''    case EpubReaderMenuActivity::MenuAction::FOOTNOTES: {\n      startActivityForResult(std::make_unique<EpubReaderFootnotesActivity>(renderer, mappedInput, currentPageFootnotes),\n                             [this](const ActivityResult& result) {\n                               if (result.isCancelled) {\n                                 openReaderMenu();\n                                 return;\n                               }\n                               const auto& footnoteResult = std::get<FootnoteResult>(result.data);\n                               navigateToHref(footnoteResult.href, true);\n                               requestUpdate();\n                             });\n      break;\n    }''',
    '''    case EpubReaderMenuActivity::MenuAction::FOOTNOTES: {\n      ensureBookFootnotes();\n      openFootnotesList(true, true);\n      break;\n    }''',
)

# Build identity.
replace_once(
    "src/CPHUNBuildId.h",
    '#define CPHUN_BUILD_ID "CPHUN-260917-135R4A-EXP"',
    '#define CPHUN_BUILD_ID "CPHUN-260917-135R4B-EXP"',
)

print("CPHUN-135r4b applied: points 4/5 + footnotes + fn layout + tips + dictionary truncation")
