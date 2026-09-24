#!/usr/bin/env python3
"""CPHUN-156: gate long-word justification by correction, respect optimizer, and separate packed modes."""
from pathlib import Path
import re

def rep(path, old, new, label):
    p=Path(path); s=p.read_text(encoding="utf-8"); n=s.count(old)
    if n!=1: raise SystemExit(f"CPHUN-156 {label}: expected 1 anchor, found {n}")
    p.write_text(s.replace(old,new,1),encoding="utf-8")

# 1) Reserve threshold-code 7 (111xxxxx) exclusively for the unoptimized
# long-word distributed mode. Codes 1..6 remain the existing optimizer configs.
h=Path("lib/Epub/Epub/LongWordTracking.h")
s=h.read_text(encoding="utf-8")
anchor='namespace LongWordTracking {\n'
insert='''namespace LongWordTracking {
constexpr uint8_t CONFIG_TAG = 0xE0u;       // threshold code 7: never used by normal optimizer
constexpr uint8_t CONFIG_TAG_MASK = 0xE0u;
constexpr uint8_t CONFIG_BUDGET_MASK = 0x1Fu;

inline uint8_t packConfig(const uint8_t pixels) {
  return pixels == 0 ? 0 : static_cast<uint8_t>(CONFIG_TAG | (pixels & CONFIG_BUDGET_MASK));
}
inline bool isConfig(const uint8_t value) {
  return (value & CONFIG_TAG_MASK) == CONFIG_TAG && (value & CONFIG_BUDGET_MASK) != 0;
}
inline uint8_t unpackBudget(const uint8_t value) {
  return isConfig(value) ? static_cast<uint8_t>(value & CONFIG_BUDGET_MASK) : 0;
}
'''
if s.count(anchor)!=1: raise SystemExit("CPHUN-156 LongWordTracking namespace anchor")
s=s.replace(anchor,insert,1)
h.write_text(s,encoding="utf-8")

# 2) Long-word layout policy.
p=Path("lib/Epub/Epub/ParsedText.cpp"); s=p.read_text(encoding="utf-8")
old='''  // CPHUN-155: single long lexical word on a justified, non-final LTR line.
  // Reserve the exact rasterizer budget, at most +1px per letter pair.
  if (lineWordCount == 1 && actualGapCount == 0 &&
      effectiveAlignment == CssTextAlign::Justify && !isLastLine &&
      !blockStyle.isRtl && !hasRtlWord && !focusReadingEnabled &&
      !lineHasRubyAnnotation && spareSpace > 0 && letterSpacingPx == 0) {
    const auto a = LongWordTracking::analyze(lineWords[0].c_str());
    if (a.singleWord && a.letters >= 16 && a.pairs > 0) {
      const int pixels = std::min({spareSpace, static_cast<int>(a.pairs), 127});
      if (pixels > 0) {
        // 0x80 | budget: distributed 1px tracking, serialized by TextBlock.
        letterSpacingPx = static_cast<uint8_t>(0x80 | pixels);
        trackingExtraTotal = pixels;
      }
    }
  }'''
new='''  // CPHUN-156: single long lexical word on a justified, non-final LTR line.
  // This feature follows the user's spacing controls:
  //   correction OFF                 -> disabled
  //   correction ON, optimizer OFF   -> distribute <=1 px over all letter pairs
  //   correction ON, optimizer ON    -> use the normal guarded/score-filtered optimizer
  // Punctuation is excluded by LongWordTracking::analyze().
  if (letterSpacingLimitPercent > 0 && lineWordCount == 1 && actualGapCount == 0 &&
      effectiveAlignment == CssTextAlign::Justify && !isLastLine &&
      !blockStyle.isRtl && !hasRtlWord && !focusReadingEnabled &&
      !lineHasRubyAnnotation && spareSpace > 0 && letterSpacingPx == 0) {
    const auto a = LongWordTracking::analyze(lineWords[0].c_str());
    if (a.singleWord && a.letters >= 16 && a.pairs > 0) {
      if (letterSpacingOptimizationThresholdCode > 0) {
        const auto& optProfile =
            LetterSpacingOptimization::profile(LetterSpacingOptimization::FIXED_PROFILE_LEVEL);
        const uint8_t availableBudget = static_cast<uint8_t>(
            std::min<int>({optProfile.maxPxPerLine, spareSpace,
                           static_cast<int>(LetterSpacingOptimization::PACKED_BUDGET_MASK)}));
        if (availableBudget > 0) {
          const auto pairTable = LetterSpacingOptimization::tableForFontId(fontId);
          const auto fontIt = renderer.getFontMap().find(fontId);
          const uint8_t pointSize =
              fontIt == renderer.getFontMap().end()
                  ? 16
                  : LetterSpacingOptimization::pointSizeForFont(fontIt->second, pairTable);
          LetterSpacingOptimization::Accumulator optAcc(
              letterSpacingOptimizationThresholdCode, availableBudget, pairTable, pointSize);
          trackingExtraTotal = LetterSpacingOptimization::consumeWord(
              lineWords[0].c_str(), lineWordStyles[0], optAcc);
          if (trackingExtraTotal > 0) {
            letterSpacingPx = LetterSpacingOptimization::packConfig(
                letterSpacingOptimizationThresholdCode,
                static_cast<uint8_t>(trackingExtraTotal));
          }
        }
      } else {
        const int pixels = std::min({spareSpace, static_cast<int>(a.pairs),
                                     static_cast<int>(LongWordTracking::CONFIG_BUDGET_MASK)});
        if (pixels > 0) {
          letterSpacingPx = LongWordTracking::packConfig(static_cast<uint8_t>(pixels));
          trackingExtraTotal = pixels;
        }
      }
    }
  }'''
if s.count(old)!=1: raise SystemExit(f"CPHUN-156 long-word policy anchor count={s.count(old)}")
s=s.replace(old,new,1)
p.write_text(s,encoding="utf-8")

# 3) Rasterizer must distinguish the new long-word mode from optimizer packed codes.
p=Path("lib/Epub/Epub/blocks/TextBlock.cpp"); s=p.read_text(encoding="utf-8")
old='''  const bool distributed = (letterSpacingPx & 0x80) != 0;
  const uint8_t budget = letterSpacingPx & 0x7f;
  const uint8_t uniform = distributed ? 0 : letterSpacingPx;'''
new='''  const bool distributed = LongWordTracking::isConfig(letterSpacingPx);
  const uint8_t budget = LongWordTracking::unpackBudget(letterSpacingPx);
  const uint8_t uniform = distributed ? 0 : letterSpacingPx;'''
if s.count(old)!=1: raise SystemExit(f"CPHUN-156 raster config anchor count={s.count(old)}")
s=s.replace(old,new,1)

# Underline/strike width: existing packed optimizer already has its own
# width logic. For the new long-word code, override the measured width *after*
# that logic, before superscript/subscript scaling; never multiply encoded 0xE*
# byte as if it were a pixel value.
normal_anchor='''      if ((currentStyle & (EpdFontFamily::SUP | EpdFontFamily::SUB)) != 0) {'''
normal_extra='''      if (LongWordTracking::isConfig(letterSpacingPx)) {
        lineWidth = renderer.getTextWidth(fontId, word, currentStyle, baseDir) +
                    LongWordTracking::unpackBudget(letterSpacingPx);
      }
'''
# Limit this replacement to the decoration-width block: the same condition
# also occurs in an unrelated rendering path.
decoration_start=s.index("if (EpdFontFamily::hasTextDecoration(currentStyle))")
decoration_end=s.index("// Do not decorate the synthetic em-space",decoration_start)
decoration_block=s[decoration_start:decoration_end]
if decoration_block.count(normal_anchor)!=1:
    raise SystemExit(f"CPHUN-156 decoration-block anchor count={decoration_block.count(normal_anchor)}")
decoration_block=decoration_block.replace(normal_anchor,normal_extra+normal_anchor,1)
s=s[:decoration_start]+decoration_block+s[decoration_end:]
visible_anchor='''        if ((currentStyle & (EpdFontFamily::SUP | EpdFontFamily::SUB)) != 0) {'''
visible_extra='''        if (LongWordTracking::isConfig(letterSpacingPx)) {
          lineWidth = renderer.getTextWidth(fontId, visibleText, currentStyle, baseDir) +
                      LongWordTracking::unpackBudget(letterSpacingPx);
        }
'''
if s.count(visible_anchor)!=1:
    raise SystemExit(f"CPHUN-156 visible decoration anchor count={s.count(visible_anchor)}")
s=s.replace(visible_anchor,visible_extra+visible_anchor,1)
p.write_text(s,encoding="utf-8")

# 4) Regression tests: tag separation and exact distributed budget.
p=Path("test/long_word_tracking/LongWordTrackingTest.cpp"); s=p.read_text(encoding="utf-8")
append=r'''
TEST(LongWordTracking, PackedModeDoesNotCollideWithOptimizerCodes) {
  for (uint8_t code=1; code<=6; ++code) {
    for (uint8_t budget=1; budget<=31; ++budget) {
      const uint8_t optimizerConfig=static_cast<uint8_t>((code<<5)|budget);
      EXPECT_FALSE(LongWordTracking::isConfig(optimizerConfig));
    }
  }
  for (uint8_t budget=1; budget<=31; ++budget) {
    const uint8_t cfg=LongWordTracking::packConfig(budget);
    EXPECT_TRUE(LongWordTracking::isConfig(cfg));
    EXPECT_EQ(LongWordTracking::unpackBudget(cfg),budget);
  }
}

TEST(LongWordTracking, SixPixelExampleIsExactlySixPairs) {
  const auto a=LongWordTracking::analyze("propagandaeszközökből,");
  ASSERT_GE(a.pairs,6u);
  uint32_t placed=0;
  for(uint32_t i=1;i<=a.pairs;++i)
    placed += LongWordTracking::spaceAtPair(i,a.pairs,6) ? 1u : 0u;
  EXPECT_EQ(placed,6u);
}
'''
if "PackedModeDoesNotCollideWithOptimizerCodes" not in s:
    s += append
p.write_text(s,encoding="utf-8")

# 5) Force section cache rebuild and identify firmware clearly.
p=Path("lib/Epub/Epub/Section.cpp"); s=p.read_text(encoding="utf-8")
s,n=re.subn(r'constexpr uint8_t SECTION_FILE_VERSION = (\d+);',
            lambda m:f"constexpr uint8_t SECTION_FILE_VERSION = {int(m.group(1))+1};",s,count=1)
if n!=1: raise SystemExit("CPHUN-156 section version anchor")
p.write_text(s,encoding="utf-8")

p=Path("src/CPHUNBuildId.h"); s=p.read_text(encoding="utf-8")
s,n=re.subn(r'#define CPHUN_BUILD_ID "[^"]+"',
            '#define CPHUN_BUILD_ID "CPHUN-260924-156-LONGWORD-RULES"',s,count=1)
if n!=1: raise SystemExit("CPHUN-156 build id anchor")
p.write_text(s,encoding="utf-8")

# Build-time invariants catch regression before compilation.
pt=Path("lib/Epub/Epub/ParsedText.cpp").read_text(encoding="utf-8")
tb=Path("lib/Epub/Epub/blocks/TextBlock.cpp").read_text(encoding="utf-8")
lh=Path("lib/Epub/Epub/LongWordTracking.h").read_text(encoding="utf-8")
assert "letterSpacingLimitPercent > 0 && lineWordCount == 1" in pt
assert "letterSpacingOptimizationThresholdCode > 0" in pt
assert "LetterSpacingOptimization::consumeWord(" in pt
assert "LongWordTracking::packConfig" in pt
assert "LongWordTracking::isConfig(letterSpacingPx)" in tb
assert "CONFIG_TAG = 0xE0u" in lh
print("CPHUN-156: correction gate + optimizer-aware long-word spacing + collision-free config applied")
