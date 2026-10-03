#include "TextBlock.h"

#include <BidiUtils.h>
#include <GfxRenderer.h>
#include <Logging.h>
#include <Memory.h>
#include <Serialization.h>
#include <Utf8.h>

#include <cstring>

#include "../../../../src/fontIds.h"
#include "../ParsedText.h"
#include "../ShortHyphenGlyph.h"
#include "../LetterSpacingOptimization.h"
#include "../OpticalLineCorrection.h"

namespace {

uint32_t countCodepoints(const char* text) {
  if (text == nullptr) return 0;
  const auto* cursor = reinterpret_cast<const uint8_t*>(text);
  uint32_t count = 0;
  while (*cursor) {
    if (utf8NextCodepoint(&cursor) == 0) break;
    ++count;
  }
  return count;
}

bool endsWithSelectedShortHyphen(const char* text, const short_hyphen::Glyph glyph) {
  if (text == nullptr) return false;
  const size_t len = strlen(text);
  const size_t glyphBytes = strlen(glyph.utf8);
  return len >= glyphBytes &&
         memcmp(text + len - glyphBytes, glyph.utf8, glyphBytes) == 0;
}

int trailingShortHyphenInkShift(const GfxRenderer& renderer, const int fontId,
                               const EpdFontFamily::Style style,
                               const short_hyphen::Glyph glyph) {
  const auto it = renderer.getFontMap().find(fontId);
  if (it == renderer.getFontMap().end()) return 0;
  const EpdGlyph* bitmap = it->second.getGlyph(glyph.codepoint, style);
  if (!bitmap) return 0;
  int renderedLeft = bitmap->left;
  if ((style & (EpdFontFamily::SUP | EpdFontFamily::SUB)) != 0) renderedLeft /= 2;
  return -renderedLeft;
}

void drawTrackedText(const GfxRenderer& renderer, const int fontId, const int x, const int y, const char* text,
                     const EpdFontFamily::Style style, const BidiUtils::BidiBaseDir baseDir,
                     const uint8_t letterSpacingPx, const bool alignTrailingShortHyphenInk,
                     LetterSpacingOptimization::Accumulator* optimizationAcc) {
  if (text == nullptr || *text == '\0') return;

  const auto shortGlyph = short_hyphen::select(renderer, fontId, style);
  const bool adjustTrailingHyphen =
      alignTrailingShortHyphenInk && endsWithSelectedShortHyphen(text, shortGlyph);
  if (letterSpacingPx == 0) {
    if (!adjustTrailingHyphen) {
      renderer.drawText(fontId, x, y, text, true, style, baseDir);
      return;
    }
    const size_t len = strlen(text);
    const std::string prefix(text, len - strlen(shortGlyph.utf8));
    if (!prefix.empty()) renderer.drawText(fontId, x, y, prefix.c_str(), true, style, baseDir);
    const int fullAdvance = renderer.getTextAdvanceX(fontId, text, style);
    const int hyphenAdvance = renderer.getTextAdvanceX(fontId, shortGlyph.utf8, style);
    const int hyphenPenX = x + fullAdvance - hyphenAdvance;
    renderer.drawText(fontId, hyphenPenX + trailingShortHyphenInkShift(renderer, fontId, style, shortGlyph), y,
                      shortGlyph.utf8, true, style, baseDir);
    return;
  }

  const bool packedOptimization =
      LetterSpacingOptimization::isPackedConfig(letterSpacingPx);
  const bool optimizeThisWord =
      packedOptimization && optimizationAcc &&
      LetterSpacingOptimization::beginWord(text, style, *optimizationAcc);

  if (packedOptimization && !optimizeThisWord) {
    if (!adjustTrailingHyphen) {
      renderer.drawText(fontId, x, y, text, true, style, baseDir);
      return;
    }
    const size_t len = strlen(text);
    const std::string prefix(text, len - strlen(shortGlyph.utf8));
    if (!prefix.empty()) renderer.drawText(fontId, x, y, prefix.c_str(), true, style, baseDir);
    const int fullAdvance = renderer.getTextAdvanceX(fontId, text, style);
    const int hyphenAdvance = renderer.getTextAdvanceX(fontId, shortGlyph.utf8, style);
    const int hyphenPenX = x + fullAdvance - hyphenAdvance;
    renderer.drawText(fontId, hyphenPenX + trailingShortHyphenInkShift(renderer, fontId, style, shortGlyph), y,
                      shortGlyph.utf8, true, style, baseDir);
    return;
  }

  if (optimizeThisWord) {
    const auto fontIt = renderer.getFontMap().find(fontId);
    if (fontIt == renderer.getFontMap().end()) return;
    const EpdFontFamily& font = fontIt->second;

    const auto* cursor = reinterpret_cast<const uint8_t*>(text);
    int nativePenX = x;
    int optimizationOffset = 0;
    uint32_t previous = 0;
    uint32_t beforePrevious = 0;

    while (*cursor) {
      const auto* glyphStart = cursor;
      const uint32_t cp = utf8NextCodepoint(&cursor);
      if (cp == 0) break;

      if (previous != 0) {
        // Match GfxRenderer::drawText exactly: combine the previous glyph's
        // 12.4 advance with this pair's 4.4 kerning, then round once.
        // Do not reconstruct the pen from prefix widths; that can introduce
        // +/-1 px differential-rounding errors between adjacent pairs.
        const EpdGlyph* previousGlyph = font.getGlyph(previous, style);
        const int32_t previousAdvanceFP = previousGlyph ? static_cast<int32_t>(previousGlyph->advanceX) : 0;
        const int32_t kernFP = static_cast<int32_t>(font.getKerning(previous, cp, style));
        const int32_t pairAdvanceFP = previousAdvanceFP + kernFP;
        const int nativePairAdvancePx = static_cast<int>((pairAdvanceFP + 8) >> 4);
        nativePenX += nativePairAdvancePx;

        // The optimizer contributes only real whole pixels. A non-emitting
        // pair therefore keeps its native spacing pixel-identical.
        const auto* lookahead = cursor;
        const uint32_t next = *lookahead ? utf8NextCodepoint(&lookahead) : 0;
        optimizationOffset += LetterSpacingOptimization::consumeGuardedPair(
            beforePrevious, previous, cp, next, style, *optimizationAcc);
      }

      const size_t glyphBytes = static_cast<size_t>(cursor - glyphStart);
      char glyphText[5];
      memcpy(glyphText, glyphStart, glyphBytes);
      glyphText[glyphBytes] = '\0';

      int glyphX = nativePenX + optimizationOffset;
      if (adjustTrailingHyphen && cp == 0x2011 && *cursor == 0) {
        glyphX += trailingShortHyphenInkShift(renderer, fontId, style, shortGlyph);
      }
      renderer.drawText(fontId, glyphX, y, glyphText, true, style, baseDir);
      beforePrevious = previous;
      previous = cp;
    }
    return;
  }

  const auto* cursor = reinterpret_cast<const uint8_t*>(text);
  int penX = x;
  uint32_t previous = 0;
  const int standaloneBudget = OpticalLineCorrection::standaloneBudget(letterSpacingPx);
  const int standaloneSlots = standaloneBudget > 0 ? static_cast<int>(countCodepoints(text)) - 1 : 0;
  int standaloneSlot = 0;
  while (*cursor) {
    const auto* glyphStart = cursor;
    const uint32_t cp = utf8NextCodepoint(&cursor);
    if (cp == 0) break;
    if (previous != 0) {
      const int extra = standaloneBudget > 0
          ? OpticalLineCorrection::extraForSlot(standaloneSlot++, standaloneSlots, standaloneBudget)
          : letterSpacingPx;
      penX += renderer.getKerning(fontId, previous, cp, style) + extra;
    }
    const size_t glyphBytes = static_cast<size_t>(cursor - glyphStart);
    char glyphText[5];
    memcpy(glyphText, glyphStart, glyphBytes);
    glyphText[glyphBytes] = '\0';
    int glyphX = penX;
    if (adjustTrailingHyphen && cp == shortGlyph.codepoint && *cursor == 0) {
      glyphX += trailingShortHyphenInkShift(renderer, fontId, style, shortGlyph);
    }
    renderer.drawText(fontId, glyphX, y, glyphText, true, style, baseDir);
    penX += renderer.getTextAdvanceX(fontId, glyphText, style);
    previous = cp;
  }
}

// Read actual 1-bit or 2-bit glyph pixels AFTER SD font prewarming.
// CPHUN-164 measured too early, frequently obtaining no bitmap at layout time.
// A missing glyph/bitmap returns -1, never the misleading zero inset.
// Reconstruct the actual last-glyph ink edge using drawText's pair-level
// fixed-point advance and kerning, NOT the layout SD advance-table sum.
// Only ordinary LTR Latin words enter this path via ParsedText's eligibility
// gate. Non-resident glyphs and unsupported shaping fail closed.
int renderedFinalWordInkInset(const GfxRenderer& renderer, const int fontId,
                             const char* text, const EpdFontFamily::Style style,
                             const int plannedAdvance) {
  if (!text || !*text || plannedAdvance <= 0) return -1;
  const auto it = renderer.getFontMap().find(fontId);
  if (it == renderer.getFontMap().end()) return -1;
  const EpdFontFamily& font = it->second;
  const EpdFontData* data = font.getData(style);
  if (!data || (style & (EpdFontFamily::SUP | EpdFontFamily::SUB)) != 0) return -1;

  // Keep the original string untouched for the layout fast-path measurement.
  const char* cursor = text;
  uint32_t previous = 0;
  int32_t previousAdvanceFP = 0;
  int nativePen = 0;
  const EpdGlyph* lastGlyph = nullptr;
  uint32_t lastCodepoint = 0;
  while (*cursor) {
    uint32_t cp = utf8NextCodepoint(reinterpret_cast<const uint8_t**>(&cursor));
    if (!cp) break;
    if (utf8IsCombiningMark(cp)) return -1;  // not the plain native paint path
    cp = font.applyLigatures(cp, cursor, style);
    if (!font.hasCodepoint(cp, style)) return -1; // fallback fonts use a different path
    const EpdGlyph* glyph = font.getGlyph(cp, style);
    if (!glyph) return -1;
    if (previous != 0) {
      // Identical to GfxRenderer::drawText: round the previous glyph's
      // 12.4 advance PLUS this pair's 4.4 kerning once.
      nativePen += static_cast<int>(
          (previousAdvanceFP + static_cast<int32_t>(font.getKerning(previous, cp, style)) + 8) >> 4);
    }
    previousAdvanceFP = glyph->advanceX;
    previous = cp;
    lastGlyph = glyph;
    lastCodepoint = cp;
  }
  if (!lastGlyph || !OpticalLineCorrection::isLatinLetter(lastCodepoint) ||
      lastGlyph->width == 0 || lastGlyph->height == 0) return -1;

  const uint8_t* bitmap = renderer.getGlyphBitmap(data, lastGlyph);
  if (!bitmap) return -1;
  // GfxRenderer BW draws all nonwhite antialiasing pixels, not only >=2.
  int rightmostPainted = -1;
  int pixel = 0;
  for (int row = 0; row < lastGlyph->height; ++row) {
    for (int col = 0; col < lastGlyph->width; ++col, ++pixel) {
      uint8_t intensity = 0;
      if (data->is2Bit) {
        const int shift = 6 - ((pixel & 3) << 1);
        intensity = static_cast<uint8_t>((bitmap[pixel >> 2] >> shift) & 3u);
      } else {
        intensity = (bitmap[pixel >> 3] & (0x80u >> (pixel & 7))) ? 3u : 0u;
      }
      if (OpticalLineCorrection::countsAsPaintedInk(intensity) && col > rightmostPainted)
        rightmostPainted = col;
    }
  }
  const int lastInk = rightmostPainted;
  if (lastInk < 0) return -1;
  const int glyphAdvance = static_cast<int>((previousAdvanceFP + 8) >> 4);
  const int glyphInkRight = static_cast<int>(lastGlyph->left) + lastInk + 1;
  const int nativeAdvance = nativePen + glyphAdvance;
  const int layoutBaseAdvance = renderer.getTextAdvanceX(fontId, text, style);
  return OpticalLineCorrection::effectiveFinalInkInset(
      plannedAdvance, layoutBaseAdvance, nativeAdvance,
      std::max(0, glyphAdvance - glyphInkRight));
}

}  // namespace

size_t TextBlock::arenaSize(const uint16_t wordCount, const bool hasFocus, const uint16_t textBytes, const bool hasOptical) {
  // Layout documented in TextBlock.h: 16-bit arrays first, then 8-bit arrays, then text.
  size_t size = static_cast<size_t>(wordCount) *
                (sizeof(uint32_t) + sizeof(uint16_t) + sizeof(int16_t) + sizeof(uint8_t) + sizeof(uint8_t));
  if (hasFocus) {
    size += static_cast<size_t>(wordCount) * (sizeof(uint16_t) + sizeof(uint8_t));
  }
  return size + (hasOptical ? wordCount : 0) + textBytes;
}

void TextBlock::bindArenaPointers() {
  uint8_t* base = arena.get();
  const size_t wc = numWords;
  visibleOffsetArr = reinterpret_cast<const uint32_t*>(base);
  size_t off = wc * sizeof(uint32_t);
  textOffArr = reinterpret_cast<const uint16_t*>(base + off);
  off += wc * sizeof(uint16_t);
  xposArr = reinterpret_cast<const int16_t*>(base + off);
  off += wc * sizeof(int16_t);
  if (focusPresent) {
    focusSuffixXArr = reinterpret_cast<const uint16_t*>(base + off);
    off += wc * 2;
  }
  stylesArr = base + off;
  off += wc;
  bidiDirArr = base + off;
  off += wc;
  if (focusPresent) {
    focusBoundaryArr = base + off;
    off += wc;
  }
  if (opticalTargetRightX_ > 0) {
    opticalGapsArr = base + off;
    off += wc;
  }
  textArr = reinterpret_cast<const char*>(base + off);
}

void TextBlock::refreshRenderFlags() {
  simpleRender = !focusPresent && rubyTexts.empty();
  if (!simpleRender) return;
  constexpr uint8_t complexMask =
      static_cast<uint8_t>(EpdFontFamily::UNDERLINE | EpdFontFamily::STRIKETHROUGH | EpdFontFamily::SUP |
                           EpdFontFamily::SUB | EpdFontFamily::RUBY_CONTINUE);
  for (uint16_t i = 0; i < numWords; ++i) {
    if ((stylesArr[i] & complexMask) != 0) {
      simpleRender = false;
      return;
    }
  }
}

TextBlock::TextBlock(const std::vector<std::string>& words, const std::vector<int16_t>& wordXpos,
                     const std::vector<EpdFontFamily::Style>& wordStyles,
                     const std::vector<uint32_t>& wordVisibleOffsets, const std::vector<uint8_t>& focusBoundary,
                     const std::vector<uint16_t>& focusSuffixX, const BlockStyle& blockStyle,
                     std::vector<std::string> rubyTexts, const uint8_t letterSpacingPx,
                      const uint16_t opticalTargetRightX,
                      const uint16_t opticalLastWordAdvance,
                      const std::vector<uint8_t>& opticalGaps)
    : blockStyle(blockStyle), rubyTexts(std::move(rubyTexts)), letterSpacingPx(letterSpacingPx),
      opticalTargetRightX_(opticalGaps.empty() ? 0 : opticalTargetRightX),
      opticalLastWordAdvance_(opticalGaps.empty() ? 0 : opticalLastWordAdvance) {
  // Same invariant as deserialize(): a block never holds an all-empty rubyTexts, so a
  // ruby-less line costs nothing beyond its arena. The layout engine hands one over for
  // every line it extracts, ruby or not; release it here rather than carrying it for the
  // block's lifetime. Move-assigning an empty vector frees the buffer (clear() would not).
  if (!hasRuby()) {
    this->rubyTexts = std::vector<std::string>{};
  }

  // Focus annotations are optional: empty vectors mean no word in this block has a split.
  // When present, they must be sized in lockstep with words[].
  const bool hasFocus = !focusBoundary.empty();
  if (words.size() != wordXpos.size() || words.size() != wordStyles.size() ||
      words.size() != wordVisibleOffsets.size() || words.size() > 10000 ||
       (!opticalGaps.empty() && words.size() != opticalGaps.size()) ||
      (hasFocus && (words.size() != focusBoundary.size() || words.size() != focusSuffixX.size()))) {
    LOG_ERR("TXB", "Construction failed: size mismatch (words=%u, xpos=%u, styles=%u, boundary=%u, suffixX=%u)",
            static_cast<uint32_t>(words.size()), static_cast<uint32_t>(wordXpos.size()),
            static_cast<uint32_t>(wordStyles.size()), static_cast<uint32_t>(focusBoundary.size()),
            static_cast<uint32_t>(focusSuffixX.size()));
    isValid = false;
    return;
  }

  numWords = static_cast<uint16_t>(words.size());
  focusPresent = hasFocus;
  if (numWords == 0) {
    return;  // valid empty block, no arena
  }

  // Pass 1: total text size, one NUL per word. A line is at most a physical
  // row of the page, so uint16_t offsets are ample; reject anything larger.
  size_t totalText = 0;
  for (const auto& w : words) totalText += w.size() + 1;
  if (totalText > UINT16_MAX) {
    LOG_ERR("TXB", "Construction failed: text size %u exceeds arena limit", static_cast<uint32_t>(totalText));
    numWords = 0;
    focusPresent = false;
    isValid = false;
    return;
  }
  textBytes = static_cast<uint16_t>(totalText);

  const size_t size = arenaSize(numWords, focusPresent, textBytes, opticalTargetRightX_ != 0);
  arena = makeUniqueNoThrow<uint8_t[]>(size);
  if (!arena) {
    LOG_ERR("TXB", "OOM: arena %u bytes", static_cast<uint32_t>(size));
    numWords = 0;
    textBytes = 0;
    focusPresent = false;
    isValid = false;
    return;
  }
  bindArenaPointers();

  // Pass 2: fill. Mutable aliases of the const views bound above.
  auto* visibleOffsets = const_cast<uint32_t*>(visibleOffsetArr);
  auto* textOff = const_cast<uint16_t*>(textOffArr);
  auto* xpos = const_cast<int16_t*>(xposArr);
  auto* styles = const_cast<uint8_t*>(stylesArr);
  auto* bidiDir = const_cast<uint8_t*>(bidiDirArr);
  auto* text = const_cast<char*>(textArr);
  uint16_t off = 0;
  for (uint16_t i = 0; i < numWords; i++) {
    visibleOffsets[i] = wordVisibleOffsets[i];
    textOff[i] = off;
    xpos[i] = wordXpos[i];
    styles[i] = static_cast<uint8_t>(wordStyles[i]);
    bidiDir[i] = static_cast<uint8_t>(BidiUtils::detectParagraphLevel(words[i].c_str(), blockStyle.isRtl ? 1 : 0));
    if (letterSpacingPx != 0) bidiDir[i] |= 0x80;
    memcpy(text + off, words[i].data(), words[i].size());
    off += static_cast<uint16_t>(words[i].size());
    text[off++] = '\0';
  }
  if (opticalTargetRightX_ > 0) {
    memcpy(const_cast<uint8_t*>(opticalGapsArr), opticalGaps.data(), numWords);
  }
  if (focusPresent) {
    auto* suffixX = const_cast<uint16_t*>(focusSuffixXArr);
    auto* boundary = const_cast<uint8_t*>(focusBoundaryArr);
    for (uint16_t i = 0; i < numWords; i++) {
      suffixX[i] = focusSuffixX[i];
      boundary[i] = focusBoundary[i];
    }
  }
  refreshRenderFlags();
}

bool TextBlock::hasRuby() const {
  for (const auto& rt : rubyTexts) {
    if (!rt.empty()) return true;
  }
  return false;
}

void TextBlock::render(const GfxRenderer& renderer, const int fontId, const int x, const int y) const {
  if (!isValid) {
    LOG_ERR("TXB", "Render skipped: invalid block");
    return;
  }

  const bool scanning = renderer.isFontCacheScanning();
  const int ascender = renderer.getFontAscenderSize(fontId);

  // Resolve ruby positions. Layout (extractLine) has already reserved extraStartOffset on the
  // left and extraEndOffset on the right, so the centered rubyX is always within the page margins.
  struct RubyDrawInfo {
    int x;
    std::string text;
    BidiUtils::BidiBaseDir baseDir;
  };
  int opticalExtra = 0;
  int opticalGapCount = 0;
  int opticalInset = -1;
  if (!scanning && opticalTargetRightX_ > 0 && numWords > 1 && opticalGapsArr) {
    opticalInset = renderedFinalWordInkInset(
        renderer, fontId, wordText(numWords - 1), wordStyle(numWords - 1),
        opticalLastWordAdvance_);
    opticalExtra = OpticalLineCorrection::missingFinalInkPixels(
        opticalTargetRightX_, xposArr[numWords - 1], opticalLastWordAdvance_, opticalInset);
    for (uint16_t j = 1; j < numWords; ++j)
      opticalGapCount += opticalGapsArr[j] != 0;
    if (opticalGapCount == 0) opticalExtra = 0;
  }
  int opticalGapIndex = 0;
  int opticalCumulative = 0;
  const auto opticalShiftAt = [&](uint16_t i) {
    if (opticalExtra > 0 && opticalGapsArr && opticalGapsArr[i]) {
      opticalCumulative += OpticalLineCorrection::extraForSlot(
          opticalGapIndex++, opticalGapCount, opticalExtra);
    }
    return opticalCumulative;
  };
  const bool blockHasRuby = hasRuby();

  if (simpleRender) {
    const auto pairTable = LetterSpacingOptimization::tableForFontId(fontId);
    const auto optimizationFontIt = renderer.getFontMap().find(fontId);
    const uint8_t optimizationPointSize = optimizationFontIt == renderer.getFontMap().end()
                                              ? 16
                                              : LetterSpacingOptimization::pointSizeForFont(
                                                    optimizationFontIt->second, pairTable);
    LetterSpacingOptimization::Accumulator optimizationAcc(
        LetterSpacingOptimization::unpackThresholdCode(letterSpacingPx),
        LetterSpacingOptimization::unpackBudget(letterSpacingPx),
        pairTable, optimizationPointSize);
    for (uint16_t i = 0; i < numWords; ++i) {
      const auto baseDir = static_cast<BidiUtils::BidiBaseDir>(wordBidiDir(i));
      const bool alignTrailingShortHyphenInk =
          i + 1 == numWords && ParsedText::isShortHyphenEnabled() && ParsedText::isOpticalMarginEnabled();
      drawTrackedText(renderer, fontId, xposArr[i] + x + opticalShiftAt(i), y, wordText(i), wordStyle(i), baseDir, letterSpacingPx,
                      alignTrailingShortHyphenInk, &optimizationAcc);
    }
    return;
  }

  std::vector<RubyDrawInfo> rubies;
  if (blockHasRuby) {
    rubies.resize(numWords);
    for (uint16_t i = 0; i < numWords; i++) {
      if (i < rubyTexts.size() && !rubyTexts[i].empty() && (wordStyle(i) & EpdFontFamily::RUBY_CONTINUE) == 0) {
        int groupWordCount = 1;
        while (i + groupWordCount < numWords && (wordStyle(i + groupWordCount) & EpdFontFamily::RUBY_CONTINUE) != 0) {
          groupWordCount++;
        }
        int groupActualWidth = 0;
        for (int k = 0; k < groupWordCount; ++k) {
          groupActualWidth += renderer.getTextAdvanceX(fontId, wordText(i + k), wordStyle(i + k));
        }
        const int rubyWidth = renderer.getTextAdvanceX(fontId, rubyTexts[i].c_str(), EpdFontFamily::SUP);
        const int leaderWordX = xposArr[i] + x;
        const auto baseDir =
            static_cast<BidiUtils::BidiBaseDir>(BidiUtils::detectParagraphLevel(wordText(i), blockStyle.isRtl ? 1 : 0));
        rubies[i] = {leaderWordX - (rubyWidth - groupActualWidth) / 2, rubyTexts[i], baseDir};
        i += groupWordCount - 1;
      }
    }
  }

  struct DecorationLineTracker {
    EpdFontFamily::Style style;
    int yOffset;
    int startX = -1;
    int endX = -1;
    int yPos = 0;

    bool active() const { return startX != -1; }
    void reset() {
      startX = -1;
      endX = -1;
      yPos = 0;
    }
  };

  DecorationLineTracker decorationLines[] = {
      {EpdFontFamily::UNDERLINE, ascender + 2},
      {EpdFontFamily::STRIKETHROUGH, ascender * 4 / 5},
  };

  const auto flushDecoration = [&](DecorationLineTracker& line) {
    if (line.active()) {
      renderer.drawLine(line.startX, line.yPos, line.endX, line.yPos, 2, true);
      line.reset();
    }
  };
  const auto flushDecorations = [&]() {
    for (auto& line : decorationLines) {
      flushDecoration(line);
    }
  };

  // Loop-invariant: hoisted out of the word loop so rubyTexts is scanned once,
  // not once per word.
  const int rubyShift = getRubyShift(ascender);

  const auto pairTable = LetterSpacingOptimization::tableForFontId(fontId);
  const auto optimizationFontIt = renderer.getFontMap().find(fontId);
  const uint8_t optimizationPointSize = optimizationFontIt == renderer.getFontMap().end()
                                            ? 16
                                            : LetterSpacingOptimization::pointSizeForFont(
                                                  optimizationFontIt->second, pairTable);
  LetterSpacingOptimization::Accumulator optimizationAcc(
      LetterSpacingOptimization::unpackThresholdCode(letterSpacingPx),
      LetterSpacingOptimization::unpackBudget(letterSpacingPx),
      pairTable, optimizationPointSize);
  for (uint16_t i = 0; i < numWords; i++) {
    const char* word = wordText(i);
    const int wordX = xposArr[i] + x + opticalShiftAt(i);
    const EpdFontFamily::Style currentStyle = wordStyle(i);
    const auto baseDir = static_cast<BidiUtils::BidiBaseDir>(wordBidiDir(i));
    const uint8_t boundary = focusBoundary(i);

    // SUP/SUB shift the baseline passed to drawText; the glyph is also scaled 50% inside
    // drawText, so these offsets are chosen relative to the full-size ascender:
    //   SUP: raise by 40% of ascender — sits clearly above the cap-height
    //   SUB: lower by 25% of ascender — descends below baseline without clashing with ascenders below
    int wordY = y + rubyShift;
    if ((currentStyle & EpdFontFamily::SUP) != 0) {
      wordY -= ascender * 2 / 5;
    } else if ((currentStyle & EpdFontFamily::SUB) != 0) {
      wordY += ascender / 4;
    }

    const int drawX = wordX;

    if (boundary > 0) {
      // Focus split: draw bold prefix, then the regular suffix at a pre-computed x offset.
      // The bold prefix is bounded to 9 codepoints by the clamp on targetBoldChars in
      // ParsedText::addWord; 9 UTF-8 codepoints occupy at most 9 * 4 = 36 bytes, +1 for null = 37.
      // suffixX is computed at cache-creation time to avoid font metric lookups at render time.
      static constexpr size_t MAX_FOCUS_PREFIX_BYTES = 9 * 4 + 1;
      char boldBuf[40];
      static_assert(sizeof(boldBuf) >= MAX_FOCUS_PREFIX_BYTES,
                    "boldBuf too small for max focus prefix (9 codepoints * 4 UTF-8 bytes + null)");
      const auto boldStyle = static_cast<EpdFontFamily::Style>(currentStyle | EpdFontFamily::BOLD);
      const size_t boldLen =
          std::min<size_t>({static_cast<size_t>(boundary), static_cast<size_t>(wordTextLen(i)), sizeof(boldBuf) - 1});
      memcpy(boldBuf, word, boldLen);
      boldBuf[boldLen] = '\0';
      renderer.drawText(fontId, drawX, wordY, boldBuf, true, boldStyle, baseDir);
      const int suffixX = drawX + focusSuffixXArr[i];
      renderer.drawText(fontId, suffixX, wordY, word + boldLen, true, currentStyle, baseDir);
    } else {
      const bool alignTrailingShortHyphenInk =
          i + 1 == numWords && ParsedText::isShortHyphenEnabled() && ParsedText::isOpticalMarginEnabled();
      drawTrackedText(renderer, fontId, drawX, wordY, word, currentStyle, baseDir, letterSpacingPx,
                      alignTrailingShortHyphenInk, &optimizationAcc);
    }

    // Horizontal ruby text rendering
    if (blockHasRuby && i < rubyTexts.size() && !rubyTexts[i].empty() &&
        (wordStyle(i) & EpdFontFamily::RUBY_CONTINUE) == 0) {
      const int rubyY = wordY - ascender;
      renderer.drawText(fontId, rubies[i].x, rubyY, rubies[i].text.c_str(), true, EpdFontFamily::SUP,
                        rubies[i].baseDir);
    }

    if (scanning) {
      continue;
    }

    if (EpdFontFamily::hasTextDecoration(currentStyle)) {
      int lineStartX = drawX;
      int lineWidth = renderer.getTextWidth(fontId, word, currentStyle, baseDir);
      const uint32_t cps = countCodepoints(word);
      if (letterSpacingPx == 1 && cps > 1) {
        lineWidth += static_cast<int>(cps - 1) * letterSpacingPx;
      }

      if ((currentStyle & (EpdFontFamily::SUP | EpdFontFamily::SUB)) != 0) {
        lineWidth = (lineWidth + 1) / 2;
      }

      // Do not decorate the synthetic em-space used for paragraph indentation.
      if (wordTextLen(i) >= 3 && static_cast<uint8_t>(word[0]) == 0xE2 && static_cast<uint8_t>(word[1]) == 0x80 &&
          static_cast<uint8_t>(word[2]) == 0x83) {
        const char* visibleText = word + 3;
        lineStartX += renderer.getTextAdvanceX(fontId, "\xe2\x80\x83", currentStyle);
        lineWidth = renderer.getTextWidth(fontId, visibleText, currentStyle, baseDir);
        const uint32_t visibleCps = countCodepoints(visibleText);
        if (letterSpacingPx == 1 && visibleCps > 1) {
          lineWidth += static_cast<int>(visibleCps - 1) * letterSpacingPx;
        }
        if ((currentStyle & (EpdFontFamily::SUP | EpdFontFamily::SUB)) != 0) {
          lineWidth = (lineWidth + 1) / 2;
        }
      }

      for (auto& line : decorationLines) {
        if ((currentStyle & line.style) == 0) {
          flushDecoration(line);
          continue;
        }

        const int lineY = wordY + line.yOffset;
        if (line.active() && line.yPos != lineY) {
          flushDecoration(line);
        }
        if (!line.active()) {
          line.startX = lineStartX;
          line.yPos = lineY;
        }
        line.endX = lineStartX + lineWidth;
      }
    } else {
      flushDecorations();
    }
  }
  flushDecorations();
}

bool TextBlock::serialize(HalFile& file) const {
  if (!isValid) {
    LOG_ERR("TXB", "Serialization failed: invalid block");
    return false;
  }

  // Word data: scalars, then the arena verbatim -- its in-memory layout is
  // exactly the on-disk layout (see TextBlock.h), so one write covers all
  // per-word arrays and the text blob.
  serialization::writePod(file, numWords);
  serialization::writePod(file, static_cast<uint8_t>(focusPresent ? 1 : 0));
  serialization::writePod(file, textBytes);
  // CPHUN-260827-24: persist the actual tracking value. The bidi high bit only
  // records tracking presence and cannot distinguish +1 px from +2 px.
  serialization::writePod(file, letterSpacingPx);
  serialization::writePod(file, opticalTargetRightX_);
  serialization::writePod(file, opticalLastWordAdvance_);
  if (numWords > 0) {
    const size_t size = arenaSize(numWords, focusPresent, textBytes, opticalTargetRightX_ != 0);
    if (file.write(arena.get(), size) != size) {
      LOG_ERR("TXB", "Serialization failed: arena write (%u bytes)", static_cast<uint32_t>(size));
      return false;
    }
  }

  // Ruby text data
  for (size_t i = 0; i < numWords; i++) {
    serialization::writeString(file, (i < rubyTexts.size()) ? rubyTexts[i] : std::string());
  }

  // Style (alignment + margins/padding/indent)
  serialization::writePod(file, blockStyle.alignment);
  serialization::writePod(file, blockStyle.textAlignDefined);
  serialization::writePod(file, blockStyle.marginTop);
  serialization::writePod(file, blockStyle.marginBottom);
  serialization::writePod(file, blockStyle.marginLeft);
  serialization::writePod(file, blockStyle.marginRight);
  serialization::writePod(file, blockStyle.paddingTop);
  serialization::writePod(file, blockStyle.paddingBottom);
  serialization::writePod(file, blockStyle.paddingLeft);
  serialization::writePod(file, blockStyle.paddingRight);
  serialization::writePod(file, blockStyle.textIndent);
  serialization::writePod(file, blockStyle.textIndentDefined);
  serialization::writePod(file, blockStyle.isRtl);
  serialization::writePod(file, blockStyle.directionDefined);

  return true;
}

std::unique_ptr<TextBlock> TextBlock::deserialize(HalFile& file) {
  uint16_t wc;
  uint8_t hasFocus;
  uint16_t textBytes;
  uint8_t cachedLetterSpacingPx = 0;
  uint16_t cachedOpticalTargetX = 0;
  uint16_t cachedOpticalAdvance = 0;
  serialization::readPod(file, wc);
  serialization::readPod(file, hasFocus);
  serialization::readPod(file, textBytes);
  serialization::readPod(file, cachedLetterSpacingPx);
  serialization::readPod(file, cachedOpticalTargetX);
  serialization::readPod(file, cachedOpticalAdvance);

  // Sanity checks: cap the arena allocation and reject impossible geometry
  // (every word carries at least its NUL terminator).
  if (wc > 10000) {
    LOG_ERR("TXB", "Deserialization failed: word count %u exceeds maximum", wc);
    return nullptr;
  }
  if ((wc == 0 && textBytes != 0) || (wc > 0 && textBytes < wc)) {
    LOG_ERR("TXB", "Deserialization failed: bad text size %u for %u words", textBytes, wc);
    return nullptr;
  }

  std::unique_ptr<TextBlock> block(new (std::nothrow) TextBlock());
  if (!block) {
    LOG_ERR("TXB", "OOM: TextBlock");
    return nullptr;
  }
  block->numWords = wc;
  block->textBytes = textBytes;
  block->focusPresent = hasFocus != 0;
  block->opticalTargetRightX_ = cachedOpticalTargetX;
  block->opticalLastWordAdvance_ = cachedOpticalAdvance;
  if ((wc == 0 && cachedOpticalTargetX != 0) ||
      (cachedOpticalTargetX != 0 && cachedOpticalAdvance == 0)) return nullptr;

  if (wc > 0) {
    const size_t size = arenaSize(wc, block->focusPresent, textBytes, block->opticalTargetRightX_ != 0);
    block->arena = makeUniqueNoThrow<uint8_t[]>(size);
    if (!block->arena) {
      LOG_ERR("TXB", "OOM: arena %u bytes", static_cast<uint32_t>(size));
      return nullptr;
    }
    if (file.read(block->arena.get(), size) != size) {
      LOG_ERR("TXB", "Deserialization failed: arena read (%u bytes)", static_cast<uint32_t>(size));
      return nullptr;
    }
    block->bindArenaPointers();
    // Cache v52 stores the exact tracking value explicitly, preserving diagnostic
    // +2 px tracking instead of collapsing every non-zero value to +1 px.
    block->letterSpacingPx = cachedLetterSpacingPx;

    // Validate offsets before anything dereferences wordText(): offset 0 first,
    // strictly increasing, in bounds, and every word NUL-terminated (word i ends
    // at the byte before offset i+1; the last word at the last text byte).
    const uint16_t* textOff = block->textOffArr;
    const char* text = block->textArr;
    if (textOff[0] != 0 || text[textBytes - 1] != '\0') {
      LOG_ERR("TXB", "Deserialization failed: corrupt text layout");
      return nullptr;
    }
    for (uint16_t i = 1; i < wc; i++) {
      if (textOff[i] <= textOff[i - 1] || textOff[i] >= textBytes || text[textOff[i] - 1] != '\0') {
        LOG_ERR("TXB", "Deserialization failed: corrupt word offset %u", i);
        return nullptr;
      }
    }
  }

  // Ruby text data. Ruby is a CJK feature, so for nearly every book every entry here
  // is the empty string. Materializing the vector regardless costs wordCount * 24 bytes
  // (sizeof(std::string)) plus a heap block per line, held for as long as the page is
  // resident -- several KB of DRAM on a full page, none of it ever read. An empty
  // rubyTexts is already the "no ruby" representation: hasRuby() reports false and every
  // other reader is guarded by `i < rubyTexts.size()`, so allocate lazily and only once a
  // non-empty annotation actually shows up.
  //
  // `scratch` is reused across words: readString() resizes it to the incoming length and
  // overwrites every byte, so a moved-from value carries nothing into the next iteration.
  std::string scratch;
  for (uint16_t i = 0; i < wc; i++) {
    serialization::readString(file, scratch);
    if (scratch.empty()) continue;
    if (block->rubyTexts.empty()) {
      block->rubyTexts.resize(wc);
    }
    block->rubyTexts[i] = std::move(scratch);
  }

  // Style (alignment + margins/padding/indent)
  BlockStyle& blockStyle = block->blockStyle;
  serialization::readPod(file, blockStyle.alignment);
  serialization::readPod(file, blockStyle.textAlignDefined);
  serialization::readPod(file, blockStyle.marginTop);
  serialization::readPod(file, blockStyle.marginBottom);
  serialization::readPod(file, blockStyle.marginLeft);
  serialization::readPod(file, blockStyle.marginRight);
  serialization::readPod(file, blockStyle.paddingTop);
  serialization::readPod(file, blockStyle.paddingBottom);
  serialization::readPod(file, blockStyle.paddingLeft);
  serialization::readPod(file, blockStyle.paddingRight);
  serialization::readPod(file, blockStyle.textIndent);
  serialization::readPod(file, blockStyle.textIndentDefined);
  serialization::readPod(file, blockStyle.isRtl);
  serialization::readPod(file, blockStyle.directionDefined);
  block->refreshRenderFlags();

  return block;
}
