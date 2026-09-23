#!/usr/bin/env python3
"""CPHUN-150: make optimizer measurement and rendering share pair eligibility,
and make the SD-font layout fast path round native glyph steps like drawText.
Run after CPHUN-149 on a clean checkout.
"""
from pathlib import Path
import re

def replace_once(path, old, new, label):
    p = Path(path)
    s = p.read_text(encoding="utf-8")
    count = s.count(old)
    if count != 1:
        raise SystemExit(f"CPHUN-150 {label}: expected one anchor, found {count}")
    p.write_text(s.replace(old, new, 1), encoding="utf-8")

# Shared zero-extra policy for AA, both gaps of ABA, and boundaries touching
# punctuation or the synthetic U+2011 line-ending hyphen.
p = Path("lib/Epub/Epub/LetterSpacingOptimization.h")
s = p.read_text(encoding="utf-8")
anchor = "inline uint8_t consumeWord(const char* text, const EpdFontFamily::Style style,"
shared = """// Used identically by measuring, positioning and rasterizing a word.
inline uint8_t consumeGuardedPair(const uint32_t beforeLeft, const uint32_t left,
                                  const uint32_t right, const uint32_t afterRight,
                                  const EpdFontFamily::Style style, Accumulator& acc) {
  // Do not charge fractional pixels for blocked pairs.
  if (!isLatinLetter(left) || !isLatinLetter(right) || left == right ||
      (beforeLeft != 0 && beforeLeft == right) ||
      (afterRight != 0 && left == afterRight)) {
    return 0;
  }
  return consumePair(left, right, style, acc);
}

"""
if s.count(anchor) != 1:
    raise SystemExit("CPHUN-150: generated consumeWord signature changed")
s = s.replace(anchor, shared + anchor, 1)
old = """    if (prev && prev != cp && !symmetricLeftGap && !symmetricRightGap) {
      extra = static_cast<uint8_t>(extra + consumePair(prev, cp, style, acc));
    }"""
new = """    if (prev) {
      extra = static_cast<uint8_t>(
          extra + consumeGuardedPair(prevPrev, prev, cp, next, style, acc));
    }"""
if s.count(old) != 1:
    raise SystemExit("CPHUN-150: CPHUN-149 measurement pair logic changed")
s = s.replace(old, new, 1)
s = s.replace(
    """    const bool symmetricLeftGap = prev != 0 && next != 0 && prev == next;
    const bool symmetricRightGap = prevPrev != 0 && prevPrev == cp;
""", "", 1)
p.write_text(s, encoding="utf-8")

# The optimized rasterizer formerly called consumePair directly, losing the
# neighboring-codepoint checks from consumeWord and thus overstretching words.
p = Path("lib/Epub/Epub/blocks/TextBlock.cpp")
s = p.read_text(encoding="utf-8")
start = s.index("  if (optimizeThisWord) {")
end = s.index("\n    return;", start)
block = s[start:end]
if block.count("uint32_t previous = 0;") != 1 or block.count("previous = cp;") != 1:
    raise SystemExit("CPHUN-150: optimized rasterizer state changed")
block = block.replace("uint32_t previous = 0;",
                      "uint32_t previous = 0;\n    uint32_t beforePrevious = 0;", 1)
old_pair = "LetterSpacingOptimization::consumePair(previous, cp, style, *optimizationAcc)"
new_pair = """LetterSpacingOptimization::consumeGuardedPair(
            beforePrevious, previous, cp,
            *cursor ? utf8NextCodepoint(&lookahead) : 0,
            style, *optimizationAcc)"""
if block.count(old_pair) != 1:
    raise SystemExit("CPHUN-150: optimized rasterizer pair call changed")
# A second cursor is essential: the next-codepoint check must not move the
# renderer's current UTF-8 cursor.
block = block.replace("        optimizationOffset += " + old_pair + ";",
    """        const auto* lookahead = cursor;
        optimizationOffset += """ + new_pair + ";", 1)
block = block.replace("      previous = cp;",
                      "      beforePrevious = previous;\n      previous = cp;", 1)
s = s[:start] + block + s[end:]
p.write_text(s, encoding="utf-8")

# SD-card font advance tables formerly rounded the sum of all advances once.
# drawText and the optimized rasterizer snap (preceding advance + pair kerning)
# for each pair, then snap the final advance. Use the same calculation for
# layout, including the same ligature substitution as the normal measure path.
p = Path("lib/GfxRenderer/GfxRenderer.cpp")
s = p.read_text(encoding="utf-8")
start_anchor = "  // Advance table fast-path for SD card fonts during layout."
end_anchor = "\n  const auto fontIt = fontMap.find(resolvedFontId);"
start = s.index(start_anchor, s.index("int GfxRenderer::getTextAdvanceX("))
end = s.index(end_anchor, start)
old_fast = s[start:end]
if "widthFP += isSupSub ? (advFP + 1) / 2 : advFP;" not in old_fast:
    raise SystemExit("CPHUN-150: SD fast path structure changed")
new_fast = """  // SD-card advance-table fast path: match drawText's pair-by-pair 12.4
  // fixed-point rounding instead of rounding the full word once. The loaded
  // font's kerning/ligature metadata is consulted when present; missing
  // metadata returns zero/identity just as drawText does.
  auto sdIt = sdCardFonts_.find(resolvedFontId);
  if (sdIt != sdCardFonts_.end() && sdIt->second->hasAdvanceTable()) {
    const bool isSupSub = (style & (EpdFontFamily::SUP | EpdFontFamily::SUB)) != 0;
    const uint8_t styleIdx = resolveSdCardStyle(*sdIt->second, style);
    const auto fontIt = fontMap.find(resolvedFontId);
    if (fontIt == fontMap.end()) {
      LOG_ERR("GFX", "Font %d not found", resolvedFontId);
      return 0;
    }
    const auto& font = fontIt->second;
    uint32_t previous = 0;
    int32_t previousAdvanceFP = 0;
    int widthPx = 0;
    while (uint32_t cp = utf8NextCodepoint(reinterpret_cast<const uint8_t**>(&text))) {
      if (BidiUtils::isTransparentMark(cp) || utf8IsCombiningMark(cp)) continue;
      cp = font.applyLigatures(cp, text, style);
      int32_t advanceFP = sdIt->second->getAdvance(cp, styleIdx);
      if (advanceFP == 0) {
        const EpdGlyph* glyph = font.getGlyph(cp, style);
        advanceFP = glyph ? glyph->advanceX : 0;
      }
      if (isSupSub) advanceFP = (advanceFP + 1) / 2;
      if (previous != 0) {
        widthPx += fp4::toPixel(previousAdvanceFP + font.getKerning(previous, cp, style));
      }
      previous = cp;
      previousAdvanceFP = advanceFP;
    }
    return widthPx + fp4::toPixel(previousAdvanceFP);
  }
"""
s = s[:start] + new_fast + s[end:]
p.write_text(s, encoding="utf-8")

# Targeted invariants make the CI fail if someone reintroduces separate pair
# rules or single-rounding SD width in a later change.
h = Path("lib/Epub/Epub/LetterSpacingOptimization.h").read_text(encoding="utf-8")
r = Path("lib/Epub/Epub/blocks/TextBlock.cpp").read_text(encoding="utf-8")
g = Path("lib/GfxRenderer/GfxRenderer.cpp").read_text(encoding="utf-8")
assert h.count("consumeGuardedPair(") == 2, "helper + measurement call"
assert r.count("LetterSpacingOptimization::consumeGuardedPair(") == 1, "renderer call"
assert "widthFP += isSupSub ? (advFP + 1) / 2 : advFP;" not in g
assert "widthPx += fp4::toPixel(previousAdvanceFP + font.getKerning(previous, cp, style));" in g
assert "trailingShortHyphenInkShift" in r, "preserve existing optical alignment"

print("CPHUN-150: shared guarded optimizer and drawText-consistent SD measurements applied")
