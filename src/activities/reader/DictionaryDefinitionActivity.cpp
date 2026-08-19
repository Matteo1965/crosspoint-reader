#include "DictionaryDefinitionActivity.h"

#include <Epub/hyphenation/Hyphenator.h>
#include <FontCacheManager.h>
#include <GfxRenderer.h>
#include <I18n.h>

#include <algorithm>
#include <cstdint>
#include <cstdio>
#include <cstring>

#include "CrossPointSettings.h"
#include "components/UITheme.h"
#include "fontIds.h"
#include "util/DictHtmlPages.h"
#include "util/HtmlToPlainText.h"

namespace {

// Longest measurable/drawable span. Wrapped lines stay under the screen width
// (far below this); only pathological unbreakable tokens are split at this cap.
constexpr size_t MAX_LINE_BYTES = 191;

// Body text left/right inset, matching the reader's default feel.
constexpr int SIDE_PADDING = 20;

constexpr size_t MAX_STYLED_HTML_BYTES = 16 * 1024;

// Uppercase the Hungarian alphabet without depending on a locale (the ESP32
// C locale only knows ASCII). Hungarian accented lower/uppercase pairs have
// equal UTF-8 byte lengths, so the conversion can safely happen in place.
std::string uppercaseHungarian(std::string text) {
  for (size_t i = 0; i < text.size(); i++) {
    const auto c = static_cast<unsigned char>(text[i]);
    if (c >= 'a' && c <= 'z') {
      text[i] = static_cast<char>(c - 'a' + 'A');
      continue;
    }
    if (i + 1 >= text.size()) continue;

    const auto next = static_cast<unsigned char>(text[i + 1]);
    if (c == 0xC3) {
      switch (next) {
        case 0xA1:  // á -> Á
        case 0xA9:  // é -> É
        case 0xAD:  // í -> Í
        case 0xB3:  // ó -> Ó
        case 0xB6:  // ö -> Ö
        case 0xBA:  // ú -> Ú
        case 0xBC:  // ü -> Ü
          text[i + 1] = static_cast<char>(next - 0x20);
          i++;
          break;
        default:
          break;
      }
    } else if (c == 0xC5 && (next == 0x91 || next == 0xB1)) {
      // ő -> Ő, ű -> Ű
      text[i + 1] = static_cast<char>(next - 1);
      i++;
    }
  }
  return text;
}

}  // namespace

void DictionaryDefinitionActivity::onEnter() {
  Activity::onEnter();
  // Normalize StarDict multi-type separators so the wrap loop and the
  // C-string font APIs below both see the whole definition.
  std::replace(definition.begin(), definition.end(), '\0', '\n');
  if (!(htmlDefinition && definition.size() <= MAX_STYLED_HTML_BYTES && layoutHtmlPages())) {
    definition = htmlToPlainText(definition);
    wrapText();
  }
  requestUpdate();
}

DictionaryDefinitionActivity::BodyArea DictionaryDefinitionActivity::bodyArea() const {
  const auto& metrics = UITheme::getInstance().getMetrics();
  const auto orientation = renderer.getOrientation();
  const bool isLandscape = orientation == GfxRenderer::Orientation::LandscapeClockwise ||
                           orientation == GfxRenderer::Orientation::LandscapeCounterClockwise;
  const bool isInverted = orientation == GfxRenderer::Orientation::PortraitInverted;
  const int hintGutterWidth = isLandscape ? metrics.sideButtonHintsWidth : 0;
  const int topArea = (isInverted ? metrics.buttonHintsHeight : 0) + metrics.topPadding + metrics.headerHeight +
                      renderer.getLineHeight(SETTINGS.getReaderFontId());
  const int bottomArea = metrics.buttonHintsHeight + metrics.verticalSpacing;
  return {renderer.getScreenWidth() - hintGutterWidth - 2 * SIDE_PADDING,
          renderer.getScreenHeight() - topArea - bottomArea};
}

bool DictionaryDefinitionActivity::layoutHtmlPages() {
  const BodyArea body = bodyArea();
  if (body.width <= 0 || body.height <= 0) return false;
  if (!buildDictionaryHtmlPages(renderer, definition, static_cast<uint16_t>(body.width),
                                static_cast<uint16_t>(body.height), pages)) {
    return false;
  }
  definition.clear();
  definition.shrink_to_fit();
  totalPages = static_cast<int>(pages.size());
  currentPage = 0;
  return true;
}

int DictionaryDefinitionActivity::measureSpan(const int fontId, const char* text, size_t len) const {
  char buf[MAX_LINE_BYTES + 1];
  len = std::min(len, MAX_LINE_BYTES);
  memcpy(buf, text, len);
  buf[len] = '\0';
  return renderer.getTextAdvanceX(fontId, buf, EpdFontFamily::REGULAR);
}

// Greedy word-wrap of `definition` into byte spans. '\n' breaks lines (blank
// lines survive as paragraph spacing; NULs from multi-type StarDict entries
// were normalized to newlines in onEnter); '\r' is dropped by treating it as
// a space at a token edge.
void DictionaryDefinitionActivity::wrapText() {
  lines.clear();
  lines.reserve(definition.size() / 32 + 8);

  const int fontId = SETTINGS.getReaderFontId();
  // SD-card fonts: merge every definition codepoint into the persistent
  // advance table up front. Otherwise each unseen codepoint measured below
  // falls back to an on-demand glyph load from SD (8-slot overflow ring).
  renderer.ensureSdCardFontReady(fontId, definition.c_str(), 0x01 /* REGULAR */);

  const auto& metrics = UITheme::getInstance().getMetrics();
  const auto orientation = renderer.getOrientation();
  const bool isLandscape = orientation == GfxRenderer::Orientation::LandscapeClockwise ||
                           orientation == GfxRenderer::Orientation::LandscapeCounterClockwise;
  const bool isInverted = orientation == GfxRenderer::Orientation::PortraitInverted;
  const int hintGutterWidth = isLandscape ? metrics.sideButtonHintsWidth : 0;
  const int maxWidth = renderer.getScreenWidth() - hintGutterWidth - 2 * SIDE_PADDING;
  const int lineHeight = renderer.getLineHeight(fontId);
  // Reserve one full blank body line between the enlarged headword and the definition.
  const int topArea =
      (isInverted ? metrics.buttonHintsHeight : 0) + metrics.topPadding + metrics.headerHeight + lineHeight;
  const int bottomArea = metrics.buttonHintsHeight + metrics.verticalSpacing;
  linesPerPage = std::max(1, (renderer.getScreenHeight() - topArea - bottomArea) / lineHeight);

  const char* text = definition.c_str();
  const uint32_t n = static_cast<uint32_t>(definition.size());
  uint32_t lineStart = 0;
  uint32_t lineEnd = 0;
  int lineWidth = 0;
  constexpr char SOURCE_PREFIX[] = "Forrás:";
  bool sourceParagraph = definition.compare(0, sizeof(SOURCE_PREFIX) - 1, SOURCE_PREFIX) == 0;

  const auto flushLine = [&](const uint32_t nextStart, const bool appendHyphen = false, const bool justify = false) {
    lines.push_back({lineStart, static_cast<uint16_t>(lineEnd - lineStart), appendHyphen, sourceParagraph, justify});
    lineStart = nextStart;
    lineEnd = nextStart;
    lineWidth = 0;
  };

  uint32_t i = 0;
  while (i < n) {
    const char c = text[i];
    if (c == '\n' || c == '\0') {
      flushLine(i + 1);
      i++;
      const bool nextIsSource = definition.compare(i, sizeof(SOURCE_PREFIX) - 1, SOURCE_PREFIX) == 0;
      // Normalize any number of source-separating newlines to exactly one
      // visible blank body line before every source paragraph.
      if (nextIsSource && !sourceParagraph && !lines.empty()) {
        while (!lines.empty() && lines.back().len == 0) lines.pop_back();
        lines.push_back({i, 0, false, false, false});
      }
      sourceParagraph = nextIsSource;
      continue;
    }
    if (c == ' ' || c == '\t' || c == '\r') {
      i++;
      continue;
    }

    const uint32_t tokenStart = i;
    while (i < n && text[i] != ' ' && text[i] != '\t' && text[i] != '\r' && text[i] != '\n' && text[i] != '\0' &&
           i - tokenStart < MAX_LINE_BYTES) {
      i++;
    }
    while (i - tokenStart > 1 && (text[i] & 0xC0) == 0x80) i--;
    const uint32_t tokenLen = i - tokenStart;
    const std::string token(text + tokenStart, tokenLen);
    const int wrapFontId = sourceParagraph ? NOTOSANS_12_FONT_ID : fontId;
    const int spaceWidth = renderer.getSpaceWidth(wrapFontId, EpdFontFamily::REGULAR);
    const int hyphenWidth = renderer.getTextAdvanceX(wrapFontId, "-", EpdFontFamily::REGULAR);
    const auto breakInfos = sourceParagraph ? std::vector<Hyphenator::BreakInfo>{}
                                            : Hyphenator::breakOffsetsForLanguage(token, false, "hu");

    uint32_t consumed = 0;
    while (consumed < tokenLen) {
      const uint32_t remainingLen = tokenLen - consumed;
      const int remainingWidth = measureSpan(wrapFontId, text + tokenStart + consumed, remainingLen);
      const bool lineEmpty = lineEnd == lineStart;
      const int gapWidth = lineEmpty ? 0 : spaceWidth;

      if (gapWidth + lineWidth + remainingWidth <= maxWidth) {
        if (lineEmpty) lineStart = tokenStart + consumed;
        lineEnd = tokenStart + tokenLen;
        lineWidth += gapWidth + remainingWidth;
        consumed = tokenLen;
        continue;
      }

      const int availableWidth = maxWidth - lineWidth - gapWidth;
      uint32_t bestOffset = 0;
      bool bestNeedsHyphen = false;
      int bestWidth = 0;
      for (const auto& breakInfo : breakInfos) {
        if (breakInfo.byteOffset <= consumed || breakInfo.byteOffset >= tokenLen) continue;
        const uint32_t partLen = static_cast<uint32_t>(breakInfo.byteOffset) - consumed;
        const int partWidth = measureSpan(wrapFontId, text + tokenStart + consumed, partLen) +
                              (breakInfo.requiresInsertedHyphen ? hyphenWidth : 0);
        if (partWidth <= availableWidth) {
          bestOffset = static_cast<uint32_t>(breakInfo.byteOffset);
          bestNeedsHyphen = breakInfo.requiresInsertedHyphen;
          bestWidth = partWidth;
        }
      }

      if (bestOffset > consumed) {
        if (lineEmpty) lineStart = tokenStart + consumed;
        lineEnd = tokenStart + bestOffset;
        lineWidth += gapWidth + bestWidth;
        flushLine(tokenStart + bestOffset, bestNeedsHyphen, true);
        consumed = bestOffset;
        continue;
      }

      // Retry the full remaining token on an empty line before using the
      // pathological-token fallback below.
      if (!lineEmpty) {
        flushLine(tokenStart + consumed, false, true);
        continue;
      }

      // No legal Hungarian break fits. Preserve the old overflow protection:
      // split at the widest complete UTF-8 boundary without inventing a
      // linguistically invalid hyphen.
      uint32_t lastFit = 0;
      for (uint32_t partLen = 1; partLen <= remainingLen; partLen++) {
        if (partLen == remainingLen || (text[tokenStart + consumed + partLen] & 0xC0) != 0x80) {
          if (measureSpan(wrapFontId, text + tokenStart + consumed, partLen) > maxWidth) break;
          lastFit = partLen;
        }
      }
      if (lastFit == 0) {
        lastFit = 1;
        while (lastFit < remainingLen && (text[tokenStart + consumed + lastFit] & 0xC0) == 0x80) lastFit++;
      }
      lineStart = tokenStart + consumed;
      lineEnd = lineStart + lastFit;
      lineWidth = measureSpan(wrapFontId, text + lineStart, lastFit);
      flushLine(lineEnd, false, true);
      consumed += lastFit;
    }
  }
  if (lineEnd > lineStart) flushLine(n);

  while (!lines.empty() && lines.back().len == 0) lines.pop_back();

  totalPages = std::max(1, (static_cast<int>(lines.size()) + linesPerPage - 1) / linesPerPage);
  currentPage = 0;
}

void DictionaryDefinitionActivity::loop() {
  if (mappedInput.wasReleased(MappedInputManager::Button::Back)) {
    finish();
    return;
  }

  // Same tap zones as the reader page turns: left third = previous page,
  // the rest = next. Back is the usual left-edge swipe.
  int tx = 0;
  int ty = 0;
  if (mappedInput.wasScreenTapped(tx, ty)) {
    if (tx < renderer.getScreenWidth() / 3) {
      if (currentPage > 0) {
        currentPage--;
        requestUpdate();
      }
    } else if (currentPage + 1 < totalPages) {
      currentPage++;
      requestUpdate();
    }
    return;
  }

  buttonNavigator.onNext([this] {
    if (currentPage + 1 < totalPages) {
      currentPage++;
      requestUpdate();
    }
  });

  buttonNavigator.onPrevious([this] {
    if (currentPage > 0) {
      currentPage--;
      requestUpdate();
    }
  });
}

// Draws the current page's line spans (copied into a stack buffer for NUL
// termination). Called twice per render: once in font-cache scan mode, once
// for the real paint.
void DictionaryDefinitionActivity::drawBody(const int fontId, const int x, const int startY, const int maxWidth) const {
  if (!pages.empty()) {
    pages[currentPage]->render(renderer, fontId, x, startY);
    return;
  }
  int lineY = startY;
  char buf[MAX_LINE_BYTES + 1];
  char wordBuf[MAX_LINE_BYTES + 1];
  const int firstLine = currentPage * linesPerPage;
  const int lastLine = std::min(firstLine + linesPerPage, static_cast<int>(lines.size()));
  for (int i = firstLine; i < lastLine; i++) {
    if (lines[i].len == 0) {
      lineY += renderer.getLineHeight(fontId);
      continue;
    }
    const size_t len = std::min(static_cast<size_t>(lines[i].len), MAX_LINE_BYTES);
    memcpy(buf, definition.c_str() + lines[i].start, len);
    buf[len] = '\0';

    // Keep the full wrapped source paragraph visually secondary, including
    // continuation lines that no longer begin with the "Forrás:" prefix.
    const int lineFontId = lines[i].isSource ? NOTOSANS_12_FONT_ID : fontId;

    int wordCount = 0;
    bool inWord = false;
    for (size_t j = 0; j < len; j++) {
      const bool whitespace = buf[j] == ' ' || buf[j] == '\t' || buf[j] == '\r';
      if (whitespace) {
        inWord = false;
      } else if (!inWord) {
        wordCount++;
        inWord = true;
      }
    }

    // Justify wrapped definition lines by distributing the remaining width
    // across word gaps. Paragraph-final and source lines stay left-aligned.
    if (lines[i].justify && !lines[i].isSource && wordCount > 1) {
      int wordsWidth = 0;
      size_t pos = 0;
      while (pos < len) {
        while (pos < len && (buf[pos] == ' ' || buf[pos] == '\t' || buf[pos] == '\r')) pos++;
        const size_t wordStart = pos;
        while (pos < len && buf[pos] != ' ' && buf[pos] != '\t' && buf[pos] != '\r') pos++;
        const size_t wordLen = pos - wordStart;
        if (wordLen == 0) continue;
        memcpy(wordBuf, buf + wordStart, wordLen);
        wordBuf[wordLen] = '\0';
        wordsWidth += renderer.getTextAdvanceX(lineFontId, wordBuf, EpdFontFamily::REGULAR);
      }

      const int gapCount = wordCount - 1;
      const int hyphenWidth =
          lines[i].appendHyphen ? renderer.getTextAdvanceX(lineFontId, "-", EpdFontFamily::REGULAR) : 0;
      const int naturalSpaceWidth = renderer.getSpaceWidth(lineFontId, EpdFontFamily::REGULAR);
      const int extraWidth = std::max(0, maxWidth - wordsWidth - gapCount * naturalSpaceWidth - hyphenWidth);
      const int extraPerGap = extraWidth / gapCount;
      const int remainder = extraWidth % gapCount;

      int cursorX = x;
      int gapIndex = 0;
      pos = 0;
      while (pos < len) {
        while (pos < len && (buf[pos] == ' ' || buf[pos] == '\t' || buf[pos] == '\r')) pos++;
        const size_t wordStart = pos;
        while (pos < len && buf[pos] != ' ' && buf[pos] != '\t' && buf[pos] != '\r') pos++;
        const size_t wordLen = pos - wordStart;
        if (wordLen == 0) continue;
        memcpy(wordBuf, buf + wordStart, wordLen);
        wordBuf[wordLen] = '\0';
        renderer.drawText(lineFontId, cursorX, lineY, wordBuf);
        cursorX += renderer.getTextAdvanceX(lineFontId, wordBuf, EpdFontFamily::REGULAR);
        if (gapIndex < gapCount) {
          cursorX += naturalSpaceWidth + extraPerGap + (gapIndex < remainder ? 1 : 0);
          gapIndex++;
        }
      }
      if (lines[i].appendHyphen) renderer.drawText(lineFontId, cursorX, lineY, "-");
      lineY += renderer.getLineHeight(lineFontId);
      continue;
    }

    renderer.drawText(lineFontId, x, lineY, buf);
    if (lines[i].appendHyphen) {
      const int hyphenX = x + renderer.getTextAdvanceX(lineFontId, buf, EpdFontFamily::REGULAR);
      renderer.drawText(lineFontId, hyphenX, lineY, "-");
    }
    lineY += renderer.getLineHeight(lineFontId);
  }
}

void DictionaryDefinitionActivity::render(RenderLock&&) {
  renderer.clearScreen();

  const auto& metrics = UITheme::getInstance().getMetrics();
  const auto orientation = renderer.getOrientation();
  const bool isLandscapeCw = orientation == GfxRenderer::Orientation::LandscapeClockwise;
  const bool isLandscapeCcw = orientation == GfxRenderer::Orientation::LandscapeCounterClockwise;
  const bool isInverted = orientation == GfxRenderer::Orientation::PortraitInverted;
  const int hintGutterWidth = (isLandscapeCw || isLandscapeCcw) ? metrics.sideButtonHintsWidth : 0;
  const int contentX = isLandscapeCw ? hintGutterWidth : 0;
  const int contentWidth = renderer.getScreenWidth() - hintGutterWidth;
  const int contentY = isInverted ? metrics.buttonHintsHeight : 0;

  // Header: matched headword left, page counter right.
  const int headerY = contentY + metrics.topPadding + 10;
  const std::string displayHeadword = uppercaseHungarian(headword);
  renderer.drawText(NOTOSANS_16_FONT_ID, contentX + SIDE_PADDING, headerY, displayHeadword.c_str(), true,
                    EpdFontFamily::BOLD);
  if (totalPages > 1) {
    char counter[16];
    snprintf(counter, sizeof(counter), "%d/%d", currentPage + 1, totalPages);
    const int counterWidth = renderer.getTextWidth(UI_10_FONT_ID, counter);
    renderer.drawText(UI_10_FONT_ID, contentX + contentWidth - SIDE_PADDING - counterWidth, headerY, counter);
  }

  // Body: two-pass draw inside a prewarm scope (same pattern as the reader's
  // renderContents) so SD-card font glyphs load from SD in one batch instead
  // of one on-demand overflow read per character on every page turn.
  const int fontId = SETTINGS.getReaderFontId();
  // Keep one empty body line below the enlarged headword for clear visual separation.
  const int bodyStartY = contentY + metrics.topPadding + metrics.headerHeight + renderer.getLineHeight(fontId);
  auto* fcm = renderer.getFontCacheManager();
  auto scope = fcm->createPrewarmScope();
  const int bodyWidth = contentWidth - 2 * SIDE_PADDING;
  drawBody(fontId, contentX + SIDE_PADDING, bodyStartY, bodyWidth);  // scan pass: records codepoints only
  scope.endScanAndPrewarm();
  drawBody(fontId, contentX + SIDE_PADDING, bodyStartY, bodyWidth);

  const auto labels =
      mappedInput.mapLabels(tr(STR_BACK), "", (currentPage > 0 ? "<" : ""), (currentPage + 1 < totalPages ? ">" : ""));
  GUI.drawButtonHints(renderer, labels.btn1, labels.btn2, labels.btn3, labels.btn4);
  renderer.displayBuffer();
}
