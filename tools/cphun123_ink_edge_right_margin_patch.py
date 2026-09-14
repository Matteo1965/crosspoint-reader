from pathlib import Path

path = Path("lib/Epub/Epub/ParsedText.cpp")
text = path.read_text(encoding="utf-8")

anchor = '''int scaledNormalSpaceAdvance(const int natural, const uint8_t percent) {
  return std::max(1, (natural * std::clamp<int>(percent, 50, 100) + 99) / 100);
}
'''

helper = r'''// CPHUN-123: optical right-edge closure for ordinary final glyphs.
// Justification is advance-based, while the reader sees the glyph's actual ink.
// For a line-ending letter with a positive right-side ink inset, let justified
// word gaps absorb that inset so the last strong black pixel reaches the same
// optical margin. Existing hanging-punctuation handling remains authoritative.
int trailingStrongInkInset(const GfxRenderer& renderer, const int fontId, const std::string& word,
                           const EpdFontFamily::Style style) {
  if (word.empty()) return 0;
  const uint32_t cp = lastCodepoint(word);
  if (cp == 0 || isHangingPunctuation(cp)) return 0;

  const auto fontIt = renderer.getFontMap().find(fontId);
  if (fontIt == renderer.getFontMap().end()) return 0;
  const EpdFontFamily& font = fontIt->second;
  const EpdGlyph* glyph = font.getGlyph(cp, style);
  const EpdFontData* fontData = font.getData(style);
  if (!glyph || !fontData || glyph->width == 0 || glyph->height == 0) return 0;

  const uint8_t* bitmap = renderer.getGlyphBitmap(fontData, glyph);
  if (!bitmap) return 0;

  int rightmostStrong = -1;
  int rightmostAny = -1;
  const int width = glyph->width;
  const int height = glyph->height;

  if (fontData->is2Bit) {
    // 2-bit font packing is MSB-first, 4 pixels per byte:
    // 0=white, 1=light gray, 2=dark gray, 3=black.
    int pixelPos = 0;
    for (int y = 0; y < height; ++y) {
      for (int x = 0; x < width; ++x, ++pixelPos) {
        const uint8_t packed = bitmap[pixelPos >> 2];
        const int shift = 6 - ((pixelPos & 3) << 1);
        const uint8_t value = static_cast<uint8_t>((packed >> shift) & 0x03u);
        if (value != 0 && x > rightmostAny) rightmostAny = x;
        if (value == 3 && x > rightmostStrong) rightmostStrong = x;
      }
    }
  } else {
    int pixelPos = 0;
    for (int y = 0; y < height; ++y) {
      for (int x = 0; x < width; ++x, ++pixelPos) {
        const uint8_t packed = bitmap[pixelPos >> 3];
        const uint8_t mask = static_cast<uint8_t>(0x80u >> (pixelPos & 7));
        if ((packed & mask) != 0 && x > rightmostStrong) rightmostStrong = x;
      }
    }
    rightmostAny = rightmostStrong;
  }

  const int rightmostInk = rightmostStrong >= 0 ? rightmostStrong : rightmostAny;
  if (rightmostInk < 0) return 0;

  const int advancePx = fp4::toPixel(static_cast<int32_t>(glyph->advanceX));
  const int inkRightExclusive = static_cast<int>(glyph->left) + rightmostInk + 1;
  // Restrict this first experimental pass to the 1-3 px discrepancy observed
  // on the Bitter 16 test page; never pull a pathological glyph far outward.
  return std::clamp(advancePx - inkRightExclusive, 0, 3);
}

'''

if text.count(anchor) != 1:
    raise SystemExit(f"CPHUN-123: scaledNormalSpaceAdvance anchor matches={text.count(anchor)}")
text = text.replace(anchor, helper + anchor, 1)

old = '''  const int spareSpace =
      effectivePageWidth + hangingAllowance - extraStartOffset - extraEndOffset - lineWordWidthSum - totalNaturalGaps;
'''
new = '''  const int trailingInkAllowance =
      (effectiveAlignment == CssTextAlign::Justify && !isLastLine && !blockStyle.isRtl && hangingAllowance == 0 &&
       !lineWords.empty() && actualGapCount > 0)
          ? trailingStrongInkInset(renderer, fontId, lineWords.back(), lineWordStyles.back())
          : 0;
  const int spareSpace = effectivePageWidth + hangingAllowance + trailingInkAllowance - extraStartOffset -
                         extraEndOffset - lineWordWidthSum - totalNaturalGaps;
'''

if text.count(old) != 1:
    raise SystemExit(f"CPHUN-123: spareSpace block matches={text.count(old)}")
text = text.replace(old, new, 1)

if "trailingStrongInkInset" not in text:
    raise SystemExit("CPHUN-123: ink-edge helper missing")
if "hangingAllowance + trailingInkAllowance" not in text:
    raise SystemExit("CPHUN-123: ink allowance not applied to spare space")

path.write_text(text, encoding="utf-8")
