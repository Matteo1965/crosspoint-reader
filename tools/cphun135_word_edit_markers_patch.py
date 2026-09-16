from pathlib import Path
import re


def replace_once(path, old, new):
    p = Path(path)
    text = p.read_text(encoding="utf-8")
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"CPHUN-135: {path}: expected one match, found {count}: {old[:180]!r}")
    p.write_text(text.replace(old, new, 1), encoding="utf-8")


def insert_after(path, marker, addition):
    replace_once(path, marker, marker + addition)


def insert_before(path, marker, addition):
    replace_once(path, marker, addition + marker)


# -----------------------------------------------------------------------------
# 1) Editing is a third use of the existing word selector.
# -----------------------------------------------------------------------------
replace_once(
    "src/highlights/HighlightMode.h",
    "  Dictionary = 0,\n  Highlight = 1,\n",
    "  Dictionary = 0,\n  Highlight = 1,\n  Edit = 2,\n",
)

# Reuse the exact stable anchor payload already produced by the selector.
replace_once(
    "src/activities/reader/DictionaryWordSelectActivity.cpp",
    "    if (mode == WordSelectionMode::Highlight)\n      finishWithHighlight();\n    else\n      performLookup();",
    "    if (mode == WordSelectionMode::Highlight || mode == WordSelectionMode::Edit)\n      finishWithHighlight();\n    else\n      performLookup();",
)
replace_once(
    "src/activities/reader/DictionaryWordSelectActivity.cpp",
    "      if (mode == WordSelectionMode::Highlight)\n        finishWithHighlight();\n      else\n        performLookup();",
    "      if (mode == WordSelectionMode::Highlight || mode == WordSelectionMode::Edit)\n        finishWithHighlight();\n      else\n        performLookup();",
)
replace_once(
    "src/activities/reader/DictionaryWordSelectActivity.cpp",
    '''  const auto labels = mappedInput.mapDirectionalLabels(
      tr(STR_BACK), mode == WordSelectionMode::Highlight ? "Megjelölés" : tr(STR_LOOKUP), tr(STR_DIR_LEFT),
      tr(STR_DIR_RIGHT), tr(STR_DIR_UP), tr(STR_DIR_DOWN));''',
    '''  const char* confirmLabel = mode == WordSelectionMode::Highlight
                                 ? "Megjelölés"
                                 : (mode == WordSelectionMode::Edit ? "Szerkesztés" : tr(STR_LOOKUP));
  const auto labels = mappedInput.mapDirectionalLabels(
      tr(STR_BACK), confirmLabel, tr(STR_DIR_LEFT), tr(STR_DIR_RIGHT), tr(STR_DIR_UP), tr(STR_DIR_DOWN));''',
)

# -----------------------------------------------------------------------------
# 2) Separate edit store. EPUB content itself remains untouched.
# -----------------------------------------------------------------------------
Path("src/highlights/TextEditStore.h").write_text(r'''#pragma once

#include <cstdint>
#include <string>
#include <vector>

struct TextEditAnchor {
  int spineIndex = 0;
  uint32_t visibleTextOffset = 0;
  uint16_t length = 0;
  std::string originalText;
  std::string replacementText;
};

class TextEditStore {
 public:
  explicit TextEditStore(std::string bookPath);
  bool load();
  bool save() const;
  const TextEditAnchor* find(int spineIndex, uint32_t visibleTextOffset) const;
  bool upsert(const TextEditAnchor& edit);
  const std::vector<TextEditAnchor>& items() const { return edits_; }

 private:
  std::string filePath_;
  std::vector<TextEditAnchor> edits_;
};
''', encoding="utf-8")

Path("src/highlights/TextEditStore.cpp").write_text(r'''#include "TextEditStore.h"

#include <ArduinoJson.h>
#include <HalStorage.h>
#include <PersistableStore.h>

#include <algorithm>

namespace {
constexpr char EDIT_DIR[] = "/.crosspoint/edits/";

std::string pathForBook(std::string bookPath) {
  if (!bookPath.empty() && bookPath.front() == '/') bookPath.erase(0, 1);
  std::replace(bookPath.begin(), bookPath.end(), '/', '_');
  std::replace(bookPath.begin(), bookPath.end(), '\\', '_');
  const size_t lastDot = bookPath.find_last_of('.');
  if (lastDot != std::string::npos) bookPath.erase(lastDot);
  return std::string(EDIT_DIR) + bookPath + ".json";
}
}  // namespace

TextEditStore::TextEditStore(std::string bookPath) : filePath_(pathForBook(std::move(bookPath))) {}

bool TextEditStore::load() {
  edits_.clear();
  if (!Storage.exists(filePath_.c_str())) return true;
  JsonDocument doc;
  if (!PersistableStoreBase::readDocFromFile(filePath_.c_str(), doc)) return false;
  for (JsonObject item : doc["edits"].as<JsonArray>()) {
    TextEditAnchor edit;
    edit.spineIndex = item["spine"] | 0;
    edit.visibleTextOffset = item["offset"] | static_cast<uint32_t>(0);
    edit.length = item["length"] | static_cast<uint16_t>(0);
    edit.originalText = item["original"] | "";
    edit.replacementText = item["replacement"] | "";
    edits_.push_back(std::move(edit));
  }
  return true;
}

bool TextEditStore::save() const {
  JsonDocument doc;
  JsonArray arr = doc["edits"].to<JsonArray>();
  for (const auto& edit : edits_) {
    JsonObject item = arr.add<JsonObject>();
    item["spine"] = edit.spineIndex;
    item["offset"] = edit.visibleTextOffset;
    item["length"] = edit.length;
    item["original"] = edit.originalText;
    item["replacement"] = edit.replacementText;
  }
  Storage.mkdir(EDIT_DIR);
  return PersistableStoreBase::writeDocToFile(filePath_.c_str(), doc);
}

const TextEditAnchor* TextEditStore::find(const int spineIndex, const uint32_t visibleTextOffset) const {
  const auto it = std::find_if(edits_.begin(), edits_.end(), [&](const TextEditAnchor& edit) {
    return edit.spineIndex == spineIndex && edit.visibleTextOffset == visibleTextOffset;
  });
  return it == edits_.end() ? nullptr : &*it;
}

bool TextEditStore::upsert(const TextEditAnchor& edit) {
  auto it = std::find_if(edits_.begin(), edits_.end(), [&](const TextEditAnchor& item) {
    return item.spineIndex == edit.spineIndex && item.visibleTextOffset == edit.visibleTextOffset;
  });
  if (it == edits_.end()) {
    edits_.push_back(edit);
    if (save()) return true;
    edits_.pop_back();
    return false;
  }
  const TextEditAnchor old = *it;
  *it = edit;
  if (save()) return true;
  *it = old;
  return false;
}
''', encoding="utf-8")

# -----------------------------------------------------------------------------
# 3) Edited-word marker: lightest non-white gray behind the existing word.
#    GfxRenderer::fillRectDither(..., Color::LightGray) is the renderer's
#    orientation-aware LightGray path. Text/layout metrics stay unchanged.
# -----------------------------------------------------------------------------
Path("src/highlights/TextEditRenderer.h").write_text(r'''#pragma once

class GfxRenderer;
class Page;
class TextEditStore;

class TextEditRenderer {
 public:
  static void renderBackground(GfxRenderer& renderer, const Page& page, int fontId, int xOffset, int yOffset,
                               int spineIndex, const TextEditStore& store);
};
''', encoding="utf-8")

Path("src/highlights/TextEditRenderer.cpp").write_text(r'''#include "TextEditRenderer.h"

#include <Epub/Page.h>
#include <GfxRenderer.h>

#include "TextEditStore.h"

void TextEditRenderer::renderBackground(GfxRenderer& renderer, const Page& page, const int fontId, const int xOffset,
                                        const int yOffset, const int spineIndex, const TextEditStore& store) {
  const int lineHeight = renderer.getLineHeight(fontId);
  const int ascender = renderer.getFontAscenderSize(fontId);
  for (const auto& element : page.elements) {
    if (element->getTag() != TAG_PageLine) continue;
    const auto& line = static_cast<const PageLine&>(*element);
    const auto& block = line.getBlock();
    if (!block || !block->valid()) continue;
    const int rubyShift = block->getRubyShift(ascender);
    for (uint16_t i = 0; i < block->wordCount(); ++i) {
      if (!store.find(spineIndex, block->wordVisibleTextOffset(i))) continue;
      const int x = xOffset + line.xPos + block->wordXpos(i);
      const int width = renderer.getTextAdvanceX(fontId, block->wordText(i), block->wordStyle(i));
      const int y = yOffset + line.yPos + rubyShift;
      if (width > 0 && lineHeight > 0) renderer.fillRectDither(x, y, width, lineHeight, Color::LightGray);
    }
  }
}
''', encoding="utf-8")

# -----------------------------------------------------------------------------
# 4) Reader menu: Szerkesztés directly after Megjelölés.
# -----------------------------------------------------------------------------
replace_once(
    "src/activities/reader/EpubReaderMenuActivity.h",
    "    DICTIONARY,\n    HIGHLIGHT,\n    MANUAL_DICTIONARY_SEARCH,",
    "    DICTIONARY,\n    HIGHLIGHT,\n    EDIT,\n    MANUAL_DICTIONARY_SEARCH,",
)
replace_once(
    "src/activities/reader/EpubReaderMenuActivity.cpp",
    '  items.push_back({MenuAction::HIGHLIGHT, StrId::STR_LOOKUP, "Megjelölés"});\n',
    '  items.push_back({MenuAction::HIGHLIGHT, StrId::STR_LOOKUP, "Megjelölés"});\n'
    '  items.push_back({MenuAction::EDIT, StrId::STR_LOOKUP, "Szerkesztés"});\n',
)

# -----------------------------------------------------------------------------
# 5) Reader ownership + deferred keyboard transition.
# -----------------------------------------------------------------------------
insert_after(
    "src/activities/reader/EpubReaderActivity.h",
    '#include "components/OptionPopup.h"\n',
    '#include "highlights/TextEditStore.h"\n',
)
insert_after(
    "src/activities/reader/EpubReaderActivity.h",
    "  std::unique_ptr<HighlightStore> highlightStore;\n",
    "  std::unique_ptr<TextEditStore> textEditStore;\n  std::optional<HighlightResult> pendingEditSelection;\n",
)
insert_after(
    "src/activities/reader/EpubReaderActivity.h",
    "  void openDictionaryWordSelect(WordSelectionMode mode = WordSelectionMode::Dictionary);\n",
    "  void openEditKeyboard(HighlightResult selection);\n",
)

insert_after(
    "src/activities/reader/EpubReaderActivity.cpp",
    '#include "highlights/HighlightRenderer.h"\n',
    '#include "highlights/TextEditRenderer.h"\n#include "activities/util/KeyboardEntryActivity.h"\n',
)

# Load the per-book edit store alongside the existing highlight store.
insert_after(
    "src/activities/reader/EpubReaderActivity.cpp",
    '''  highlightStore = std::make_unique<HighlightStore>(epub->getPath());
  highlightStore->load();
''',
    '''  textEditStore = std::make_unique<TextEditStore>(epub->getPath());
  textEditStore->load();
''',
)

# The selector callback must not turn an edit into a highlight. Queue keyboard
# launch and let the parent Activity loop unwind before starting the next child.
p = Path("src/activities/reader/EpubReaderActivity.cpp")
s = p.read_text(encoding="utf-8")
s2, n = re.subn(
    r'\[this, highlightBookPath\]\(const ActivityResult& result\) \{\n'
    r'(\s*highlightStore = std::make_unique<HighlightStore>\(highlightBookPath\);\n'
    r'\s*highlightStore->load\(\);\n'
    r'\s*if \(!result\.isCancelled\) \{\n'
    r'\s*if \(const auto\* selected = std::get_if<HighlightResult>\(&result\.data\)\) \{\n)'
    r'(\s*if \(highlightStore\) \{)',
    r'[this, highlightBookPath, mode](const ActivityResult& result) {\n\1'
    r'            if (mode == WordSelectionMode::Edit) {\n'
    r'              pendingEditSelection = *selected;\n'
    r'              requestUpdate();\n'
    r'              return;\n'
    r'            }\n\2',
    s,
    count=1,
    flags=re.MULTILINE,
)
if n != 1:
    raise SystemExit(f"CPHUN-135: selector callback edit routing patch failed: {n}")
p.write_text(s2, encoding="utf-8")

# Start the keyboard from the next normal loop turn, never from the child result callback.
replace_once(
    "src/activities/reader/EpubReaderActivity.cpp",
    "void EpubReaderActivity::loop() {\n",
    '''void EpubReaderActivity::loop() {
  if (pendingEditSelection) {
    HighlightResult selection = std::move(*pendingEditSelection);
    pendingEditSelection.reset();
    openEditKeyboard(std::move(selection));
    return;
  }
''',
)

# KeyboardEntryActivity explicitly accepts initialText in its constructor. If
# this anchor was edited earlier, preload the previous replacement; otherwise
# preload the selected original word.
insert_before(
    "src/activities/reader/EpubReaderActivity.cpp",
    "void EpubReaderActivity::openDictionaryWordSelect(const WordSelectionMode mode) {\n",
    r'''void EpubReaderActivity::openEditKeyboard(HighlightResult selection) {
  if (!epub) return;
  if (!textEditStore) {
    textEditStore = std::make_unique<TextEditStore>(epub->getPath());
    textEditStore->load();
  }
  std::string initialText = selection.text;
  if (textEditStore) {
    if (const auto* old = textEditStore->find(selection.spineIndex, selection.visibleTextOffset)) {
      if (!old->replacementText.empty()) initialText = old->replacementText;
    }
  }

  startActivityForResult(
      std::make_unique<KeyboardEntryActivity>(renderer, mappedInput, "Szerkesztés", initialText, 0, InputType::Text),
      [this, selection = std::move(selection)](const ActivityResult& result) {
        if (!result.isCancelled) {
          if (const auto* keyboard = std::get_if<KeyboardResult>(&result.data)) {
            if (!keyboard->text.empty() && textEditStore) {
              textEditStore->upsert({selection.spineIndex, selection.visibleTextOffset, selection.length,
                                     selection.text, keyboard->text});
            }
          }
        }
        requestUpdate();
      });
}

''',
)

# Reader menu entry point.
insert_after(
    "src/activities/reader/EpubReaderActivity.cpp",
    '''    case EpubReaderMenuActivity::MenuAction::HIGHLIGHT: {
      openDictionaryWordSelect(WordSelectionMode::Highlight);
      break;
    }
''',
    '''    case EpubReaderMenuActivity::MenuAction::EDIT: {
      openDictionaryWordSelect(WordSelectionMode::Edit);
      break;
    }
''',
)

# Draw marker background before normal page text. Existing highlight underline
# remains independent and is still drawn after page text.
insert_before(
    "src/activities/reader/EpubReaderActivity.cpp",
    "  page->render(renderer, fontId, orientedMarginLeft, orientedMarginTop);\n",
    '''  if (textEditStore) {
    TextEditRenderer::renderBackground(renderer, *page, fontId, orientedMarginLeft, orientedMarginTop,
                                       currentSpineIndex, *textEditStore);
  }
''',
)

# Make underline precede the status bar (background -> page text -> underline -> status).
p = Path("src/activities/reader/EpubReaderActivity.cpp")
s = p.read_text(encoding="utf-8")n = 0
pattern = re.compile(
    r'(  page->render\(renderer, fontId, orientedMarginLeft, orientedMarginTop\);\n)'
    r'  renderStatusBar\(\);\n'
    r'(  const auto tBwRender = millis\(\);\n\n'
    r'  if \(highlightStore\) \{\n'
    r'    HighlightRenderer::render\(renderer, \*page, fontId, orientedMarginLeft, orientedMarginTop,\n'
    r'\s*currentSpineIndex, \*highlightStore\);\n'
    r'  \}\n)'
)
m = pattern.search(s)
if m:
    block = m.group(1) + m.group(2)
    # Move only the underline block before status; keep timing marker after status.
    timing = "  const auto tBwRender = millis();\n"
    underline_start = m.group(2).find("  if (highlightStore)")
    underline = m.group(2)[underline_start:]
    replacement = m.group(1) + underline + "  renderStatusBar();\n" + timing
    s = s[:m.start()] + replacement + s[m.end():]
    n = 1
if n != 1:
    # The exact timing placement may evolve; the essential requirement remains
    # background-before-page and underline-after-page, so don't fail the build
    # solely on status-bar timing layout.
    print("CPHUN-135: note: status-bar/underline reorder pattern not found; preserving existing underline order")
p.write_text(s, encoding="utf-8")

# Build identity.
p = Path("src/CPHUNBuildId.h")
s = p.read_text(encoding="utf-8")
s2, n = re.subn(r'#define CPHUN_BUILD_ID "[^"]+"', '#define CPHUN_BUILD_ID "CPHUN-260916-135-EXP"', s, count=1)
if n != 1:
    raise SystemExit(f"CPHUN-135: build id replacement failed: {n}")
p.write_text(s2, encoding="utf-8")

print("CPHUN-135 word edit markers + deferred prefilled keyboard applied")
