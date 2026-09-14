from pathlib import Path

path = Path("lib/Epub/Epub/blocks/TextBlock.cpp")
text = path.read_text(encoding="utf-8")

start_marker = "  if (letterSpacingPx == 2 && optimizationAcc) {\n"
end_marker = "\n  const auto* cursor = reinterpret_cast<const uint8_t*>(text);\n"

start = text.find(start_marker)
if start == -1:
    raise SystemExit("CPHUN-121: optimizer render block start not found")
end = text.find(end_marker, start)
if end == -1:
    raise SystemExit("CPHUN-121: optimizer render block end not found")

replacement = r'''  if (letterSpacingPx == 2 && optimizationAcc) {
    const auto fontIt = renderer.getFontMap().find(fontId);
    if (fontIt == renderer.getFontMap().end()) return;
    const EpdFontFamily& font = fontIt->second;

    const auto* cursor = reinterpret_cast<const uint8_t*>(text);
    int nativePenX = x;
    int optimizationOffset = 0;
    uint32_t previous = 0;

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
        optimizationOffset += LetterSpacingOptimization::consumePair(previous, cp, style, *optimizationAcc);
      }

      const size_t glyphBytes = static_cast<size_t>(cursor - glyphStart);
      char glyphText[5];
      memcpy(glyphText, glyphStart, glyphBytes);
      glyphText[glyphBytes] = '\0';

      int glyphX = nativePenX + optimizationOffset;
      if (adjustTrailingHyphen && cp == 0x2011 && *cursor == 0) {
        glyphX += trailingShortHyphenInkShift(renderer, fontId, style);
      }
      renderer.drawText(fontId, glyphX, y, glyphText, true, style, baseDir);
      previous = cp;
    }
    return;
  }
'''

text = text[:start] + replacement + text[end:]

if "nativePrefix" in text:
    raise SystemExit("CPHUN-121: stale nativePrefix reconstruction remains")
if "prefixAdvance - glyphAdvance + optimizationOffset" in text:
    raise SystemExit("CPHUN-121: stale prefix subtraction remains")
if "previousAdvanceFP + kernFP" not in text:
    raise SystemExit("CPHUN-121: native pair advance calculation missing")

path.write_text(text, encoding="utf-8")
