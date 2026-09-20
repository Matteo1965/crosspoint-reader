from pathlib import Path
import re

def read(path):
    return Path(path).read_text(encoding="utf-8")

def write(path, text):
    Path(path).write_text(text, encoding="utf-8")

def rep(path, old, new, label):
    s = read(path)
    n = s.count(old)
    if n != 1:
        raise SystemExit(f"CPHUN-144 {label}: expected 1 match, found {n}")
    write(path, s.replace(old, new, 1))

# ---------------------------------------------------------------------------
# Popup typography/layout: 640 px, bold title, extra half-line title gap,
# justified body using the existing Hungarian Extended hyphenator.
# ---------------------------------------------------------------------------
p = "src/activities/reader/FootnotePopupActivity.cpp"
s = read(p)

if '#include <Epub/hyphenation/Hyphenator.h>' not in s:
    s = s.replace('#include <GfxRenderer.h>\n', '#include <GfxRenderer.h>\n#include <Epub/hyphenation/Hyphenator.h>\n', 1)

s = s.replace('constexpr int POPUP_HEIGHT = 600;', 'constexpr int POPUP_HEIGHT = 640;', 1)

wrap_pat = re.compile(r'void FootnotePopupActivity::wrapText\(\) \{.*?\n\}\n\nvoid FootnotePopupActivity::loop\(\)', re.S)
m = wrap_pat.search(s)
if not m:
    raise SystemExit("CPHUN-144 wrapText function not found")

wrap = r'''void FootnotePopupActivity::wrapText() {
  lines_.clear();
  lineJustified_.clear();

  // Reserve one contiguous block up front to reduce repeated small heap
  // reallocations while switching among footnotes.
  const size_t estimatedLines = std::min<size_t>(64, std::max<size_t>(8, text_.size() / 48 + 1));
  lines_.reserve(estimatedLines);
  lineJustified_.reserve(estimatedLines);

  const int maxWidth = renderer.getScreenWidth() - 2 * (POPUP_SIDE_MARGIN + POPUP_PADDING);
  const int fontId = NOTOSERIF_14_FONT_ID;

  auto replacementSuffix = [](const Hyphenator::Replacement replacement) -> const char* {
    switch (replacement) {
      case Hyphenator::Replacement::AppendY:
        return "y";
      case Hyphenator::Replacement::AppendZ:
        return "z";
      case Hyphenator::Replacement::AppendS:
        return "s";
      case Hyphenator::Replacement::AppendZS:
        return "zs";
      case Hyphenator::Replacement::None:
      default:
        return "";
    }
  };

  auto pushLine = [&](std::string&& value, const bool justify) {
    if (value.empty()) return;
    lines_.push_back(std::move(value));
    lineJustified_.push_back(justify ? 1 : 0);
  };

  std::string line;
  std::string word;
  line.reserve(96);
  word.reserve(48);

  auto fitHyphenatedPrefix = [&](const std::string& source, const int availableWidth,
                                 std::string& left, std::string& right) -> bool {
    const auto breaks = Hyphenator::breakOffsetsForLanguageExtended(source, false, "hu");
    for (auto it = breaks.rbegin(); it != breaks.rend(); ++it) {
      if (it->byteOffset == 0 || it->byteOffset >= source.size()) continue;
      std::string candidate = source.substr(0, it->byteOffset);
      candidate += replacementSuffix(it->replacement);
      if (it->requiresInsertedHyphen) candidate += "-";
      if (renderer.getTextAdvanceX(fontId, candidate.c_str(), EpdFontFamily::REGULAR) <= availableWidth) {
        left = std::move(candidate);
        right = source.substr(it->byteOffset);
        return true;
      }
    }
    return false;
  };

  auto placeWord = [&](std::string incoming) {
    while (!incoming.empty()) {
      if (line.empty()) {
        if (renderer.getTextAdvanceX(fontId, incoming.c_str(), EpdFontFamily::REGULAR) <= maxWidth) {
          line = std::move(incoming);
          return;
        }

        std::string left, right;
        if (fitHyphenatedPrefix(incoming, maxWidth, left, right)) {
          pushLine(std::move(left), false);
          incoming = std::move(right);
          continue;
        }

        // Unbreakable token: keep it intact rather than corrupting UTF-8.
        line = std::move(incoming);
        return;
      }

      const std::string candidate = line + " " + incoming;
      if (renderer.getTextAdvanceX(fontId, candidate.c_str(), EpdFontFamily::REGULAR) <= maxWidth) {
        line = candidate;
        return;
      }

      const int used = renderer.getTextAdvanceX(fontId, line.c_str(), EpdFontFamily::REGULAR);
      const int available =
          std::max(0, maxWidth - used - renderer.getSpaceWidth(fontId, EpdFontFamily::REGULAR));
      std::string left, right;
      if (available > 0 && fitHyphenatedPrefix(incoming, available, left, right)) {
        line += " ";
        line += left;
        pushLine(std::move(line), true);
        line.clear();
        incoming = std::move(right);
        continue;
      }

      pushLine(std::move(line), true);
      line.clear();
    }
  };

  auto flushWord = [&]() {
    if (word.empty()) return;
    placeWord(std::move(word));
    word.clear();
  };

  auto finishParagraph = [&]() {
    flushWord();
    if (!line.empty()) {
      pushLine(std::move(line), false);
      line.clear();
    }
  };

  for (char c : text_) {
    if (c == '\r') continue;
    if (c == '\n') {
      finishParagraph();
      continue;
    }
    if (std::isspace(static_cast<unsigned char>(c))) {
      flushWord();
    } else {
      word.push_back(c);
    }
  }
  finishParagraph();

  if (lines_.empty()) {
    lines_.push_back("–");
    lineJustified_.push_back(0);
  }
  firstLine_ = std::clamp(firstLine_, 0, std::max(0, static_cast<int>(lines_.size()) - 1));
}

void FootnotePopupActivity::loop()'''
s = s[:m.start()] + wrap + s[m.end():]

render_pat = re.compile(r'void FootnotePopupActivity::render\(RenderLock&&\) \{.*?\n\}\s*$', re.S)
m = render_pat.search(s)
if not m:
    raise SystemExit("CPHUN-144 popup render function not found")

render = r'''void FootnotePopupActivity::render(RenderLock&&) {
  const int screenW = renderer.getScreenWidth();
  const int screenH = renderer.getScreenHeight();
  const int popupW = screenW - 2 * POPUP_SIDE_MARGIN;
  const int popupH = std::min(POPUP_HEIGHT, screenH - 80);
  const int popupX = POPUP_SIDE_MARGIN;
  const int popupY = std::max(0, (screenH - popupH) / 2 - 40);

  renderer.fillRect(popupX, popupY, popupW, popupH, true);
  renderer.fillRect(popupX + 2, popupY + 2, popupW - 4, popupH - 4, false);

  const std::string title = label_.empty() ? "Lábjegyzet" : "Lábjegyzet {" + label_ + "}";
  renderer.drawText(NOTOSANS_14_FONT_ID, popupX + POPUP_PADDING, popupY + 12, title.c_str(), true,
                    EpdFontFamily::BOLD);

  const int lineHeight = renderer.getLineHeight(NOTOSERIF_14_FONT_ID);
  // CPHUN-144: keep an extra half line between the bold title and body.
  const int bodyTop = popupY + POPUP_HEADER_HEIGHT + 12 + lineHeight / 2;
  const int bodyBottom = popupY + popupH - 42;
  const int visibleLines = std::max(1, (bodyBottom - bodyTop) / std::max(1, lineHeight));
  const int textX = popupX + POPUP_PADDING;
  const int textWidth = popupW - 2 * POPUP_PADDING;

  auto drawBodyLine = [&](const std::string& line, const int y, const bool justify) {
    if (!justify) {
      renderer.drawText(NOTOSERIF_14_FONT_ID, textX, y, line.c_str(), true, EpdFontFamily::REGULAR);
      return;
    }

    int gaps = 0;
    for (char c : line) {
      if (c == ' ') ++gaps;
    }
    if (gaps <= 0) {
      renderer.drawText(NOTOSERIF_14_FONT_ID, textX, y, line.c_str(), true, EpdFontFamily::REGULAR);
      return;
    }

    std::string token;
    token.reserve(line.size());
    int wordsWidth = 0;
    for (size_t i = 0; i <= line.size(); ++i) {
      const char c = (i < line.size()) ? line[i] : ' ';
      if (c == ' ') {
        if (!token.empty()) {
          wordsWidth += renderer.getTextAdvanceX(NOTOSERIF_14_FONT_ID, token.c_str(), EpdFontFamily::REGULAR);
          token.clear();
        }
      } else {
        token.push_back(c);
      }
    }

    const int normalSpace = renderer.getSpaceWidth(NOTOSERIF_14_FONT_ID, EpdFontFamily::REGULAR);
    const int extra = std::max(0, textWidth - wordsWidth - gaps * normalSpace);
    const int extraPerGap = extra / gaps;
    int remainder = extra % gaps;

    int x = textX;
    token.clear();
    int gapIndex = 0;
    for (size_t i = 0; i <= line.size(); ++i) {
      const char c = (i < line.size()) ? line[i] : ' ';
      if (c == ' ') {
        if (!token.empty()) {
          renderer.drawText(NOTOSERIF_14_FONT_ID, x, y, token.c_str(), true, EpdFontFamily::REGULAR);
          x += renderer.getTextAdvanceX(NOTOSERIF_14_FONT_ID, token.c_str(), EpdFontFamily::REGULAR);
          token.clear();
          if (gapIndex < gaps) {
            x += normalSpace + extraPerGap + (remainder-- > 0 ? 1 : 0);
            ++gapIndex;
          }
        }
      } else {
        token.push_back(c);
      }
    }
  };

  int y = bodyTop;
  for (int i = 0; i < visibleLines && firstLine_ + i < static_cast<int>(lines_.size()); ++i) {
    const int lineIndex = firstLine_ + i;
    const bool justify = lineIndex < static_cast<int>(lineJustified_.size()) && lineJustified_[lineIndex] != 0;
    drawBodyLine(lines_[lineIndex], y, justify);
    y += lineHeight;
  }

  const bool canUp = firstLine_ > 0;
  const bool canDown = firstLine_ + visibleLines < static_cast<int>(lines_.size());
  const auto labels = mappedInput.mapLabels(
      canReturnToList_ ? "Vissza" : "", "Bezárás",
      canNavigateSiblings_ ? "Előző" : (canUp ? "Fel" : ""),
      canNavigateSiblings_ ? "Következő" : (canDown ? "Le" : ""));
  GUI.drawButtonHints(renderer, labels.btn1, labels.btn2, labels.btn3, labels.btn4);
  renderer.displayBuffer(HalDisplay::FAST_REFRESH);
}
'''
s = s[:m.start()] + render
write(p, s)

# Popup header: remember which wrapped lines are eligible for justification.
p = "src/activities/reader/FootnotePopupActivity.h"
s = read(p)
old = '''  std::string text_;
  std::vector<std::string> lines_;
  int firstLine_ = 0;'''
new = '''  std::string text_;
  std::vector<std::string> lines_;
  std::vector<uint8_t> lineJustified_;
  int firstLine_ = 0;'''
if s.count(old) != 1:
    raise SystemExit("CPHUN-144 popup header line storage anchor mismatch")
write(p, s.replace(old, new, 1))

# ---------------------------------------------------------------------------
# Reader: small fixed cache for extracted current-page footnote text + heap
# diagnostics. Fixed slots avoid another dynamically-growing vector.
# ---------------------------------------------------------------------------
p = "src/activities/reader/EpubReaderActivity.h"
s = read(p)
if '#include <array>' not in s:
    s = s.replace('#include <atomic>\n', '#include <array>\n#include <atomic>\n', 1)

old = '''  std::vector<FootnoteEntry> currentPageFootnotes;'''
new = '''  std::vector<FootnoteEntry> currentPageFootnotes;
  static constexpr size_t FOOTNOTE_TEXT_CACHE_SLOTS = 8;
  std::array<int, FOOTNOTE_TEXT_CACHE_SLOTS> footnoteTextCacheIndexes_ = {-1, -1, -1, -1, -1, -1, -1, -1};
  std::array<std::string, FOOTNOTE_TEXT_CACHE_SLOTS> footnoteTextCacheTexts_;
  int footnoteTextCacheSpine_ = -1;
  int footnoteTextCachePage_ = -1;
  const std::string& getCachedCurrentPageFootnoteText(int sourceSpineIndex, int noteIndex);'''
if s.count(old) != 1:
    raise SystemExit("CPHUN-144 currentPageFootnotes header anchor mismatch")
write(p, s.replace(old, new, 1))

p = "src/activities/reader/EpubReaderActivity.cpp"
s = read(p)

anchor = 'void EpubReaderActivity::openFootnotePopupSession('
pos = s.find(anchor)
if pos < 0:
    raise SystemExit("CPHUN-144 openFootnotePopupSession anchor not found")

helper = r'''const std::string& EpubReaderActivity::getCachedCurrentPageFootnoteText(const int sourceSpineIndex,
                                                                        const int noteIndex) {
  static const std::string empty;
  if (noteIndex < 0 || noteIndex >= static_cast<int>(currentPageFootnotes.size())) return empty;

  if (footnoteTextCacheSpine_ != sourceSpineIndex ||
      (section && footnoteTextCachePage_ != section->currentPage)) {
    footnoteTextCacheIndexes_.fill(-1);
    for (auto& text : footnoteTextCacheTexts_) text.clear();
    footnoteTextCacheSpine_ = sourceSpineIndex;
    footnoteTextCachePage_ = section ? section->currentPage : -1;
  }

  const size_t slot = static_cast<size_t>(noteIndex) % FOOTNOTE_TEXT_CACHE_SLOTS;
  if (footnoteTextCacheIndexes_[slot] == noteIndex && !footnoteTextCacheTexts_[slot].empty()) {
    LOG_DBG("FNT", "Cache hit note=%d heap=%u max=%u", noteIndex, static_cast<unsigned>(ESP.getFreeHeap()),
            static_cast<unsigned>(ESP.getMaxAllocHeap()));
    return footnoteTextCacheTexts_[slot];
  }

  LOG_INF("FNT", "Extract begin note=%d heap=%u max=%u", noteIndex, static_cast<unsigned>(ESP.getFreeHeap()),
          static_cast<unsigned>(ESP.getMaxAllocHeap()));
  std::string text = extractFootnoteText(currentPageFootnotes[noteIndex], sourceSpineIndex);
  if (text.empty()) text = "A lábjegyzet tartalma nem olvasható ebben az EPUB-ban.";
  footnoteTextCacheTexts_[slot] = std::move(text);
  footnoteTextCacheIndexes_[slot] = noteIndex;
  LOG_INF("FNT", "Extract end note=%d bytes=%u heap=%u max=%u", noteIndex,
          static_cast<unsigned>(footnoteTextCacheTexts_[slot].size()), static_cast<unsigned>(ESP.getFreeHeap()),
          static_cast<unsigned>(ESP.getMaxAllocHeap()));
  return footnoteTextCacheTexts_[slot];
}

'''
s = s[:pos] + helper + s[pos:]

# Current-page menu/session popup: cache extracted text.
old = '''  std::string text = extractFootnoteText(note, sourceSpineIndex);
  if (text.empty()) text = "A lábjegyzet tartalma nem olvasható ebben az EPUB-ban.";

  startActivityForResult(
      std::make_unique<FootnotePopupActivity>(renderer, mappedInput, note.number, std::move(text), true, count > 1),'''
new = '''  std::string text;
  if (!wholeBook) {
    text = getCachedCurrentPageFootnoteText(sourceSpineIndex, noteIndex);
  } else {
    text = extractFootnoteText(note, sourceSpineIndex);
    if (text.empty()) text = "A lábjegyzet tartalma nem olvasható ebben az EPUB-ban.";
  }

  startActivityForResult(
      std::make_unique<FootnotePopupActivity>(renderer, mappedInput, note.number, std::move(text), true, count > 1),'''
if s.count(old) < 1:
    raise SystemExit("CPHUN-144 menu popup cache anchor missing")
s = s.replace(old, new, 1)

# Shortcut popup: cache current-page text and Back goes directly to word selection.
old = '''  std::string text = extractFootnoteText(note, sourceSpineIndex);
  if (text.empty()) text = "A lábjegyzet tartalma nem olvasható ebben az EPUB-ban.";

  startActivityForResult(
      std::make_unique<FootnotePopupActivity>(renderer, mappedInput, note.number, std::move(text), true, count > 1),
      [this, mode, sourceSpineIndex, noteIndex](const ActivityResult& popupResult) {
        if (popupResult.isCancelled) {
          if (currentPageFootnotes.size() > 1) {
            openSearchFootnoteList(mode, sourceSpineIndex);  // Vissza -> list
          } else {
            openDictionaryWordSelect(mode);                  // single note: Vissza -> word selector
          }
          return;
        }'''
new = '''  std::string text = getCachedCurrentPageFootnoteText(sourceSpineIndex, noteIndex);

  startActivityForResult(
      std::make_unique<FootnotePopupActivity>(renderer, mappedInput, note.number, std::move(text), true, count > 1),
      [this, mode, sourceSpineIndex, noteIndex](const ActivityResult& popupResult) {
        if (popupResult.isCancelled) {
          openDictionaryWordSelect(mode);  // Shortcut: Vissza -> selected word mode, never the list.
          return;
        }'''
if s.count(old) != 1:
    raise SystemExit(f"CPHUN-144 shortcut popup anchor matches={s.count(old)}")
s = s.replace(old, new, 1)

# Shortcut entry: skip the list and open the first footnote immediately.
old = '''  const int sourceSpine = currentSpineIndex;
  if (currentPageFootnotes.size() == 1) {
    openSearchFootnotePopup(mode, sourceSpine, 0);
  } else {
    openSearchFootnoteList(mode, sourceSpine);
  }'''
new = '''  const int sourceSpine = currentSpineIndex;
  // CPHUN-144 shortcut UX: for any non-empty page, open the first footnote
  // immediately. Sibling footnotes remain reachable with front buttons 3/4.
  openSearchFootnotePopup(mode, sourceSpine, 0);'''
if s.count(old) != 1:
    raise SystemExit(f"CPHUN-144 shortcut entry anchor matches={s.count(old)}")
s = s.replace(old, new, 1)

# Keep cache across redraws of the same page, invalidate only when page identity changes.
old = '''    currentPageVisibleOffset = p->visibleTextOffset;
    currentPageFootnotes = std::move(p->footnotes);

    const auto start = millis();'''
new = '''    currentPageVisibleOffset = p->visibleTextOffset;
    currentPageFootnotes = std::move(p->footnotes);
    if (footnoteTextCacheSpine_ != currentSpineIndex || footnoteTextCachePage_ != section->currentPage) {
      footnoteTextCacheIndexes_.fill(-1);
      for (auto& text : footnoteTextCacheTexts_) text.clear();
      footnoteTextCacheSpine_ = currentSpineIndex;
      footnoteTextCachePage_ = section->currentPage;
    }

    const auto start = millis();'''
if s.count(old) != 1:
    raise SystemExit("CPHUN-144 page cache reset anchor mismatch")
s = s.replace(old, new, 1)

write(p, s)

print("CPHUN-144 applied: direct shortcut first footnote + 640px popup + bold/gap + justified HU extended hyphenation + cache/heap diagnostics")
