from pathlib import Path


def replace_once(path: str, old: str, new: str) -> None:
    p = Path(path)
    text = p.read_text(encoding="utf-8")
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"Expected one match in {path}, found {count}")
    p.write_text(text.replace(old, new, 1), encoding="utf-8")


def replace_all(path: str, old: str, new: str, expected: int) -> None:
    p = Path(path)
    text = p.read_text(encoding="utf-8")
    count = text.count(old)
    if count != expected:
        raise SystemExit(f"Expected {expected} matches in {path}, found {count}")
    p.write_text(text.replace(old, new), encoding="utf-8")


replace_once("src/CPHUNBuildId.h", "CPHUN-260910-88", "CPHUN-260910-89")
replace_once("lib/Epub/Epub/Section.cpp", "constexpr uint8_t SECTION_FILE_VERSION = 54;",
             "constexpr uint8_t SECTION_FILE_VERSION = 55;")

# 1) Párbeszéd fix: protect exactly one space after leading dialogue/list marker.
parsed = Path("lib/Epub/Epub/ParsedText.cpp")
text = parsed.read_text(encoding="utf-8")
anchor = '''bool isStandaloneDialogueDash(const std::string& word) {\n  if (word.empty()) return false;\n  const uint32_t first = firstCodepoint(word);\n  return (first == 0x2013 || first == 0x2014) && first == lastCodepoint(word);\n}\n'''
insert = anchor + '''\n// CPHUN-89: fixed-width leading marker spacing. Besides the existing dialogue\n// dash, protect one source space after common paragraph-leading list markers:\n// 1. / 12. / 1) / 12) / a) / bullet.\nbool isAsciiDigitsToken(const std::string& token) {\n  if (token.empty()) return false;\n  for (const unsigned char c : token)\n    if (c < '0' || c > '9') return false;\n  return true;\n}\n\nbool isSingleAsciiAlphaToken(const std::string& token) {\n  return token.size() == 1 &&\n         ((token[0] >= 'a' && token[0] <= 'z') || (token[0] >= 'A' && token[0] <= 'Z'));\n}\n\ntemplate <typename WordContainer>\nbool isFixedLeadingMarkerBoundary(const WordContainer& tokens, const size_t boundary) {\n  if (boundary == 1 && !tokens.empty()) {\n    if (isStandaloneDialogueDash(tokens[0])) return true;\n    const uint32_t cp = firstCodepoint(tokens[0]);\n    if (cp == 0x2022 && cp == lastCodepoint(tokens[0])) return true;\n  }\n  if (boundary == 2 && tokens.size() >= 2) {\n    const std::string& leader = tokens[0];\n    const std::string& suffix = tokens[1];\n    if ((suffix == "." && isAsciiDigitsToken(leader)) ||\n        (suffix == ")" && (isAsciiDigitsToken(leader) || isSingleAsciiAlphaToken(leader)))) {\n      return true;\n    }\n  }\n  return false;\n}\n'''
if text.count(anchor) != 1:
    raise SystemExit("Could not insert CPHUN-89 leading-marker helper")
parsed.write_text(text.replace(anchor, insert, 1), encoding="utf-8")

replace_once(
    "lib/Epub/Epub/ParsedText.cpp",
    '''  // Dialogue typography: when a paragraph begins with a standalone en/em dash,\n  // keep the following normal source space fixed-width and non-breaking. In the\n  // token boundary model continues=true/noSpace=false is exactly that: a regular\n  // space is drawn, but it is neither a line-break opportunity nor a justify gap.\n  if (fixedDialogueSpacing && words.size() == 1 && !attachToPrevious) {\n    const uint32_t first = firstCodepoint(words.front());\n    if ((first == 0x2013 || first == 0x2014) && first == lastCodepoint(words.front())) {\n      effectiveAttachToPrevious = true;\n    }\n  }\n''',
    '''  // CPHUN-89: keep exactly one source space after a paragraph-leading\n  // dialogue/list marker fixed-width and non-breaking.\n  if (fixedDialogueSpacing && !attachToPrevious &&\n      isFixedLeadingMarkerBoundary(words, words.size())) {\n    effectiveAttachToPrevious = true;\n  }\n''',
)
replace_all("lib/Epub/Epub/ParsedText.cpp",
            "fixedDialogueSpacing && j == 1 && isStandaloneDialogueDash(words[0])",
            "fixedDialogueSpacing && isFixedLeadingMarkerBoundary(words, j)", 1)
replace_all("lib/Epub/Epub/ParsedText.cpp",
            "fixedDialogueSpacing && currentIndex == 1 && isStandaloneDialogueDash(words[0])",
            "fixedDialogueSpacing && isFixedLeadingMarkerBoundary(words, currentIndex)", 1)
replace_all("lib/Epub/Epub/ParsedText.cpp",
            "fixedDialogueSpacing && boundaryIdx == 1 && isStandaloneDialogueDash(lineWords[0])",
            "fixedDialogueSpacing && lastBreakAt == 0 && isFixedLeadingMarkerBoundary(lineWords, wordIdx)", 2)
replace_all("lib/Epub/Epub/ParsedText.cpp",
            "fixedDialogueSpacing && lastBreakAt == 0 && wordIdx == 0 && isStandaloneDialogueDash(lineWords[0])",
            "fixedDialogueSpacing && lastBreakAt == 0 && isFixedLeadingMarkerBoundary(lineWords, wordIdx + 1)", 1)

# 2) Result type for the compact dictionary choice screen.
replace_once("src/activities/ActivityResult.h",
             '''struct KeyboardResult {\n  std::string text;\n};\n''',
             '''struct KeyboardResult {\n  std::string text;\n};\n\nstruct DictionaryHeadwordResult {\n  std::string headword;\n};\n''')
replace_once("src/activities/ActivityResult.h",
             '''    std::variant<std::monostate, WifiResult, KeyboardResult, MenuResult, ChapterResult, PercentResult, IntervalResult,\n                 PageResult, ProgressChangeResult, NetworkModeResult, FootnoteResult, FilePathResult>;''',
             '''    std::variant<std::monostate, WifiResult, KeyboardResult, DictionaryHeadwordResult, MenuResult, ChapterResult,\n                 PercentResult, IntervalResult, PageResult, ProgressChangeResult, NetworkModeResult, FootnoteResult,\n                 FilePathResult>;''')

# 3) Exact multi-candidate probing through one shared dictionary session.
replace_once("src/util/Dictionary.h",
             '''  bool lookup(const char* word, std::string& definitionOut, std::string& matchedHeadwordOut,\n              LookupResult* outResult = nullptr);\n\n  static std::string cleanWord(const char* word);\n''',
             '''  bool lookup(const char* word, std::string& definitionOut, std::string& matchedHeadwordOut,\n              LookupResult* outResult = nullptr);\n\n  // Probe context candidates using one .idx/.qidx session. True means the scan\n  // completed, even when there are no hits. Only exact headwords are returned;\n  // synonyms and stemming are intentionally excluded.\n  bool findExactHeadwords(const std::vector<std::string>& candidates, std::vector<std::string>& matches,\n                          LookupResult* outResult = nullptr);\n\n  static std::string cleanWord(const char* word);\n''')
replace_once("src/util/Dictionary.cpp",
             '''bool Dictionary::lookup(const char* word, std::string& definitionOut, std::string& matchedHeadwordOut,\n                        LookupResult* outResult) {\n''',
             '''bool Dictionary::findExactHeadwords(const std::vector<std::string>& candidates, std::vector<std::string>& matches,\n                                        LookupResult* outResult) {\n  const auto setResult = [outResult](LookupResult r) {\n    if (outResult) *outResult = r;\n  };\n  setResult(LookupResult::NotFound);\n  matches.clear();\n  if (!isOpen()) {\n    setResult(LookupResult::ReadError);\n    return false;\n  }\n\n  LookupSession session;\n  if (!openSession(session)) {\n    setResult(LookupResult::ReadError);\n    return false;\n  }\n\n  for (const auto& candidate : candidates) {\n    const std::string cleaned = cleanWord(candidate.c_str());\n    if (cleaned.empty()) continue;\n    std::string matched;\n    const DictLocation location = locate(session, cleaned.c_str(), &matched);\n    if (location.readError) {\n      setResult(LookupResult::ReadError);\n      return false;\n    }\n    if (!location.found) continue;\n    if (std::find(matches.begin(), matches.end(), matched) == matches.end())\n      matches.push_back(std::move(matched));\n  }\n\n  setResult(matches.empty() ? LookupResult::NotFound : LookupResult::Found);\n  return true;\n}\n\nbool Dictionary::lookup(const char* word, std::string& definitionOut, std::string& matchedHeadwordOut,\n                        LookupResult* outResult) {\n''')

# 4) Preserve the underlying TextBlock/token index for punctuation-aware lookup.
replace_once("src/activities/reader/DictionaryWordSelectActivity.h",
             '''    const char* text;\n    EpdFontFamily::Style style;\n''',
             '''    const char* text;\n    const TextBlock* block;\n    uint16_t tokenIndex;\n    EpdFontFamily::Style style;\n''')

# 5) Compact selectable headword list. Definitions are not retained here.
Path("src/activities/reader/DictionaryMatchSelectActivity.h").write_text(r'''#pragma once

#include <string>
#include <vector>

#include "activities/UiListActivity.h"

class DictionaryMatchSelectActivity final : public UiListActivity {
 public:
  DictionaryMatchSelectActivity(GfxRenderer& renderer, MappedInputManager& mappedInput,
                                std::vector<std::string> headwords);

 private:
  int listCount() const override { return static_cast<int>(headwords.size()); }
  void buildScreen(UiScreen& screen) override;
  void activateIndex(int index) override;
  const char* headerTitle() const override { return "Szótári találatok"; }

  std::vector<std::string> headwords;
  std::vector<freeink::ui::ListItem> rows;
};
''', encoding="utf-8")
Path("src/activities/reader/DictionaryMatchSelectActivity.cpp").write_text(r'''#include "DictionaryMatchSelectActivity.h"

#include "activities/ActivityResult.h"
#include "components/UITheme.h"

namespace fui = freeink::ui;

DictionaryMatchSelectActivity::DictionaryMatchSelectActivity(GfxRenderer& renderer, MappedInputManager& mappedInput,
                                                             std::vector<std::string> headwords)
    : UiListActivity("DictionaryMatchSelect", renderer, mappedInput), headwords(std::move(headwords)) {
  rows.resize(this->headwords.size());
  for (size_t i = 0; i < this->headwords.size(); ++i) {
    rows[i].label = this->headwords[i].c_str();
    rows[i].actionValue = static_cast<int16_t>(i);
  }
}

void DictionaryMatchSelectActivity::buildScreen(UiScreen& screen) {
  const auto& metrics = UITheme::getInstance().getMetrics();
  const Rect safe = UITheme::getInstance().getScreenSafeArea(renderer, true, false);
  screen.setContentMargin(fui::Insets{static_cast<int16_t>(safe.y + metrics.topPadding + metrics.headerHeight),
                                      static_cast<int16_t>(renderer.getScreenWidth() - (safe.x + safe.width)),
                                      static_cast<int16_t>(renderer.getScreenHeight() - (safe.y + safe.height)),
                                      static_cast<int16_t>(safe.x)});
  screen.spacer(static_cast<int16_t>(metrics.verticalSpacing));
  if (rows.empty()) return;
  fui::ListProps props;
  props.count = static_cast<uint16_t>(rows.size());
  props.items = rows.data();
  props.action = ACTION_ROW;
  props.inputMask = fui::InputTouch;
  syncListViewport(screen, props);
  screen.list(props);
}

void DictionaryMatchSelectActivity::activateIndex(const int index) {
  if (index < 0 || index >= static_cast<int>(headwords.size())) return;
  app.clearTapFlash();
  setResult(DictionaryHeadwordResult{headwords[index]});
  finish();
}
''', encoding="utf-8")

replace_once("src/activities/reader/DictionaryWordSelectActivity.cpp",
             '''#include <cctype>\n''', '''#include <algorithm>\n#include <cctype>\n''')
replace_once("src/activities/reader/DictionaryWordSelectActivity.cpp",
             '''#include <cstdlib>\n''', '''#include <cstdlib>\n#include <cstring>\n''')
replace_once("src/activities/reader/DictionaryWordSelectActivity.cpp",
             '''#include "DictionaryDefinitionActivity.h"\n''',
             '''#include "DictionaryDefinitionActivity.h"\n#include "DictionaryMatchSelectActivity.h"\n''')
replace_once("src/activities/reader/DictionaryWordSelectActivity.cpp",
             '''void indexBuildYield(void*) { vTaskDelay(1); }\n''',
             '''bool isExplicitHyphenToken(const char* text) {\n  return std::strcmp(text, "-") == 0 || std::strcmp(text, "\\xE2\\x80\\x90") == 0 ||\n         std::strcmp(text, "\\xE2\\x80\\x91") == 0 || std::strcmp(text, "\\xE2\\x80\\x92") == 0 ||\n         std::strcmp(text, "\\xE2\\x80\\x93") == 0 || std::strcmp(text, "\\xE2\\x80\\x94") == 0;\n}\n\nvoid appendUnique(std::vector<std::string>& items, std::string value) {\n  if (!value.empty() && std::find(items.begin(), items.end(), value) == items.end())\n    items.push_back(std::move(value));\n}\n\nvoid indexBuildYield(void*) { vTaskDelay(1); }\n''')
replace_once("src/activities/reader/DictionaryWordSelectActivity.cpp",
             '''      box.row = rowCount;\n      box.text = text;\n      words.push_back(box);\n''',
             '''      box.row = rowCount;\n      box.text = text;\n      box.block = block.get();\n      box.tokenIndex = i;\n      words.push_back(box);\n''')

old_lookup = '''  std::string definition;\n  std::string headword;\n  Dictionary::LookupResult result = Dictionary::LookupResult::NotFound;\n  bool found = false;\n\n  // CPHUN-88: prefer a two-token exact phrase beginning at the selected word.\n  // Dictionary::lookup() already tries exact lookup before stemming, so a\n  // dictionary headword such as "formális logika" wins over "formális".\n  if (ok && selected + 1 < static_cast<int>(words.size()) &&\n      words[selected].row == words[selected + 1].row) {\n    const std::string phrase = std::string(words[selected].text) + " " + words[selected + 1].text;\n    found = dict.lookup(phrase.c_str(), definition, headword, &result);\n    if (!found && result != Dictionary::LookupResult::NotFound) {\n      // A real SD/decompression/OOM failure must not be hidden by a second\n      // lookup that happens to miss or succeed.\n      ok = false;\n    }\n  }\n  if (ok && !found) {\n    definition.clear();\n    headword.clear();\n    result = Dictionary::LookupResult::NotFound;\n    found = dict.lookup(words[selected].text, definition, headword, &result);\n  }\n\n  if (found) {\n    popup = Popup::None;\n    startActivityForResult(\n        std::make_unique<DictionaryDefinitionActivity>(renderer, mappedInput, std::move(headword),\n                                                       std::move(definition), dict.definitionsAreHtml()),\n        [this](const ActivityResult&) { requestUpdate(); });\n    return;\n  }\n'''
new_lookup = '''  std::string definition;\n  std::string headword;\n  Dictionary::LookupResult result = Dictionary::LookupResult::NotFound;\n\n  // CPHUN-89: selected word first. Exact context headwords are alternatives.\n  const bool found = ok && dict.lookup(words[selected].text, definition, headword, &result);\n\n  if (found) {\n    std::vector<std::string> candidates;\n    candidates.reserve(10);\n\n    // Restore a hyphenated orthographic unit from hidden punctuation tokens.\n    const WordBox& current = words[selected];\n    if (current.block) {\n      const TextBlock* block = current.block;\n      int start = current.tokenIndex;\n      int end = current.tokenIndex;\n      if (start >= 2 && isExplicitHyphenToken(block->wordText(start - 1)) &&\n          isSelectableToken(block->wordText(start - 2)))\n        start -= 2;\n      if (end + 2 < block->wordCount() && isExplicitHyphenToken(block->wordText(end + 1)) &&\n          isSelectableToken(block->wordText(end + 2)))\n        end += 2;\n      if (start != end) {\n        std::string compound;\n        for (int i = start; i <= end; ++i) compound += block->wordText(i);\n        appendUnique(candidates, std::move(compound));\n      }\n    }\n\n    // Search a bounded +/-2 selectable-token window. Space-separated phrases\n    // are only formed across directly adjacent source tokens in the same row;\n    // punctuation therefore cannot be silently discarded.\n    const int first = std::max(0, selected - 2);\n    const int last = std::min(static_cast<int>(words.size()) - 1, selected + 2);\n    for (int left = first; left <= selected; ++left) {\n      for (int right = selected; right <= last; ++right) {\n        if (left == right) continue;\n        bool contiguous = true;\n        for (int i = left; i < right; ++i) {\n          if (words[i].row != words[i + 1].row || words[i].block != words[i + 1].block ||\n              words[i].tokenIndex + 1 != words[i + 1].tokenIndex) {\n            contiguous = false;\n            break;\n          }\n        }\n        if (!contiguous) continue;\n        std::string phrase;\n        for (int i = left; i <= right; ++i) {\n          if (!phrase.empty()) phrase.push_back(' ');\n          phrase += words[i].text;\n        }\n        appendUnique(candidates, std::move(phrase));\n      }\n    }\n\n    std::vector<std::string> exactMatches;\n    Dictionary::LookupResult contextResult = Dictionary::LookupResult::NotFound;\n    if (!candidates.empty()) dict.findExactHeadwords(candidates, exactMatches, &contextResult);\n\n    std::vector<std::string> choices;\n    choices.reserve(1 + exactMatches.size());\n    appendUnique(choices, headword);\n    for (auto& match : exactMatches) appendUnique(choices, std::move(match));\n\n    popup = Popup::None;\n    if (choices.size() == 1) {\n      startActivityForResult(\n          std::make_unique<DictionaryDefinitionActivity>(renderer, mappedInput, std::move(headword),\n                                                         std::move(definition), dict.definitionsAreHtml()),\n          [this](const ActivityResult&) { requestUpdate(); });\n      return;\n    }\n\n    const std::string primaryHeadword = headword;\n    startActivityForResult(\n        std::make_unique<DictionaryMatchSelectActivity>(renderer, mappedInput, std::move(choices)),\n        [this, primaryHeadword, primaryDefinition = std::move(definition)](const ActivityResult& choiceResult) mutable {\n          if (choiceResult.isCancelled) {\n            requestUpdate();\n            return;\n          }\n          const auto* choice = std::get_if<DictionaryHeadwordResult>(&choiceResult.data);\n          if (!choice) {\n            requestUpdate();\n            return;\n          }\n\n          std::string chosenDefinition;\n          std::string chosenHeadword;\n          if (choice->headword == primaryHeadword) {\n            chosenHeadword = primaryHeadword;\n            chosenDefinition = std::move(primaryDefinition);\n          } else {\n            Dictionary::LookupResult chosenResult = Dictionary::LookupResult::NotFound;\n            if (!dict.lookup(choice->headword.c_str(), chosenDefinition, chosenHeadword, &chosenResult)) {\n              popup = Popup::Error;\n              popupMsg = chosenResult == Dictionary::LookupResult::LowMemory\n                             ? StrId::STR_DICT_LOW_MEMORY\n                             : (chosenResult == Dictionary::LookupResult::Decompress\n                                    ? StrId::STR_DICT_DECOMPRESS_ERROR\n                                    : StrId::STR_DICT_READ_FAILED);\n              popupTime = millis();\n              requestUpdate();\n              return;\n            }\n          }\n\n          startActivityForResult(\n              std::make_unique<DictionaryDefinitionActivity>(renderer, mappedInput, std::move(chosenHeadword),\n                                                             std::move(chosenDefinition), dict.definitionsAreHtml()),\n              [this](const ActivityResult&) { requestUpdate(); });\n        });\n    return;\n  }\n'''
replace_once("src/activities/reader/DictionaryWordSelectActivity.cpp", old_lookup, new_lookup)

print("CPHUN-89 dictionary/list-spacing patch applied")
