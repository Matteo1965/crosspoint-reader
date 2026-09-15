from pathlib import Path


def replace_once(path, old, new):
    path = Path(path)
    text = path.read_text(encoding="utf-8")
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"CPHUN-132: {path}: expected one match, found {count}: {old[:140]!r}")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


def insert_before(path, marker, addition):
    replace_once(path, marker, addition + marker)


def insert_after(path, marker, addition):
    replace_once(path, marker, marker + addition)


# -----------------------------------------------------------------------------
# Stable, markup-independent per-word anchors
# -----------------------------------------------------------------------------
replace_once(
    "lib/Epub/Epub/blocks/TextBlock.h",
    "  std::unique_ptr<uint8_t[]> arena;\n",
    "  std::unique_ptr<uint8_t[]> arena;\n  // CPHUN-132: exact visible Unicode-codepoint offset in the spine for each word.\n  const uint32_t* visibleOffsetArr = nullptr;\n",
)
replace_once(
    "lib/Epub/Epub/blocks/TextBlock.h",
    '''  explicit TextBlock(const std::vector<std::string>& words, const std::vector<int16_t>& wordXpos,
                     const std::vector<EpdFontFamily::Style>& wordStyles, const std::vector<uint8_t>& focusBoundary,
                     const std::vector<uint16_t>& focusSuffixX, const BlockStyle& blockStyle = BlockStyle(),
                     std::vector<std::string> rubyTexts = {}, uint8_t letterSpacingPx = 0);''',
    '''  explicit TextBlock(const std::vector<std::string>& words, const std::vector<int16_t>& wordXpos,
                     const std::vector<EpdFontFamily::Style>& wordStyles,
                     const std::vector<uint32_t>& wordVisibleOffsets, const std::vector<uint8_t>& focusBoundary,
                     const std::vector<uint16_t>& focusSuffixX, const BlockStyle& blockStyle = BlockStyle(),
                     std::vector<std::string> rubyTexts = {}, uint8_t letterSpacingPx = 0);''',
)
insert_before(
    "lib/Epub/Epub/blocks/TextBlock.h",
    "  int16_t wordXpos(const uint16_t i) const { return xposArr[i]; }\n",
    "  uint32_t wordVisibleTextOffset(const uint16_t i) const { return visibleOffsetArr[i]; }\n",
)

replace_once(
    "lib/Epub/Epub/blocks/TextBlock.cpp",
    '''  size_t size =
      static_cast<size_t>(wordCount) * (sizeof(uint16_t) + sizeof(int16_t) + sizeof(uint8_t) + sizeof(uint8_t));''',
    '''  size_t size = static_cast<size_t>(wordCount) *
                (sizeof(uint32_t) + sizeof(uint16_t) + sizeof(int16_t) + sizeof(uint8_t) + sizeof(uint8_t));''',
)
replace_once(
    "lib/Epub/Epub/blocks/TextBlock.cpp",
    '''  textOffArr = reinterpret_cast<const uint16_t*>(base);
  xposArr = reinterpret_cast<const int16_t*>(base + wc * 2);
  size_t off = wc * 4;''',
    '''  visibleOffsetArr = reinterpret_cast<const uint32_t*>(base);
  size_t off = wc * sizeof(uint32_t);
  textOffArr = reinterpret_cast<const uint16_t*>(base + off);
  off += wc * sizeof(uint16_t);
  xposArr = reinterpret_cast<const int16_t*>(base + off);
  off += wc * sizeof(int16_t);''',
)
replace_once(
    "lib/Epub/Epub/blocks/TextBlock.cpp",
    '''TextBlock::TextBlock(const std::vector<std::string>& words, const std::vector<int16_t>& wordXpos,
                     const std::vector<EpdFontFamily::Style>& wordStyles, const std::vector<uint8_t>& focusBoundary,
                     const std::vector<uint16_t>& focusSuffixX, const BlockStyle& blockStyle,
                     std::vector<std::string> rubyTexts, const uint8_t letterSpacingPx)''',
    '''TextBlock::TextBlock(const std::vector<std::string>& words, const std::vector<int16_t>& wordXpos,
                     const std::vector<EpdFontFamily::Style>& wordStyles,
                     const std::vector<uint32_t>& wordVisibleOffsets, const std::vector<uint8_t>& focusBoundary,
                     const std::vector<uint16_t>& focusSuffixX, const BlockStyle& blockStyle,
                     std::vector<std::string> rubyTexts, const uint8_t letterSpacingPx)''',
)
replace_once(
    "lib/Epub/Epub/blocks/TextBlock.cpp",
    '''  if (words.size() != wordXpos.size() || words.size() != wordStyles.size() || words.size() > 10000 ||
      (hasFocus && (words.size() != focusBoundary.size() || words.size() != focusSuffixX.size()))) {''',
    '''  if (words.size() != wordXpos.size() || words.size() != wordStyles.size() ||
      words.size() != wordVisibleOffsets.size() || words.size() > 10000 ||
      (hasFocus && (words.size() != focusBoundary.size() || words.size() != focusSuffixX.size()))) {''',
)
insert_before(
    "lib/Epub/Epub/blocks/TextBlock.cpp",
    "  auto* textOff = const_cast<uint16_t*>(textOffArr);\n",
    "  auto* visibleOffsets = const_cast<uint32_t*>(visibleOffsetArr);\n",
)
insert_before(
    "lib/Epub/Epub/blocks/TextBlock.cpp",
    "    textOff[i] = off;\n",
    "    visibleOffsets[i] = wordVisibleOffsets[i];\n",
)

insert_after(
    "lib/Epub/Epub/ParsedText.cpp",
    '''  std::vector<EpdFontFamily::Style> lineWordStyles;
  lineWordStyles.reserve(lineWordCount);
''',
    '''  std::vector<uint32_t> lineWordVisibleOffsets;
  lineWordVisibleOffsets.reserve(lineWordCount);
''',
)
insert_after(
    "lib/Epub/Epub/ParsedText.cpp",
    "    lineWordStyles.push_back(wordStyles[lastBreakAt + i]);\n",
    "    lineWordVisibleOffsets.push_back(visibleOffsetAt(lastBreakAt + i));\n",
)
insert_after(
    "lib/Epub/Epub/ParsedText.cpp",
    "    reorderedFocusBoundaryScratch.reserve(visualOrderScratch.size());\n",
    '''    std::vector<uint32_t> reorderedVisibleOffsets;
    reorderedVisibleOffsets.reserve(visualOrderScratch.size());
''',
)
insert_after(
    "lib/Epub/Epub/ParsedText.cpp",
    "      const uint16_t src = visualOrderScratch[i];\n",
    "      reorderedVisibleOffsets.push_back(lineWordVisibleOffsets[src]);\n",
)
insert_after(
    "lib/Epub/Epub/ParsedText.cpp",
    '''    lineWords.swap(reorderedWordsScratch);
    lineWordStyles.swap(reorderedStylesScratch);
''',
    "    lineWordVisibleOffsets.swap(reorderedVisibleOffsets);\n",
)
replace_once(
    "lib/Epub/Epub/ParsedText.cpp",
    '''    auto block = std::make_shared<TextBlock>(lineWords, lineXPos, lineWordStyles, std::vector<uint8_t>{},
                                             std::vector<uint16_t>{}, blockStyle, std::move(lineRubyTexts), letterSpacingPx);''',
    '''    auto block = std::make_shared<TextBlock>(lineWords, lineXPos, lineWordStyles, lineWordVisibleOffsets,
                                             std::vector<uint8_t>{}, std::vector<uint16_t>{}, blockStyle,
                                             std::move(lineRubyTexts), letterSpacingPx);''',
)
replace_once(
    "lib/Epub/Epub/ParsedText.cpp",
    '''  auto block = std::make_shared<TextBlock>(lineWords, lineXPos, lineWordStyles, outBoundaries, outSuffixX, blockStyle,
                                           std::move(lineRubyTexts));''',
    '''  auto block = std::make_shared<TextBlock>(lineWords, lineXPos, lineWordStyles, lineWordVisibleOffsets,
                                           outBoundaries, outSuffixX, blockStyle, std::move(lineRubyTexts));''',
)

replace_once(
    "lib/Epub/Epub/Section.cpp",
    "constexpr uint8_t SECTION_FILE_VERSION = 56;",
    "constexpr uint8_t SECTION_FILE_VERSION = 57;",
)

# -----------------------------------------------------------------------------
# Highlight result payload and reusable word-selection mode
# -----------------------------------------------------------------------------
insert_after(
    "src/activities/ActivityResult.h",
    '''struct DictionaryHeadwordResult {
  std::string headword;
};
''',
    '''
struct HighlightResult {
  int spineIndex = 0;
  uint32_t visibleTextOffset = 0;
  uint16_t length = 0;
  std::string text;
};
''',
)
replace_once(
    "src/activities/ActivityResult.h",
    '''    std::variant<std::monostate, WifiResult, KeyboardResult, DictionaryHeadwordResult, MenuResult, ChapterResult,
                 PercentResult, IntervalResult, PageResult, ProgressChangeResult, NetworkModeResult, FootnoteResult,
                 FilePathResult>;''',
    '''    std::variant<std::monostate, WifiResult, KeyboardResult, DictionaryHeadwordResult, HighlightResult, MenuResult,
                 ChapterResult, PercentResult, IntervalResult, PageResult, ProgressChangeResult, NetworkModeResult,
                 FootnoteResult, FilePathResult>;''',
)

Path("src/highlights").mkdir(parents=True, exist_ok=True)
Path("src/highlights/HighlightMode.h").write_text(r'''#pragma once

enum class WordSelectionMode : unsigned char {
  Dictionary = 0,
  Highlight = 1,
};
''', encoding="utf-8")

Path("src/highlights/HighlightStore.h").write_text(r'''#pragma once

#include <cstdint>
#include <string>
#include <vector>

struct HighlightAnchor {
  int spineIndex = 0;
  uint32_t visibleTextOffset = 0;
  uint16_t length = 0;
  std::string text;
};

class HighlightStore {
 public:
  explicit HighlightStore(std::string bookPath);
  bool load();
  bool save() const;
  bool contains(const HighlightAnchor& anchor) const;
  bool add(const HighlightAnchor& anchor);
  const std::vector<HighlightAnchor>& items() const { return highlights_; }

 private:
  std::string filePath_;
  std::vector<HighlightAnchor> highlights_;
};
''', encoding="utf-8")

Path("src/highlights/HighlightStore.cpp").write_text(r'''#include "HighlightStore.h"

#include <ArduinoJson.h>
#include <HalStorage.h>
#include <PersistableStore.h>

#include <algorithm>

namespace {
constexpr char HIGHLIGHT_DIR[] = "/.crosspoint/highlights/";

std::string pathForBook(std::string bookPath) {
  if (!bookPath.empty() && bookPath.front() == '/') bookPath.erase(0, 1);
  std::replace(bookPath.begin(), bookPath.end(), '/', '_');
  std::replace(bookPath.begin(), bookPath.end(), '\\', '_');
  const size_t lastDot = bookPath.find_last_of('.');
  if (lastDot != std::string::npos) bookPath.erase(lastDot);
  return std::string(HIGHLIGHT_DIR) + bookPath + ".json";
}

bool sameAnchor(const HighlightAnchor& a, const HighlightAnchor& b) {
  return a.spineIndex == b.spineIndex && a.visibleTextOffset == b.visibleTextOffset;
}
}  // namespace

HighlightStore::HighlightStore(std::string bookPath) : filePath_(pathForBook(std::move(bookPath))) {}

bool HighlightStore::load() {
  highlights_.clear();
  if (!Storage.exists(filePath_.c_str())) return true;
  JsonDocument doc;
  if (!PersistableStoreBase::readDocFromFile(filePath_.c_str(), doc)) return false;
  for (JsonObject item : doc["highlights"].as<JsonArray>()) {
    HighlightAnchor anchor;
    anchor.spineIndex = item["spine"] | 0;
    anchor.visibleTextOffset = item["offset"] | static_cast<uint32_t>(0);
    anchor.length = item["length"] | static_cast<uint16_t>(0);
    anchor.text = item["text"] | "";
    highlights_.push_back(std::move(anchor));
  }
  return true;
}

bool HighlightStore::save() const {
  JsonDocument doc;
  JsonArray arr = doc["highlights"].to<JsonArray>();
  for (const auto& anchor : highlights_) {
    JsonObject item = arr.add<JsonObject>();
    item["spine"] = anchor.spineIndex;
    item["offset"] = anchor.visibleTextOffset;
    item["length"] = anchor.length;
    item["text"] = anchor.text;
  }
  Storage.mkdir(HIGHLIGHT_DIR);
  return PersistableStoreBase::writeDocToFile(filePath_.c_str(), doc);
}

bool HighlightStore::contains(const HighlightAnchor& anchor) const {
  return std::any_of(highlights_.begin(), highlights_.end(),
                     [&](const HighlightAnchor& item) { return sameAnchor(item, anchor); });
}

bool HighlightStore::add(const HighlightAnchor& anchor) {
  if (contains(anchor)) return true;
  highlights_.push_back(anchor);
  if (save()) return true;
  highlights_.pop_back();
  return false;
}
''', encoding="utf-8")

Path("src/activities/reader/DictionaryHighlightPromptActivity.h").write_text(r'''#pragma once

#include <string>

#include "activities/Activity.h"
#include "activities/ActivityResult.h"

class DictionaryHighlightPromptActivity final : public Activity {
 public:
  DictionaryHighlightPromptActivity(GfxRenderer& renderer, MappedInputManager& mappedInput,
                                    std::string firstLine, HighlightResult highlight)
      : Activity("DictionaryHighlightPrompt", renderer, mappedInput),
        firstLine(std::move(firstLine)),
        highlight(std::move(highlight)) {}

  void loop() override;
  void render(RenderLock&&) override;
  bool appliesNightMode() const override { return true; }

 private:
  std::string firstLine;
  HighlightResult highlight;
};
''', encoding="utf-8")

Path("src/activities/reader/DictionaryHighlightPromptActivity.cpp").write_text(r'''#include "DictionaryHighlightPromptActivity.h"

#include <GfxRenderer.h>

#include "MappedInputManager.h"
#include "components/UITheme.h"
#include "fontIds.h"

void DictionaryHighlightPromptActivity::loop() {
  if (mappedInput.wasReleased(MappedInputManager::Button::Back)) {
    ActivityResult result;
    result.isCancelled = true;
    setResult(std::move(result));
    finish();
    return;
  }
  if (mappedInput.wasReleased(MappedInputManager::Button::Confirm)) {
    setResult(highlight);
    finish();
  }
}

void DictionaryHighlightPromptActivity::render(RenderLock&&) {
  renderer.clearScreen();
  const int centerY = renderer.getScreenHeight() / 2 - 25;
  renderer.drawCenteredText(NOTOSANS_14_FONT_ID, centerY, firstLine.c_str(), true, EpdFontFamily::REGULAR);
  renderer.drawCenteredText(NOTOSANS_14_FONT_ID, centerY + 34, "A kijelölt szó kiemelhető.", true,
                            EpdFontFamily::REGULAR);
  const auto labels = mappedInput.mapLabels("Vissza", "Kiemelés", "", "");
  GUI.drawButtonHints(renderer, labels.btn1, labels.btn2, labels.btn3, labels.btn4);
  renderer.displayBuffer(HalDisplay::FAST_REFRESH);
}
''', encoding="utf-8")

replace_once(
    "src/activities/reader/DictionaryDefinitionActivity.h",
    "#include <memory>\n",
    "#include <memory>\n#include <optional>\n",
)
replace_once(
    "src/activities/reader/DictionaryDefinitionActivity.h",
    '''                                        std::string definition, bool htmlDefinition = false,
                                        bool manualSearchMode = false)''',
    '''                                        std::string definition, bool htmlDefinition = false,
                                        bool manualSearchMode = false,
                                        std::optional<HighlightResult> highlight = std::nullopt)''',
)
replace_once(
    "src/activities/reader/DictionaryDefinitionActivity.h",
    '''        htmlDefinition(htmlDefinition),
        manualSearchMode(manualSearchMode) {}''',
    '''        htmlDefinition(htmlDefinition),
        manualSearchMode(manualSearchMode),
        highlight(std::move(highlight)) {}''',
)
insert_after(
    "src/activities/reader/DictionaryDefinitionActivity.h",
    "  const bool manualSearchMode;\n",
    "  const std::optional<HighlightResult> highlight;\n",
)
replace_once(
    "src/activities/reader/DictionaryDefinitionActivity.cpp",
    '''  if (manualSearchMode && mappedInput.wasReleased(MappedInputManager::Button::Confirm)) {
    finish();
    return;
  }''',
    '''  if (mappedInput.wasReleased(MappedInputManager::Button::Confirm)) {
    if (manualSearchMode) {
      finish();
      return;
    }
    if (highlight.has_value()) {
      setResult(*highlight);
      finish();
      return;
    }
  }''',
)
replace_once(
    "src/activities/reader/DictionaryDefinitionActivity.cpp",
    '''  const auto labels = mappedInput.mapLabels(
      tr(STR_BACK), manualSearchMode ? "Billentyűzet" : "", (currentPage > 0 ? "<" : ""),
      (currentPage + 1 < totalPages ? ">" : ""));''',
    '''  const auto labels = mappedInput.mapLabels(
      tr(STR_BACK), manualSearchMode ? "Billentyűzet" : (highlight.has_value() ? "Kiemelés" : ""),
      (currentPage > 0 ? "<" : ""), (currentPage + 1 < totalPages ? ">" : ""));''',
)

insert_after(
    "src/activities/reader/DictionaryWordSelectActivity.h",
    '#include "activities/Activity.h"\n',
    '#include "highlights/HighlightMode.h"\n',
)
replace_once(
    "src/activities/reader/DictionaryWordSelectActivity.h",
    '''  explicit DictionaryWordSelectActivity(GfxRenderer& renderer, MappedInputManager& mappedInput,
                                        std::unique_ptr<Page> page, int marginLeft, int marginTop)
      : Activity("DictionaryWordSelect", renderer, mappedInput),
        page(std::move(page)),
        marginLeft(marginLeft),
        marginTop(marginTop) {}''',
    '''  explicit DictionaryWordSelectActivity(GfxRenderer& renderer, MappedInputManager& mappedInput,
                                        std::unique_ptr<Page> page, int marginLeft, int marginTop,
                                        int spineIndex, WordSelectionMode mode = WordSelectionMode::Dictionary)
      : Activity("DictionaryWordSelect", renderer, mappedInput),
        page(std::move(page)),
        marginLeft(marginLeft),
        marginTop(marginTop),
        spineIndex(spineIndex),
        mode(mode) {}''',
)
insert_after(
    "src/activities/reader/DictionaryWordSelectActivity.h",
    "  void performLookup();\n",
    "  HighlightResult makeHighlightResult() const;\n  void finishWithHighlight();\n  void showHighlightPrompt(bool noDictionary);\n",
)
insert_after(
    "src/activities/reader/DictionaryWordSelectActivity.h",
    "  const int marginTop;\n",
    "  const int spineIndex;\n  const WordSelectionMode mode;\n",
)

insert_after(
    "src/activities/reader/DictionaryWordSelectActivity.cpp",
    '#include "CrossPointSettings.h"\n',
    '#include "DictionaryHighlightPromptActivity.h"\n',
)
insert_after(
    "src/activities/reader/DictionaryWordSelectActivity.cpp",
    "void indexBuildYield(void*) { vTaskDelay(1); }\n",
    '''
uint16_t visibleCodepointLength(const char* text) {
  if (!text) return 0;
  const auto* p = reinterpret_cast<const uint8_t*>(text);
  uint16_t count = 0;
  while (*p && count != UINT16_MAX) {
    utf8NextCodepoint(&p);
    ++count;
  }
  return count;
}
''',
)
insert_after(
    "src/activities/reader/DictionaryWordSelectActivity.cpp",
    "#include <Memory.h>\n",
    "#include <Utf8.h>\n",
)
insert_before(
    "src/activities/reader/DictionaryWordSelectActivity.cpp",
    "void DictionaryWordSelectActivity::performLookup() {\n",
    '''HighlightResult DictionaryWordSelectActivity::makeHighlightResult() const {
  if (words.empty()) return {};
  const WordBox& word = words[selected];
  HighlightResult result;
  result.spineIndex = spineIndex;
  result.visibleTextOffset = word.block ? word.block->wordVisibleTextOffset(word.tokenIndex) : page->visibleTextOffset;
  result.length = visibleCodepointLength(word.text);
  result.text = word.text ? word.text : "";
  return result;
}

void DictionaryWordSelectActivity::finishWithHighlight() {
  setResult(makeHighlightResult());
  finish();
}

void DictionaryWordSelectActivity::showHighlightPrompt(const bool noDictionary) {
  popup = Popup::None;
  snapshotIdx = -1;
  startActivityForResult(
      std::make_unique<DictionaryHighlightPromptActivity>(
          renderer, mappedInput, noDictionary ? "Nincs szótár beállítva." : "Nincs találat a szótárban.",
          makeHighlightResult()),
      [this](const ActivityResult& result) {
        if (!result.isCancelled) {
          if (const auto* highlight = std::get_if<HighlightResult>(&result.data)) {
            setResult(*highlight);
            finish();
            return;
          }
        }
        requestUpdate();
      });
}

''',
)
insert_after(
    "src/activities/reader/DictionaryWordSelectActivity.cpp",
    "void DictionaryWordSelectActivity::performLookup() {\n",
    '''  if (SETTINGS.dictionaryName[0] == '\\0') {
    showHighlightPrompt(true);
    return;
  }
''',
)
replace_once(
    "src/activities/reader/DictionaryWordSelectActivity.cpp",
    '''          std::make_unique<DictionaryDefinitionActivity>(renderer, mappedInput, std::move(headword),
                                                         std::move(definition), dict.definitionsAreHtml()),
          [this](const ActivityResult&) { requestUpdate(); });''',
    '''          std::make_unique<DictionaryDefinitionActivity>(renderer, mappedInput, std::move(headword),
                                                         std::move(definition), dict.definitionsAreHtml(), false,
                                                         makeHighlightResult()),
          [this](const ActivityResult& result) {
            if (!result.isCancelled) {
              if (const auto* highlight = std::get_if<HighlightResult>(&result.data)) {
                setResult(*highlight);
                finish();
                return;
              }
            }
            requestUpdate();
          });''',
)
replace_once(
    "src/activities/reader/DictionaryWordSelectActivity.cpp",
    '''              std::make_unique<DictionaryDefinitionActivity>(renderer, mappedInput, std::move(chosenHeadword),
                                                             std::move(chosenDefinition), dict.definitionsAreHtml()),
              [this](const ActivityResult&) { requestUpdate(); });''',
    '''              std::make_unique<DictionaryDefinitionActivity>(renderer, mappedInput, std::move(chosenHeadword),
                                                             std::move(chosenDefinition), dict.definitionsAreHtml(),
                                                             false, makeHighlightResult()),
              [this](const ActivityResult& result) {
                if (!result.isCancelled) {
                  if (const auto* highlight = std::get_if<HighlightResult>(&result.data)) {
                    setResult(*highlight);
                    finish();
                    return;
                  }
                }
                requestUpdate();
              });''',
)
replace_once(
    "src/activities/reader/DictionaryWordSelectActivity.cpp",
    '''      case Dictionary::LookupResult::NotFound:
      default:
        popup = Popup::NotFound;
        popupMsg = StrId::STR_DICT_NOT_FOUND;
        break;
    }
  }
  popupTime = millis();
  requestUpdate();''',
    '''      case Dictionary::LookupResult::NotFound:
      default:
        showHighlightPrompt(false);
        return;
    }
  }
  popupTime = millis();
  requestUpdate();''',
)
replace_once(
    "src/activities/reader/DictionaryWordSelectActivity.cpp",
    '''  if (mappedInput.wasReleased(MappedInputManager::Button::Confirm) && !words.empty()) {
    performLookup();
    return;
  }''',
    '''  if (mappedInput.wasReleased(MappedInputManager::Button::Confirm) && !words.empty()) {
    if (mode == WordSelectionMode::Highlight)
      finishWithHighlight();
    else
      performLookup();
    return;
  }''',
)
replace_once(
    "src/activities/reader/DictionaryWordSelectActivity.cpp",
    '''    if (hit >= 0) {
      selected = hit;
      performLookup();
    }''',
    '''    if (hit >= 0) {
      selected = hit;
      if (mode == WordSelectionMode::Highlight)
        finishWithHighlight();
      else
        performLookup();
    }''',
)
replace_once(
    "src/activities/reader/DictionaryWordSelectActivity.cpp",
    '''  const auto labels = mappedInput.mapDirectionalLabels(tr(STR_BACK), tr(STR_LOOKUP), tr(STR_DIR_LEFT),
                                                       tr(STR_DIR_RIGHT), tr(STR_DIR_UP), tr(STR_DIR_DOWN));''',
    '''  const auto labels = mappedInput.mapDirectionalLabels(
      tr(STR_BACK), mode == WordSelectionMode::Highlight ? "Kiemelés" : tr(STR_LOOKUP), tr(STR_DIR_LEFT),
      tr(STR_DIR_RIGHT), tr(STR_DIR_UP), tr(STR_DIR_DOWN));''',
)

Path("src/highlights/HighlightRenderer.h").write_text(r'''#pragma once

class GfxRenderer;
class Page;
class HighlightStore;

class HighlightRenderer {
 public:
  static void render(GfxRenderer& renderer, const Page& page, int fontId, int xOffset, int yOffset,
                     int spineIndex, const HighlightStore& store);
};
''', encoding="utf-8")

Path("src/highlights/HighlightRenderer.cpp").write_text(r'''#include "HighlightRenderer.h"

#include <Epub/Page.h>
#include <GfxRenderer.h>

#include "HighlightStore.h"

void HighlightRenderer::render(GfxRenderer& renderer, const Page& page, const int fontId, const int xOffset,
                               const int yOffset, const int spineIndex, const HighlightStore& store) {
  const int lineHeight = renderer.getLineHeight(fontId);
  const int ascender = renderer.getFontAscenderSize(fontId);
  for (const auto& element : page.elements) {
    if (element->getTag() != TAG_PageLine) continue;
    const auto& line = static_cast<const PageLine&>(*element);
    const auto& block = line.getBlock();
    if (!block || !block->valid()) continue;
    const int rubyShift = block->getRubyShift(ascender);
    for (uint16_t i = 0; i < block->wordCount(); ++i) {
      HighlightAnchor anchor;
      anchor.spineIndex = spineIndex;
      anchor.visibleTextOffset = block->wordVisibleTextOffset(i);
      if (!store.contains(anchor)) continue;
      const int x = xOffset + line.xPos + block->wordXpos(i);
      const int width = renderer.getTextAdvanceX(fontId, block->wordText(i), block->wordStyle(i));
      const int y = yOffset + line.yPos + rubyShift + lineHeight - 2;
      renderer.drawLine(x, y, x + width, y, 2, true);
    }
  }
}
''', encoding="utf-8")

replace_once(
    "src/activities/reader/EpubReaderMenuActivity.h",
    '''    DELETE_CACHE,
    DICTIONARY,
    MANUAL_DICTIONARY_SEARCH,''',
    '''    DELETE_CACHE,
    DICTIONARY,
    HIGHLIGHT,
    MANUAL_DICTIONARY_SEARCH,''',
)
insert_after(
    "src/activities/reader/EpubReaderMenuActivity.cpp",
    '  items.push_back({MenuAction::DICTIONARY, StrId::STR_LOOKUP, "Szótári keresés"});\n',
    '  items.push_back({MenuAction::HIGHLIGHT, StrId::STR_LOOKUP, "Kiemelés"});\n',
)

insert_after(
    "src/activities/reader/EpubReaderActivity.h",
    '#include "components/OptionPopup.h"\n',
    '#include "highlights/HighlightMode.h"\n#include "highlights/HighlightStore.h"\n',
)
insert_after(
    "src/activities/reader/EpubReaderActivity.h",
    "  std::shared_ptr<Epub> epub;\n",
    "  std::unique_ptr<HighlightStore> highlightStore;\n",
)
replace_once(
    "src/activities/reader/EpubReaderActivity.h",
    "  void openDictionaryWordSelect();\n",
    "  void openDictionaryWordSelect(WordSelectionMode mode = WordSelectionMode::Dictionary);\n",
)

insert_after(
    "src/activities/reader/EpubReaderActivity.cpp",
    '#include "util/ScreenshotUtil.h"\n',
    '#include "highlights/HighlightRenderer.h"\n',
)
insert_before(
    "src/activities/reader/EpubReaderActivity.cpp",
    "  loadCachedBookmarks();\n  return true;\n",
    '''  highlightStore = std::make_unique<HighlightStore>(epub->getPath());
  highlightStore->load();
''',
)
replace_once(
    "src/activities/reader/EpubReaderActivity.cpp",
    '''void EpubReaderActivity::openDictionaryWordSelect() {
  if (SETTINGS.dictionaryName[0] == '\\0') {
    showDictionaryMessage = true;
    dictionaryMessageTime = millis();
    requestUpdate();
    return;
  }
  if (!section) return;''',
    '''void EpubReaderActivity::openDictionaryWordSelect(const WordSelectionMode mode) {
  if (!section) return;''',
)
replace_once(
    "src/activities/reader/EpubReaderActivity.cpp",
    '''  startActivityForResult(std::make_unique<DictionaryWordSelectActivity>(renderer, mappedInput, std::move(page),
                                                                        orientedMarginLeft, orientedMarginTop),
                         [this](const ActivityResult&) { requestUpdate(); });''',
    '''  const std::string highlightBookPath = epub->getPath();
  // CPHUN-132r1: the dictionary index/lookup path is memory-sensitive. The
  // highlight list is persisted already, so release its heap while the word
  // selector/dictionary owns the foreground, then reload it on return.
  highlightStore.reset();
  startActivityForResult(
      std::make_unique<DictionaryWordSelectActivity>(renderer, mappedInput, std::move(page), orientedMarginLeft,
                                                     orientedMarginTop, currentSpineIndex, mode),
      [this, highlightBookPath](const ActivityResult& result) {
        highlightStore = std::make_unique<HighlightStore>(highlightBookPath);
        highlightStore->load();
        if (!result.isCancelled) {
          if (const auto* selected = std::get_if<HighlightResult>(&result.data)) {
            if (highlightStore) {
              highlightStore->add({selected->spineIndex, selected->visibleTextOffset, selected->length, selected->text});
            }
          }
        }
        requestUpdate();
      });''',
)
insert_after(
    "src/activities/reader/EpubReaderActivity.cpp",
    '''    case EpubReaderMenuActivity::MenuAction::DICTIONARY: {
      openDictionaryWordSelect();
      break;
    }
''',
    '''    case EpubReaderMenuActivity::MenuAction::HIGHLIGHT: {
      openDictionaryWordSelect(WordSelectionMode::Highlight);
      break;
    }
''',
)
insert_after(
    "src/activities/reader/EpubReaderActivity.cpp",
    '''  page->render(renderer, fontId, orientedMarginLeft, orientedMarginTop);
  renderStatusBar();
  const auto tBwRender = millis();''',
    '''
  if (highlightStore) {
    HighlightRenderer::render(renderer, *page, fontId, orientedMarginLeft, orientedMarginTop,
                              currentSpineIndex, *highlightStore);
  }
''',
)

replace_once(
    "src/CPHUNBuildId.h",
    '#define CPHUN_BUILD_ID "CPHUN-260915-131-EXP"',
    '#define CPHUN_BUILD_ID "CPHUN-260915-132-EXP"',
)

print("CPHUN-132 word highlights patch applied")
