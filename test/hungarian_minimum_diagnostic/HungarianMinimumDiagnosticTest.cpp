#include <gtest/gtest.h>

#include <algorithm>
#include <iostream>
#include <string>
#include <vector>

#include "lib/Epub/Epub/hyphenation/HyphenationCommon.h"
#include "lib/Epub/Epub/hyphenation/LanguageHyphenator.h"
#include "lib/Epub/Epub/hyphenation/generated/hyph-hu.trie.h"

namespace {

std::string annotateBreaks(const std::string& word, const std::vector<size_t>& breaks) {
  std::string out;
  auto cps = collectCodepoints(word);
  size_t breakIdx = 0;
  for (size_t i = 0; i < cps.size(); ++i) {
    while (breakIdx < breaks.size() && breaks[breakIdx] == i) {
      out += "-";
      ++breakIdx;
    }
    const size_t begin = cps[i].byteOffset;
    const size_t end = (i + 1 < cps.size()) ? cps[i + 1].byteOffset : word.size();
    out.append(word, begin, end - begin);
  }
  while (breakIdx < breaks.size() && breaks[breakIdx] == cps.size()) {
    out += "-";
    ++breakIdx;
  }
  return out;
}

std::string indexesToString(const std::vector<size_t>& breaks) {
  if (breaks.empty()) return "none";
  std::string out;
  for (size_t i = 0; i < breaks.size(); ++i) {
    if (i) out += ",";
    out += std::to_string(breaks[i]);
  }
  return out;
}

std::vector<size_t> run(const std::string& word, const LanguageHyphenator& hyphenator) {
  auto cps = collectCodepoints(word);
  trimSurroundingPunctuationAndFootnote(cps);
  return hyphenator.breakIndexes(cps);
}

}  // namespace

TEST(HungarianMinimumDiagnostic, PrintSixteenSampleWords) {
  const LanguageHyphenator hu22(hu_patterns, isLatinLetter, toLowerLatin, 2, 2);
  const LanguageHyphenator hu12(hu_patterns, isLatinLetter, toLowerLatin, 1, 2);

  const std::vector<std::string> words = {
      "Anyámnak", "ugyan", "olyan", "alak", "ülök", "eső", "apa", "óda",
      "oda", "ide", "ami", "esze", "elem", "alap", "óra", "akar",
  };

  std::cout << "\nHungarian Liang breakpoint diagnostic\n";
  std::cout << "word | 2/2 indexes | 2/2 annotated | 1/2 indexes | 1/2 annotated | first-break@1\n";
  for (const auto& word : words) {
    const auto b22 = run(word, hu22);
    const auto b12 = run(word, hu12);
    const bool firstBreak = std::find(b12.begin(), b12.end(), 1) != b12.end();
    std::cout << word << " | " << indexesToString(b22) << " | " << annotateBreaks(word, b22)
              << " | " << indexesToString(b12) << " | " << annotateBreaks(word, b12)
              << " | " << (firstBreak ? "YES" : "NO") << "\n";
  }

  SUCCEED();
}
