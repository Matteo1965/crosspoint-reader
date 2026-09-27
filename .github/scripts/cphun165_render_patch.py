#!/usr/bin/env python3
"""CPHUN-165: render-time bitmap inspection and exact distributed gap shifts."""
from pathlib import Path

def edit(path,fn):
    p=Path(path)
    old=p.read_text(encoding="utf-8")
    new=fn(old)
    assert old!=new,path
    p.write_text(new,encoding="utf-8")

def rep(s,old,new,label):
    assert s.count(old)==1,(label,s.count(old))
    return s.replace(old,new,1)

def opt_header(s):
    a="inline bool isStandaloneWordSpacing(uint8_t value)"
    helper="""// Reject missing-bitmaps (-1); never count them as a zero-pixel ink inset.
inline int missingFinalInkPixels(int targetRight, int finalWordX,
                                 int measuredAdvance, int renderedInkInset) {
  if (targetRight <= 0 || renderedInkInset < 0) return 0;
  return std::clamp(targetRight - finalWordX - measuredAdvance + renderedInkInset,
                    0, MAX_INK_CORRECTION_PX);
}

"""
    return rep(s,a,helper+a,"optical math helper")
edit("lib/Epub/Epub/OpticalLineCorrection.h",opt_header)

def header(s):
    s=rep(s,"  uint8_t letterSpacingPx = 0;","""  uint8_t letterSpacingPx = 0;
  uint16_t opticalTargetRightX_ = 0;  // 0 means no optical closure
  uint16_t opticalLastWordAdvance_ = 0;""","optical scalars")
    s=rep(s,"  const uint8_t* bidiDirArr = nullptr;","""  const uint8_t* bidiDirArr = nullptr;
  const uint8_t* opticalGapsArr = nullptr;  // allocated only for optical lines""","gap flags")
    s=rep(s,"static size_t arenaSize(uint16_t wordCount, bool hasFocus, uint16_t textBytes);","static size_t arenaSize(uint16_t wordCount, bool hasFocus, uint16_t textBytes, bool hasOptical);","arena method")
    s=rep(s,"std::vector<std::string> rubyTexts = {}, uint8_t letterSpacingPx = 0);","""std::vector<std::string> rubyTexts = {}, uint8_t letterSpacingPx = 0,
                     uint16_t opticalTargetRightX = 0, uint16_t opticalLastWordAdvance = 0,
                     const std::vector<uint8_t>& opticalGaps = {});""","constructor signature")
    return s
edit("lib/Epub/Epub/blocks/TextBlock.h",header)

def block(s):
    anchor="}  // namespace\n\nsize_t TextBlock::arenaSize("
    helper="""// Read actual 1-bit or 2-bit glyph pixels AFTER SD font prewarming.
// CPHUN-164 measured too early, frequently obtaining no bitmap at layout time.
// A missing glyph/bitmap returns -1, never the misleading zero inset.
int renderedFinalInkInset(const GfxRenderer& renderer, const int fontId,
                         const char* text, const EpdFontFamily::Style style) {
  if (!text || !*text) return -1;
  const auto* cursor = reinterpret_cast<const uint8_t*>(text);
  uint32_t finalCp = 0;
  while (*cursor) {
    const uint32_t cp = utf8NextCodepoint(&cursor);
    if (!cp) break;
    finalCp = cp;
  }
  if (!OpticalLineCorrection::isLatinLetter(finalCp)) return -1;
  const auto it = renderer.getFontMap().find(fontId);
  if (it == renderer.getFontMap().end() ||
      !it->second.hasCodepoint(finalCp, style)) return -1;
  const EpdFontFamily& font = it->second;
  const EpdFontData* data = font.getData(style);
  const EpdGlyph* glyph = font.getGlyph(finalCp, style);
  if (!data || !glyph || glyph->width == 0 || glyph->height == 0) return -1;
  const uint8_t* bitmap = renderer.getGlyphBitmap(data, glyph);
  if (!bitmap) return -1;
  int dark = -1;
  int any = -1;
  int pixel = 0;
  for (int row = 0; row < glyph->height; ++row) {
    for (int col = 0; col < glyph->width; ++col, ++pixel) {
      uint8_t intensity;
      if (data->is2Bit) {
        const int shift = 6 - ((pixel & 3) << 1);
        intensity = static_cast<uint8_t>((bitmap[pixel >> 2] >> shift) & 3u);
      } else {
        intensity = (bitmap[pixel >> 3] & (0x80u >> (pixel & 7))) ? 3u : 0u;
      }
      if (intensity && col > any) any = col;
      if (intensity >= 2 && col > dark) dark = col;
    }
  }
  const int lastInk = dark >= 0 ? dark : any;
  if (lastInk < 0) return -1;
  const int advance = (static_cast<int>(glyph->advanceX) + 8) >> 4;
  const int rightEdge = static_cast<int>(glyph->left) + lastInk + 1;
  return std::max(0, advance - rightEdge);
}

"""
    s=rep(s,anchor,helper+anchor,"bitmap helper")
    s=rep(s,"const bool hasFocus, const uint16_t textBytes) {","const bool hasFocus, const uint16_t textBytes, const bool hasOptical) {","arena definition")
    s=rep(s,"  return size + textBytes;\n}","  return size + (hasOptical ? wordCount : 0) + textBytes;\n}","arena bytes")
    s=rep(s,"  textArr = reinterpret_cast<const char*>(base + off);","""  if (opticalTargetRightX_ > 0) {
    opticalGapsArr = base + off;
    off += wc;
  }
  textArr = reinterpret_cast<const char*>(base + off);""","bind gap flags")
    old="""std::vector<std::string> rubyTexts, const uint8_t letterSpacingPx)
    : blockStyle(blockStyle), rubyTexts(std::move(rubyTexts)), letterSpacingPx(letterSpacingPx) {"""
    new="""std::vector<std::string> rubyTexts, const uint8_t letterSpacingPx,
                      const uint16_t opticalTargetRightX,
                      const uint16_t opticalLastWordAdvance,
                      const std::vector<uint8_t>& opticalGaps)
    : blockStyle(blockStyle), rubyTexts(std::move(rubyTexts)), letterSpacingPx(letterSpacingPx),
      opticalTargetRightX_(opticalGaps.empty() ? 0 : opticalTargetRightX),
      opticalLastWordAdvance_(opticalGaps.empty() ? 0 : opticalLastWordAdvance) {"""
    s=rep(s,old,new,"constructor")
    s=rep(s,"words.size() != wordVisibleOffsets.size() || words.size() > 10000 ||","""words.size() != wordVisibleOffsets.size() || words.size() > 10000 ||
       (!opticalGaps.empty() && words.size() != opticalGaps.size()) ||""","constructor validation")
    assert s.count("arenaSize(numWords, focusPresent, textBytes);")==2
    s=s.replace("arenaSize(numWords, focusPresent, textBytes);","arenaSize(numWords, focusPresent, textBytes, opticalTargetRightX_ != 0);",1)
    s=rep(s,"  if (focusPresent) {\n    auto* suffixX = const_cast<uint16_t*>(focusSuffixXArr);","""  if (opticalTargetRightX_ > 0) {
    memcpy(const_cast<uint8_t*>(opticalGapsArr), opticalGaps.data(), numWords);
  }
  if (focusPresent) {
    auto* suffixX = const_cast<uint16_t*>(focusSuffixXArr);""","copy optical gaps")
    # Select exact target and eligible positions before drawing. No heap allocation
    # or font-SD lookup during scan mode. Both simple and complex paths use it.
    anchor="  const bool blockHasRuby = hasRuby();"
    code="""  int opticalExtra = 0;
  int opticalGapCount = 0;
  if (!scanning && opticalTargetRightX_ > 0 && numWords > 1 && opticalGapsArr) {
    const int inset = renderedFinalInkInset(
        renderer, fontId, wordText(numWords - 1), wordStyle(numWords - 1));
    opticalExtra = OpticalLineCorrection::missingFinalInkPixels(
        opticalTargetRightX_, xposArr[numWords - 1], opticalLastWordAdvance_, inset);
    if (opticalExtra > 0) {
      for (uint16_t j = 1; j < numWords; ++j)
        opticalGapCount += opticalGapsArr[j] != 0;
    }
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
"""
    s=rep(s,anchor,code+anchor,"render-time shift")
    s=rep(s,"drawTrackedText(renderer, fontId, xposArr[i] + x, y, wordText(i)","drawTrackedText(renderer, fontId, xposArr[i] + x + opticalShiftAt(i), y, wordText(i)","simple render")
    s=rep(s,"    const int wordX = xposArr[i] + x;","    const int wordX = xposArr[i] + x + opticalShiftAt(i);","decorated render")
    s=rep(s,"  serialization::writePod(file, letterSpacingPx);","""  serialization::writePod(file, letterSpacingPx);
  serialization::writePod(file, opticalTargetRightX_);
  serialization::writePod(file, opticalLastWordAdvance_);""","serialize scalars")
    s=rep(s,"arenaSize(numWords, focusPresent, textBytes);","arenaSize(numWords, focusPresent, textBytes, opticalTargetRightX_ != 0);","serialize arena")
    s=rep(s,"  uint8_t cachedLetterSpacingPx = 0;","""  uint8_t cachedLetterSpacingPx = 0;
  uint16_t cachedOpticalTargetX = 0;
  uint16_t cachedOpticalAdvance = 0;""","deserialize scalars")
    s=rep(s,"  serialization::readPod(file, cachedLetterSpacingPx);","""  serialization::readPod(file, cachedLetterSpacingPx);
  serialization::readPod(file, cachedOpticalTargetX);
  serialization::readPod(file, cachedOpticalAdvance);""","deserialize reads")
    s=rep(s,"  block->focusPresent = hasFocus != 0;","""  block->focusPresent = hasFocus != 0;
  block->opticalTargetRightX_ = cachedOpticalTargetX;
  block->opticalLastWordAdvance_ = cachedOpticalAdvance;
  if ((wc == 0 && cachedOpticalTargetX != 0) ||
      (cachedOpticalTargetX != 0 && cachedOpticalAdvance == 0)) return nullptr;""","deserialize validate")
    s=rep(s,"arenaSize(wc, block->focusPresent, textBytes);","arenaSize(wc, block->focusPresent, textBytes, block->opticalTargetRightX_ != 0);","deserialize arena")
    assert s.count("opticalShiftAt(i)")==2
    assert "getGlyphBitmap(data, glyph)" in s
    return s
edit("lib/Epub/Epub/blocks/TextBlock.cpp",block)
print("CPHUN-165: bitmap-ready optical closure, distributed gaps and cache scalars patched.")
