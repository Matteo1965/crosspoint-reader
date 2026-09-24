#!/usr/bin/env python3
"""CPHUN-155: bounded, exactly measured long-word tracking on one-word justified lines."""
from pathlib import Path
import re

def replace_one(path,old,new):
 p=Path(path);s=p.read_text(encoding="utf-8")
 if s.count(old)!=1: raise SystemExit("CPHUN-155 missing or duplicate anchor "+path+": "+old[:70])
 p.write_text(s.replace(old,new,1),encoding="utf-8")

Path("lib/Epub/Epub/LongWordTracking.h").write_text(r'''#pragma once
#include <Utf8.h>
#include <cstdint>
namespace LongWordTracking {
inline bool isLatinLetter(uint32_t cp) {
 return (cp >= 'A' && cp <= 'Z') || (cp >= 'a' && cp <= 'z') ||
        (cp >= 0x00C0 && cp <= 0x00D6) || (cp >= 0x00D8 && cp <= 0x00F6) ||
        (cp >= 0x00F8 && cp <= 0x02FF);
}
struct Analysis { uint32_t letters=0; uint32_t pairs=0; bool singleWord=true; };
inline Analysis analyze(const char* text) {
 Analysis a;
 if (!text) return a;
 auto* p=reinterpret_cast<const uint8_t*>(text);
 bool previous=false, seen=false, suffix=false;
 while (*p) {
   uint32_t cp=utf8NextCodepoint(&p);
   if (!cp) break;
   bool letter=isLatinLetter(cp);
   if (letter) {
     if (suffix) a.singleWord=false;
     ++a.letters;
     if (previous) ++a.pairs;
     seen=true;
   } else if (seen) suffix=true;
   previous=letter;
 }
 return a;
}
inline bool spaceAtPair(uint32_t i,uint32_t pairs,uint32_t pixels) {
 return pairs>0 && i>0 && i<=pairs &&
        (i*pixels/pairs)>((i-1)*pixels/pairs);
}
} // namespace LongWordTracking
''',encoding="utf-8")

parsed="lib/Epub/Epub/ParsedText.cpp"
replace_one(parsed,'#include "TokenBoundary.h"\n','#include "LongWordTracking.h"\n#include "TokenBoundary.h"\n')
anchor='  const int adjustedSpareSpace = spareSpace - hyphenMicroTotal - punctuationMicroTotal - (letterSpacingPx ? trackingExtraTotal : 0);'
new='''  // CPHUN-155: single long lexical word on a justified, non-final LTR line.
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
  }
  const int adjustedSpareSpace = spareSpace - hyphenMicroTotal - punctuationMicroTotal -
                                 (letterSpacingPx ? trackingExtraTotal : 0);'''
replace_one(parsed,anchor,new)

block="lib/Epub/Epub/blocks/TextBlock.cpp"
replace_one(block,'#include "../ParsedText.h"\n','#include "../LongWordTracking.h"\n#include "../ParsedText.h"\n')
replace_one(block,'''  const bool adjustTrailingHyphen = alignTrailingShortHyphenInk && endsWithShortHyphen(text);
  if (letterSpacingPx == 0) {''','''  const bool distributed = (letterSpacingPx & 0x80) != 0;
  const uint8_t budget = letterSpacingPx & 0x7f;
  const uint8_t uniform = distributed ? 0 : letterSpacingPx;
  const auto a = distributed ? LongWordTracking::analyze(text) : LongWordTracking::Analysis{};
  uint32_t eligibleIndex = 0;
  const bool adjustTrailingHyphen = alignTrailingShortHyphenInk && endsWithShortHyphen(text);
  if (letterSpacingPx == 0) {''')
replace_one(block,'''    if (previous != 0) {
      penX += renderer.getKerning(fontId, previous, cp, style) + letterSpacingPx;
    }''','''    if (previous != 0) {
      int extra = uniform;
      if (distributed && LongWordTracking::isLatinLetter(previous) &&
          LongWordTracking::isLatinLetter(cp)) {
        ++eligibleIndex;
        extra = LongWordTracking::spaceAtPair(eligibleIndex, a.pairs, budget) ? 1 : 0;
      }
      penX += renderer.getKerning(fontId, previous, cp, style) + extra;
    }''')
# An altered TextBlock must invalidate saved page cache after firmware update.
sec=Path("lib/Epub/Epub/Section.cpp");s=sec.read_text(encoding="utf-8")
s,n=re.subn(r'constexpr uint8_t SECTION_FILE_VERSION = (\d+);',
 lambda m:'constexpr uint8_t SECTION_FILE_VERSION = '+str(int(m.group(1))+1)+';',s,count=1)
if n!=1:raise SystemExit("CPHUN-155 cache version anchor missing")
sec.write_text(s,encoding="utf-8")

t=Path("test/long_word_tracking");t.mkdir(parents=True,exist_ok=True)
(t/"CMakeLists.txt").write_text('''add_executable(LongWordTrackingTest LongWordTrackingTest.cpp
  @REPO_ROOT@/lib/Utf8/Utf8.cpp)
target_include_directories(LongWordTrackingTest PRIVATE @REPO_ROOT@/lib/Utf8)
target_link_libraries(LongWordTrackingTest PRIVATE crosspoint_test_common GTest::gtest_main)
gtest_discover_tests(LongWordTrackingTest)
'''.replace("@REPO_ROOT@",chr(36)+"{REPO_ROOT}"),encoding="utf-8")
(t/"LongWordTrackingTest.cpp").write_text(r'''#include <gtest/gtest.h>
#include "lib/Epub/Epub/LongWordTracking.h"
TEST(LongWordTracking, TrailingPunctuationDoesNotCount) {
 const auto a=LongWordTracking::analyze("propagandaeszközökből,");
 EXPECT_TRUE(a.singleWord);
 EXPECT_GE(a.letters,16u);
 EXPECT_EQ(a.pairs,a.letters-1);
 EXPECT_EQ(LongWordTracking::analyze("rövid,").letters,5u);
 EXPECT_FALSE(LongWordTracking::analyze("két-hosszúszó").singleWord);
}
TEST(LongWordTracking, ExactPixelBudget) {
 for(uint32_t pairs:{15u,20u,40u}) {
  for(uint32_t budget=0;budget<=pairs;++budget) {
   uint32_t sum=0;
   for(uint32_t i=1;i<=pairs;++i) sum+=LongWordTracking::spaceAtPair(i,pairs,budget);
   EXPECT_EQ(sum,budget);
  }
 }
}
TEST(LongWordTracking, OnlyLetterPairsEligible) {
 const auto a=LongWordTracking::analyze("„propagandaeszközökből,”");
 EXPECT_TRUE(a.singleWord);
 EXPECT_EQ(a.pairs,a.letters-1);
}
''',encoding="utf-8")
c=Path("test/CMakeLists.txt");s=c.read_text(encoding="utf-8")
if "add_subdirectory(long_word_tracking)" not in s:
 c.write_text(s+"\nadd_subdirectory(long_word_tracking)\n",encoding="utf-8")
bid=Path("src/CPHUNBuildId.h");s=bid.read_text(encoding="utf-8")
s,n=re.subn(r'#define CPHUN_BUILD_ID "[^"]+"','#define CPHUN_BUILD_ID "CPHUN-260924-155-EXP"',s,count=1)
if n!=1:raise SystemExit("CPHUN-155 build id missing")
bid.write_text(s,encoding="utf-8")
print("CPHUN-155: long single-word tracking patch, cache invalidation and tests applied")
