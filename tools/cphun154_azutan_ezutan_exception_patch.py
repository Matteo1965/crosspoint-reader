#!/usr/bin/env python3
"""CPHUN-154: narrowly scoped Hungarian exceptions for azután and ezután.
Apply after the CPHUN-149 and CPHUN-150 patches, before C++ unit tests.
"""
from pathlib import Path

source = Path("lib/Epub/Epub/hyphenation/Hyphenator.cpp")
s = source.read_text(encoding="utf-8")
anchor = "  std::vector<size_t> indexes;\n  if (hyphenator) {\n    indexes = hyphenator->breakIndexes(cps);\n  }\n"
if s.count(anchor) != 1:
    raise SystemExit("CPHUN-154: normal-word Liang anchor changed")

replacement = """  // CPHUN-154: azután / ezután are az/ez + után compounds.
  // Never admit the Liang/single-letter a-zután or e-zután split.
  // Both basic and extended Hungarian modes use these same vetted breaks;
  // keep respecting the selected min-prefix and min-suffix thresholds.
  // Explicit soft/visible hyphens were already handled above and take priority.
  if (preferredLanguageIsHungarian_ && cps.size() == 6 &&
      (toLowerLatin(cps[0].value) == 'a' || toLowerLatin(cps[0].value) == 'e') &&
      toLowerLatin(cps[1].value) == 'z' && toLowerLatin(cps[2].value) == 'u' &&
      toLowerLatin(cps[3].value) == 't' &&
      (cps[4].value == 0x00E1 || cps[4].value == 0x00C1) &&
      toLowerLatin(cps[5].value) == 'n') {
    std::vector<BreakInfo> compoundBreaks;
    const size_t minPrefix = hyphenator ? hyphenator->minPrefix() : LiangWordConfig::kDefaultMinPrefix;
    const size_t minSuffix = hyphenator ? hyphenator->minSuffix() : LiangWordConfig::kDefaultMinSuffix;
    for (const size_t split : {size_t{2}, size_t{3}}) {
      if (split >= minPrefix && cps.size() - split >= minSuffix) {
        compoundBreaks.push_back({byteOffsetForIndex(cps, split), true});
      }
    }
    return compoundBreaks;
  }

"""
s = s.replace(anchor, replacement + anchor, 1)
source.write_text(s, encoding="utf-8")

tests = Path("test/hyphenation_eval/HyphenationEvaluationTest.cpp")
t = tests.read_text(encoding="utf-8")
if "CPHUN154AzutanEzutanCompoundExceptions" in t:
    raise SystemExit("CPHUN-154: tests already present")
t += r"""

TEST(HyphenationEval, CPHUN154AzutanEzutanCompoundExceptions) {
  Hyphenator::setPreferredLanguage("hu");
  struct Case { const char* word; };
  const Case cases[] = {{"azután"}, {"ezután"}, {"Azután"}, {"EZUTÁN"}};
  for (bool extended : {false, true}) {
    Hyphenator::setHungarianExtended(extended);
    for (const auto& tc : cases) {
      for (const auto [prefix, suffix] : {
               std::pair<size_t, size_t>{1, 2},
               std::pair<size_t, size_t>{2, 2},
               std::pair<size_t, size_t>{3, 3}}) {
        Hyphenator::setHungarianMinima(prefix, suffix);
        const auto breaks = Hyphenator::breakOffsets(tc.word, false);
        const auto fallbackBreaks = Hyphenator::breakOffsets(tc.word, true);
        const std::vector<size_t> expected = (prefix == 3) ? std::vector<size_t>{3}
                                                            : std::vector<size_t>{2, 3};
        for (const auto* actual : {&breaks, &fallbackBreaks}) {
          std::vector<size_t> offsets;
          for (const auto& b : *actual) {
            EXPECT_NE(b.byteOffset, 1u) << tc.word << " extended=" << extended;
            EXPECT_TRUE(b.requiresInsertedHyphen) << tc.word;
            offsets.push_back(b.byteOffset);
          }
          EXPECT_EQ(offsets, expected) << tc.word << " extended=" << extended
                                       << " minima=" << prefix << "-" << suffix;
        }
      }
    }
  }
  Hyphenator::setHungarianMinima(2, 2);
  Hyphenator::setHungarianExtended(false);
}
"""
tests.write_text(t, encoding="utf-8")
print("CPHUN-154 azután/ezután exceptions + 24 mode/minima/word tests added")
