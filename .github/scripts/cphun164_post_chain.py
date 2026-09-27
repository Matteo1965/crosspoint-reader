#!/usr/bin/env python3
"""CPHUN-164: patch the full tested 152->163 regeneration output.

Run AFTER cphun163_post_chain.py. Abort when any upstream source shape changes:
do not silently build firmware with incompatible width and drawing paths.
"""
from pathlib import Path
import re

def replace_once(path, old, new, label):
    p = Path(path)
    s = p.read_text(encoding="utf-8")
    found = s.count(old)
    if found != 1:
        raise SystemExit(f"CPHUN-164 {label}: expected one source anchor, found {found}")
    p.write_text(s.replace(old, new, 1), encoding="utf-8")

optpath = Path("lib/Epub/Epub/LetterSpacingOptimization.h")
opt = optpath.read_text(encoding="utf-8")
if opt.count('#include "BitterSpacingScores.h"') != 1:
    raise SystemExit("CPHUN-164: generated optimizer missing calibrated Bitter scores")
opt = opt.replace('#include "BitterSpacingScores.h"',
                  '#include "BitterSpacingScores.h"\n#include "OpticalLineCorrection.h"', 1)

guard = """// CPHUN-164: shared AA/ABA zero-extra rule. Called exclusively when
// Betűköz optimalizálás is ON, with the same neighbor context in both the
// measurement and rasterizer paths. The correction-only path is unchanged.
inline uint8_t consumeGuardedPair(const uint32_t beforeLeft, const uint32_t left,
                                  const uint32_t right, const uint32_t afterRight,
                                  const EpdFontFamily::Style style, Accumulator& acc) {
  if (OpticalLineCorrection::isProtectedPair(beforeLeft, left, right, afterRight)) return 0;
  return consumePair(left, right, style, acc);
}

"""
anchor = "inline uint8_t consumeWord(const char* text, const EpdFontFamily::Style style,"
if opt.count(anchor) != 1 or opt.count("inline uint8_t consumeGuardedPair(") != 0:
    raise SystemExit("CPHUN-164: unexpected optimization helper")
opt = opt.replace(anchor, guard + anchor, 1)
old = """  uint32_t prev = 0;
  uint8_t extra = 0;
  while (*cursor) {
    const uint32_t cp = utf8NextCodepoint(&cursor);
    if (!cp) break;
    if (prev) extra = static_cast<uint8_t>(extra + consumePair(prev, cp, style, acc));
    prev = cp;
  }"""
new = """  uint32_t prevPrev = 0;
  uint32_t prev = 0;
  uint8_t extra = 0;
  while (*cursor) {
    const uint32_t cp = utf8NextCodepoint(&cursor);
    if (!cp) break;
    const auto* lookahead = cursor;
    const uint32_t next = *lookahead ? utf8NextCodepoint(&lookahead) : 0;
    if (prev) {
      extra = static_cast<uint8_t>(extra +
          consumeGuardedPair(prevPrev, prev, cp, next, style, acc));
    }
    prevPrev = prev;
    prev = cp;
  }"""
if opt.count(old) != 1:
    raise SystemExit("CPHUN-164: generated consumeWord shape changed")
opt = opt.replace(old, new, 1)
optpath.write_text(opt, encoding="utf-8")

# Rasterization uses exactly the same neighbor-aware helper. This fixes the
# previously existing drift where the regenerated CPHUN-152 renderer called
# consumePair() directly and ignored the guarded measurement helper.
path = Path("lib/Epub/Epub/blocks/TextBlock.cpp")
render = path.read_text(encoding="utf-8")
if render.count('#include "../LetterSpacingOptimization.h"') != 1:
    raise SystemExit("CPHUN-164: TextBlock optimizer include missing")
render = render.replace('#include "../LetterSpacingOptimization.h"',
                        '#include "../LetterSpacingOptimization.h"\n#include "../OpticalLineCorrection.h"', 1)
start = render.index("  if (optimizeThisWord) {")
end = render.index("\n    return;", start)
block = render[start:end]
if block.count("uint32_t previous = 0;") != 1 or block.count("previous = cp;") != 1:
    raise SystemExit("CPHUN-164: optimized drawing state changed")
block = block.replace("uint32_t previous = 0;",
                      "uint32_t previous = 0;\n    uint32_t beforePrevious = 0;", 1)
old_pair = "optimizationOffset += LetterSpacingOptimization::consumePair(previous, cp, style, *optimizationAcc);"
new_pair = """const auto* lookahead = cursor;
        const uint32_t next = *lookahead ? utf8NextCodepoint(&lookahead) : 0;
        optimizationOffset += LetterSpacingOptimization::consumeGuardedPair(
            beforePrevious, previous, cp, next, style, *optimizationAcc);"""
if block.count(old_pair) != 1:
    raise SystemExit("CPHUN-164: optimized rasterizer pair path changed")
block = block.replace(old_pair, new_pair, 1)
block = block.replace("      previous = cp;",
                      "      beforePrevious = previous;\n      previous = cp;", 1)
render = render[:start] + block + render[end:]

# 2..31 encodes a total 1..30 px for a single long word on a no-space line.
# The layout and renderer use the SAME integer-distribution helper. This
# correction-only fallback intentionally does not apply AA/ABA blocking when
# optimization is OFF, as explicitly requested.
start = render.index("  const auto* cursor = reinterpret_cast<const uint8_t*>(text);",
                     render.index("  if (optimizeThisWord) {") + 1)
# Find the LAST plain tracked codepoint loop after the optimized path.
plain_anchor = """  const auto* cursor = reinterpret_cast<const uint8_t*>(text);
  int penX = x;
  uint32_t previous = 0;
  while (*cursor) {"""
if render.count(plain_anchor) != 1:
    raise SystemExit("CPHUN-164: plain tracked renderer shape changed")
plain_new = """  const auto* cursor = reinterpret_cast<const uint8_t*>(text);
  int penX = x;
  uint32_t previous = 0;
  const int standaloneBudget = OpticalLineCorrection::standaloneBudget(letterSpacingPx);
  const int standaloneSlots = standaloneBudget > 0 ? static_cast<int>(countCodepoints(text)) - 1 : 0;
  int standaloneSlot = 0;
  while (*cursor) {"""
render = render.replace(plain_anchor, plain_new, 1)
old = """      penX += renderer.getKerning(fontId, previous, cp, style) + letterSpacingPx;"""
new = """      const int extra = standaloneBudget > 0
          ? OpticalLineCorrection::extraForSlot(standaloneSlot++, standaloneSlots, standaloneBudget)
          : letterSpacingPx;
      penX += renderer.getKerning(fontId, previous, cp, style) + extra;"""
if render.count(old) != 1:
    raise SystemExit("CPHUN-164: plain tracked spacing step changed")
render = render.replace(old, new, 1)
path.write_text(render, encoding="utf-8")

# Post-layout ink-edge correction. CPHUN-123 measured the visible final
# glyph but added up to 3 px into the normal justification budget BEFORE
# measuring the final word. Instead inspect the completed positions and
# distribute at most 5 px over actual, breakable word gaps.
path = Path("lib/Epub/Epub/ParsedText.cpp")
parsed = path.read_text(encoding="utf-8")
if parsed.count('#include "LetterSpacingOptimization.h"') != 1:
    raise SystemExit("CPHUN-164: ParsedText optimizer include missing")
parsed = parsed.replace('#include "LetterSpacingOptimization.h"',
                        '#include "LetterSpacingOptimization.h"\n#include "OpticalLineCorrection.h"', 1)
old = "  // Restrict this first experimental pass to the 1-3 px discrepancy observed\n  // on the Bitter 16 test page; never pull a pathological glyph far outward.\n  return std::clamp(advancePx - inkRightExclusive, 0, 3);"
new = "  // Report the actual final-glyph ink inset, capped at five pixels.\n  return std::clamp(advancePx - inkRightExclusive, 0,\n                    OpticalLineCorrection::MAX_INK_CORRECTION_PX);"
if parsed.count(old) != 1:
    raise SystemExit("CPHUN-164: CPHUN-123 ink-inset cap changed")
parsed = parsed.replace(old, new, 1)
ink_start = parsed.index("  const int trailingInkAllowance =",
                         parsed.index("void ParsedText::extractLine("))
ink_end = parsed.index("\n  // CPHUN-44/45:", ink_start)
old_ink = parsed[ink_start:ink_end]
if "hangingAllowance + trailingInkAllowance" not in old_ink:
    raise SystemExit("CPHUN-164: old premultiplied ink allowance changed")
parsed = parsed[:ink_start] + """  const int spareSpace =
      effectivePageWidth + hangingAllowance - extraStartOffset - extraEndOffset -
      lineWordWidthSum - totalNaturalGaps;
""" + parsed[ink_end:]

# A no-space nonfinal justified line must get internal tracking too. With
# optimization ON use the calibrated guarded-pair accumulator (and its 6px per
# word ceiling). With optimization OFF distribute up to 30 px across ordinary
# character gaps without applying AA/ABA protection.
anchor = "  const int adjustedSpareSpace = spareSpace - hyphenMicroTotal - punctuationMicroTotal - (letterSpacingPx ? trackingExtraTotal : 0);"
if parsed.count(anchor) != 1:
    raise SystemExit("CPHUN-164: post-tracking layout anchor missing")
single_word = """  // CPHUN-164: the ordinary threshold calculation needs word spaces.
  // A single long word alone on a justified line has none, so offer it the
  // available space through its internal letter pairs instead.
  if (letterSpacingPx == 0 && letterSpacingLimitPercent > 0 && spareSpace > 0 &&
      effectiveAlignment == CssTextAlign::Justify && !isLastLine && !blockStyle.isRtl &&
      !hasRtlWord && !focusReadingEnabled && !lineHasRubyAnnotation &&
      actualGapCount == 0 && lineWordCount == 1 &&
      lineWordStyles[0] == EpdFontFamily::REGULAR &&
      LetterSpacingOptimization::isLatinLetter(lastCodepoint(lineWords[0]))) {
    const int pairs = static_cast<int>(countCodepoints(lineWords[0])) - 1;
    if (pairs >= 5) {
      if (letterSpacingOptimizationThresholdCode > 0) {
        const auto pairTable = LetterSpacingOptimization::tableForFontId(fontId);
        const auto fontIt = renderer.getFontMap().find(fontId);
        const uint8_t pointSize = fontIt == renderer.getFontMap().end()
            ? 16 : LetterSpacingOptimization::pointSizeForFont(fontIt->second, pairTable);
        const auto& profile = LetterSpacingOptimization::profile(
            LetterSpacingOptimization::FIXED_PROFILE_LEVEL);
        LetterSpacingOptimization::Accumulator optAcc(
            letterSpacingOptimizationThresholdCode,
            static_cast<uint8_t>(std::min<int>(spareSpace, profile.maxPxPerLine)),
            pairTable, pointSize);
        const int extra = LetterSpacingOptimization::consumeWord(
            lineWords[0].c_str(), lineWordStyles[0], optAcc);
        if (extra > 0) {
          trackingExtraTotal = extra;
          letterSpacingPx = LetterSpacingOptimization::packConfig(
              letterSpacingOptimizationThresholdCode, static_cast<uint8_t>(extra));
        }
      } else {
        const int extra = std::min<int>({30, spareSpace, pairs});
        if (extra > 0) {
          trackingExtraTotal = extra;
          letterSpacingPx = OpticalLineCorrection::encodeStandaloneBudget(extra);
        }
      }
    }
  }
"""
parsed = parsed.replace(anchor, single_word + anchor, 1)

# Remember the final word's *actual* tracked advance, not an estimate based
# on number of codepoints. The extra pixels are already included in layout.
anchor = """  std::vector<int16_t> lineXPos;
  lineXPos.reserve(lineWordCount);"""
new = anchor + "\n  int lastWordTrackingExtra = 0;"
if parsed.count(anchor) != 1:
    raise SystemExit("CPHUN-164: final line position vector changed")
parsed = parsed.replace(anchor, new, 1)
start = parsed.index("      for (size_t wordIdx = 0; wordIdx < lineWordCount; wordIdx++) {",
                     parsed.index("const auto positionPairTable ="))
end = parsed.index("        if (wordIdx > 0 && hyphenMicroRemaining", start)
segment = parsed[start:end]
if segment.count("const int wordTrackingExtra =") != 1:
    raise SystemExit("CPHUN-164: tracking positioning expression changed")
old = """: (letterSpacingPx
                       ? static_cast<int>(
                             std::max<uint32_t>(1, countCodepoints(lineWords[wordIdx])) - 1) *
                             letterSpacingPx
                       : 0);"""
new = """: (OpticalLineCorrection::isStandaloneWordSpacing(letterSpacingPx)
                       ? OpticalLineCorrection::standaloneBudget(letterSpacingPx)
                       : (letterSpacingPx
                            ? static_cast<int>(
                                  std::max<uint32_t>(1, countCodepoints(lineWords[wordIdx])) - 1) *
                                  letterSpacingPx
                            : 0));"""
if segment.count(old) != 1:
    raise SystemExit("CPHUN-164: unoptimized positioning expression changed")
segment = segment.replace(old, new, 1)
segment += "        if (wordIdx + 1 == lineWordCount) lastWordTrackingExtra = wordTrackingExtra;\n"
parsed = parsed[:start] + segment + parsed[end:]

# The eligible positions are the same token boundaries used by the ordinary
# justification algorithm. A single eligible gap receives the full 5 px; with
# two eligible gaps the distribution is 2+3, etc. Recompute the terminal ink
# coordinate after ALL tracking and space adjustments, not before.
marker = "  const auto focusBoundaryAt = [&](const size_t idx) {"
if parsed.count(marker) != 1:
    raise SystemExit("CPHUN-164: line end / focus block boundary changed")
closure = """  // CPHUN-164: final visible-ink closure (never an EPUB-text modification).
  // Inline punctuation and short hyphens keep the earlier hanging rules.
  if (!willReorder && !isLastLine && effectiveAlignment == CssTextAlign::Justify &&
      !blockStyle.isRtl && !hasRtlWord && !focusReadingEnabled &&
      !lineHasRubyAnnotation && hangingAllowance == 0 &&
      actualGapCount > 0 && !lineWords.empty() && lineXPos.size() == lineWords.size() &&
      LetterSpacingOptimization::isLatinLetter(lastCodepoint(lineWords.back()))) {
    const auto lastFontIt = renderer.getFontMap().find(fontId);
    if (lastFontIt != renderer.getFontMap().end() &&
        lastFontIt->second.hasCodepoint(lastCodepoint(lineWords.back()), lineWordStyles.back())) {
      const int lastWidth = renderer.getTextAdvanceX(
          fontId, lineWords.back().c_str(), lineWordStyles.back()) + lastWordTrackingExtra;
      const int inkInset = trailingStrongInkInset(
          renderer, fontId, lineWords.back(), lineWordStyles.back());
      const int visibleRight = static_cast<int>(lineXPos.back()) + lastWidth - inkInset;
      const int extra = std::clamp(pageWidth - visibleRight, 0,
                                   OpticalLineCorrection::MAX_INK_CORRECTION_PX);
      if (extra > 0) {
        size_t eligibleCount = 0;
        for (size_t i = 1; i < lineWordCount; ++i) {
          if (TokenBoundary::isJustifiableGap(
                  continuesVec[lastBreakAt + i], noSpaceBeforeVec[lastBreakAt + i],
                  lineWords[i] == " ")) {
            ++eligibleCount;
          }
        }
        if (eligibleCount > 0) {
          int passed = 0;
          int cumulative = 0;
          for (size_t i = 0; i < lineWordCount; ++i) {
            if (i > 0 && TokenBoundary::isJustifiableGap(
                    continuesVec[lastBreakAt + i], noSpaceBeforeVec[lastBreakAt + i],
                    lineWords[i] == " ")) {
              cumulative += OpticalLineCorrection::extraForSlot(
                  passed++, static_cast<int>(eligibleCount), extra);
            }
            lineXPos[i] = static_cast<int16_t>(lineXPos[i] + cumulative);
          }
        }
      }
    }
  }

"""
parsed = parsed.replace(marker, closure + marker, 1)
path.write_text(parsed, encoding="utf-8")

# Both final and partial page caches must change together; the original format
# computes the partial sentinel from SECTION_FILE_VERSION automatically.
path = Path("lib/Epub/Epub/Section.cpp")
section = path.read_text(encoding="utf-8")
marker = "// CPHUN-164: guarded optimization and five-pixel ink-edge positions."
if marker not in section:
    version = re.search(r"(?m)^(constexpr uint8_t SECTION_FILE_VERSION = )(\d+)(;)$", section)
    if not version:
        raise SystemExit("CPHUN-164: section cache version definition changed")
    number = int(version.group(2))
    if number >= 220:
        raise SystemExit("CPHUN-164: no safe section cache version remains")
    section = section[:version.start()] + marker + "\n" + version.group(1) + \
        str(number + 1) + version.group(3) + section[version.end():]
    path.write_text(section, encoding="utf-8")
    print(f"CPHUN-164: section cache v{number} -> v{number+1}")

# CI source assertions supplement the native tests and fail closed if an older
# generated code path reappears in either rasterizer or measurement.
opt = optpath.read_text(encoding="utf-8")
render = Path("lib/Epub/Epub/blocks/TextBlock.cpp").read_text(encoding="utf-8")
parsed = Path("lib/Epub/Epub/ParsedText.cpp").read_text(encoding="utf-8")
assert opt.count("consumeGuardedPair(") == 2
assert render.count("LetterSpacingOptimization::consumeGuardedPair(") == 1
assert "LetterSpacingOptimization::consumePair(previous, cp, style, *optimizationAcc)" not in render
assert "OpticalLineCorrection::extraForSlot" in render and "OpticalLineCorrection::extraForSlot" in parsed
assert "lastWordTrackingExtra = wordTrackingExtra" in parsed
assert "MAX_INK_CORRECTION_PX" in parsed
assert "letterSpacingOptimizationThresholdCode > 0" in parsed
print("CPHUN-164: no-gap words, ON-only AA/ABA and final 5px distributed ink closure patched.")
