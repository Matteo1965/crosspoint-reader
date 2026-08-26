#include <gtest/gtest.h>

#include <algorithm>
#include <string>
#include <vector>

#include "lib/Epub/Epub/hyphenation/Hyphenator.h"

namespace {

size_t firstCodepointByteLength(const std::string& word) {
  const unsigned char lead = static_cast<unsigned char>(word[0]);
  if ((lead & 0x80u) == 0) return 1;
  if ((lead & 0xE0u) == 0xC0u) return 2;
  if ((lead & 0xF0u) == 0xE0u) return 3;
  return 4;
}

bool hasBreakAfterFirstCodepoint(const std::string& word) {
  const size_t expectedOffset = firstCodepointByteLength(word);
  const auto breaks = Hyphenator::breakOffsetsForLanguage(word, false, "hu");
  return std::any_of(breaks.begin(), breaks.end(), [expectedOffset](const Hyphenator::BreakInfo& info) {
    return info.byteOffset == expectedOffset && info.requiresInsertedHyphen;
  });
}

}  // namespace

TEST(HungarianSinglePrefix, RejectsNonSingletonFirstSyllables) {
  const std::vector<std::string> words = {
      "ember", "ablak", "asztal", "iskola", "autó", "akkor", "egyszer",
  };

  for (const auto& word : words) {
    EXPECT_FALSE(hasBreakAfterFirstCodepoint(word)) << word;
  }
}
