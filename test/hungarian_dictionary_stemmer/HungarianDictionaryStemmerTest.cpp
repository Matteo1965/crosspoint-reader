#include <gtest/gtest.h>

#include <algorithm>
#include <string>
#include <vector>

#include "src/util/HungarianDictionaryStemmer.h"

namespace {
bool containsCandidate(const std::string& word, const std::string& lemma) {
  std::vector<std::string> candidates;
  hungarianStemVariants(word, candidates);
  return std::find(candidates.begin(), candidates.end(), lemma) != candidates.end();
}
} // namespace

TEST(HungarianDictionaryStemmer, IrregularHungarianForms) {
  EXPECT_TRUE(containsCandidate("írtam", "ír"));
  EXPECT_TRUE(containsCandidate("mentünk", "megy"));
  EXPECT_TRUE(containsCandidate("legszebb", "szép"));
}

TEST(HungarianDictionaryStemmer, InflectionsAndPossessives) {
  EXPECT_TRUE(containsCandidate("könyvekből", "könyv"));
  EXPECT_TRUE(containsCandidate("házakban", "ház"));
  EXPECT_TRUE(containsCandidate("igazgatónője", "igazgató"));
}

TEST(HungarianDictionaryStemmer, BoundedCandidateGeneration) {
  std::vector<std::string> candidates;
  hungarianStemVariants("könyvekből", candidates);
  EXPECT_LE(candidates.size(), 128u);
  EXPECT_EQ(std::count(candidates.begin(), candidates.end(), "könyv"), 1);
}
