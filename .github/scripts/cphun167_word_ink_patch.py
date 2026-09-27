#!/usr/bin/env python3
"""CPHUN-167: measure the final word's actual painted right edge.

CPHUN-166 proves the last glyph bitmap is available but alone cannot detect
width drift caused by the SD advance-table fast path omitting pair kerning.
Reconstruct drawText's whole-word native pen positions, then account for
tracking already reserved by layout. Never change AA/ABA, hyphens or pagination.
"""
from pathlib import Path

def replace_once(data, before, after, title):
    hits = data.count(before)
    if hits != 1:
        raise SystemExit(f"CPHUN-167 {title}: expected one anchor, got {hits}")
    return data.replace(before, after, 1)

p = Path("lib/Epub/Epub/OpticalLineCorrection.h")
h = p.read_text(encoding="utf-8")
needle = "inline bool isStandaloneWordSpacing(uint8_t value)"
helper = """// The measured layout advance (SD glyph advance table) can differ from
// the renderer's true pair-kerned native advance. The final glyph's own right
// bearing alone is NOT enough: 'kerestek' was measured 137px wide but drew
// three pixels narrower even though the last 'k' ink inset was zero.
// alreadyReservedTracking is included in plannedAdvance and is applied by
// the separate tracked renderer; do not account for it twice.
inline int effectiveFinalInkInset(int plannedAdvance, int layoutBaseAdvance,
                                 int actualNativeAdvance, int finalGlyphInkInset) {
  if (plannedAdvance < 0 || layoutBaseAdvance < 0 ||
      actualNativeAdvance < 0 || finalGlyphInkInset < 0) return -1;
  const int tracking = plannedAdvance - layoutBaseAdvance;
  if (tracking < 0) return -1;
  const int trueInkRight = actualNativeAdvance + tracking - finalGlyphInkInset;
  return std::max(0, plannedAdvance - trueInkRight);
}

"""
h = replace_once(h, needle, helper + needle, "shared effective inset math")
p.write_text(h, encoding="utf-8")

p = Path("lib/Epub/Epub/blocks/TextBlock.cpp")
s = p.read_text(encoding="utf-8")
start = s.index("int renderedFinalInkInset(")
end = s.index("\n}\n\n}  // namespace", start) + 2
old = s[start:end]
if "getGlyphBitmap" not in old or "advanceX" not in old:
    raise SystemExit("CPHUN-167: regenerated bitmap-measurement helper changed")
new = """// Reconstruct the actual last-glyph ink edge using drawText's pair-level
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
  int dark = -1;
  int any = -1;
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
      if (intensity != 0 && col > any) any = col;
      if (intensity >= 2 && col > dark) dark = col;
    }
  }
  const int lastInk = dark >= 0 ? dark : any;
  if (lastInk < 0) return -1;
  const int glyphAdvance = static_cast<int>((previousAdvanceFP + 8) >> 4);
  const int glyphInkRight = static_cast<int>(lastGlyph->left) + lastInk + 1;
  const int nativeAdvance = nativePen + glyphAdvance;
  const int layoutBaseAdvance = renderer.getTextAdvanceX(fontId, text, style);
  return OpticalLineCorrection::effectiveFinalInkInset(
      plannedAdvance, layoutBaseAdvance, nativeAdvance,
      std::max(0, glyphAdvance - glyphInkRight));
}"""
s = s[:start] + new + s[end:]
old_call = """    opticalInset = renderedFinalInkInset(
        renderer, fontId, wordText(numWords - 1), wordStyle(numWords - 1));"""
new_call = """    opticalInset = renderedFinalWordInkInset(
        renderer, fontId, wordText(numWords - 1), wordStyle(numWords - 1),
        opticalLastWordAdvance_);"""
s = replace_once(s, old_call, new_call, "CPHUN-166 recorded render measurement")
# Tests can detect a regression to the old last-glyph-only calculation.
if "renderedFinalInkInset(" in s:
    raise SystemExit("CPHUN-167: obsolete glyph-only measurement still referenced")
p.write_text(s, encoding="utf-8")

p = Path("lib/Epub/Epub/Section.cpp")
s = p.read_text(encoding="utf-8")
s = replace_once(s, "constexpr uint8_t SECTION_FILE_VERSION = 66;",
                 "// CPHUN-167: invalidate saved lines after full-word ink correction.\n"
                 "constexpr uint8_t SECTION_FILE_VERSION = 67;",
                 "chapter cache version")
p.write_text(s, encoding="utf-8")
print("CPHUN-167: actual pair-kerned full-word right edge, diagnostics and cache v67 applied.")
