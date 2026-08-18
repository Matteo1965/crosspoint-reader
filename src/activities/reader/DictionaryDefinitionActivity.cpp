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
#include "util/HtmlToPlainText.h"

namespace {

// Longest measurable/drawable span. Wrapped lines stay under the screen width
// (far below this); only pathological unbreakable tokens are split at this cap.
constexpr size_t MAX_LINE_BYTES = 191;

// Body text left/right inset, matching the reader's default feel.
constexpr int SIDE_PADDING = 20;

}  // namespace

void DictionaryDefinitionActivity::onEnter() {
  Activity::onEnter();
  // Normalize StarDict multi-type separators so the wrap loop and the
  // C-string font APIs below both see the whole definition.
  std::replace(definition.begin(), definition.end(), '\0', '\n');
  definition = htmlToPlainText(definition);
  wrapText();
  requestUpdate();
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
  const int spaceWidth = renderer.getSpaceWidth(fontId, EpdFontFamily::REGULAR);
  const int hyphenWidth = renderer.getTextAdvanceX(fontId, "-", EpdFontFamily::REGULAR);

  const int lineHeight = renderer.getLineHeight(fontId);
  const int topArea = (isInverted ? metrics.buttonHintsHeight : 0) + metrics.topPadding + metrics.headerHeight;
  const int bottomArea = metrics.buttonHintsHeight + metrics.verticalSpacing;
  linesPerPage = std::max(1, (renderer.getScreenHeight() - topArea - bottomArea) / lineHeight);

  const char* text = definition.c_str();
  const uint32_t n = static_cast<uint32_t>(definition.size());
  uint32_t lineStart = 0;
  uint32_t lineEnd = 0;
  int lineWidth = 0;
  constexpr char SOURCE_PREFIX[] = "Forrás:";
  bool sourceParagraph = definition.compare(0, sizeof(SOURCE_PREFIX) - 1, SOURCE_PREFIX) == 0;

  const auto flushLine = [&](const uint32_t nextStart, const bool appendHyphen = false) {
    lines.push_back({lineStart, static_cast<uint16_t>(lineEnd - lineStart), appendHyphen});
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
      sourceParagraph = definition.compare(i, sizeof(SOURCE_PREFIX) - 1, SOURCE_PREFIX) == 0;
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
    const auto breakInfos =
        sourceParagraph ? std::vector<Hyphenator::BreakInfo>{}
                        : Hyphenator::breakOffsetsForLanguage(token, false, "hu");

    uint32_t consumed = 0;
    while (consumed < tokenLen) {
      const uint32_t remainingLen = tokenLen - consumed;
      const int remainingWidth = measureSpan(fontId, text + tokenStart + consumed, remainingLen);
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
        const int partWidth = measureSpan(fontId, text + tokenStart + consumed, partLen) +
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
        flushLine(tokenStart + bestOffset, bestNeedsHyphen);
        consumed = bestOffset;
        continue;
      }

      // Retry the full remaining token on an empty line before using the
      // pathological-token fallback below.
      if (!lineEmpty) {
        flushLine(tokenStart + consumed);
        continue;
      }

      // No legal Hungarian break fits. Preserve the old overflow protection:
      // split at the widest complete UTF-8 boundary without inventing a
      // linguistically invalid hyphen.
      uint32_t lastFit = 0;
      for (uint32_t partLen = 1; partLen <= remainingLen; partLen++) {
        if (partLen == remainingLen || (text[tokenStart + consumed + partLen] & 0xC0) != 0x80) {
          if (measureSpan(fontId, text + tokenStart + consumed, partLen) > maxWidth) break;
          lastFit = partLen;
        }
      }
      if (lastFit == 0) {
        lastFit = 1;
        while (lastFit < remainingLen && (text[tokenStart + consumed + lastFit] & 0xC0) == 0x80) lastFit++;
      }
      lineStart = tokenStart + consumed;
      lineEnd = lineStart + lastFit;
      lineWidth = measureSpan(fontId, text + lineStart, lastFit);
      flushLine(lineEnd);
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
void DictionaryDefinitionActivity::drawBody(const int fontId, const int x, const int startY) const {
  const int lineHeight = renderer.getLineHeight(fontId);
  char buf[MAX_LINE_BYTES + 1];
  const int firstLine = currentPage * linesPerPage;
  const int lastLine = std::min(firstLine + linesPerPage, static_cast<int>(lines.size()));
  for (int i = firstLine; i < lastLine; i++) {
    if (lines[i].len == 0) continue;
    const size_t len = std::min(static_cast<size_t>(lines[i].len), MAX_LINE_BYTES);
    memcpy(buf, definition.c_str() + lines[i].start, len);
    buf[len] = '\0';
    // Keep source attribution visually secondary to the dictionary content.
    const bool isSourceLine = strncmp(buf, "Forrás:", strlen("Forrás:")) == 0;
    const int lineFontId = isSourceLine ? NOTOSANS_12_FONT_ID : fontId;
    const int lineY = startY + (i - firstLine) * lineHeight;
    renderer.drawText(lineFontId, x, lineY, buf);
    if (lines[i].appendHyphen) {
      const int hyphenX = x + renderer.getTextAdvanceX(lineFontId, buf, EpdFontFamily::REGULAR);
      renderer.drawText(lineFontId, hyphenX, lineY, "-");
    }
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
  renderer.drawText(NOTOSANS_18_FONT_ID, contentX + SIDE_PADDING, headerY, headword.c_str(), true,
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
  const int bodyStartY = contentY + metrics.topPadding + metrics.headerHeight;
  auto* fcm = renderer.getFontCacheManager();
  auto scope = fcm->createPrewarmScope();
  drawBody(fontId, contentX + SIDE_PADDING, bodyStartY);  // scan pass: records codepoints only
  scope.endScanAndPrewarm();
  drawBody(fontId, contentX + SIDE_PADDING, bodyStartY);

  const auto labels =
      mappedInput.mapLabels(tr(STR_BACK), "", (currentPage > 0 ? "<" : ""), (currentPage + 1 < totalPages ? ">" : ""));
  GUI.drawButtonHints(renderer, labels.btn1, labels.btn2, labels.btn3, labels.btn4);
  renderer.displayBuffer();
}
