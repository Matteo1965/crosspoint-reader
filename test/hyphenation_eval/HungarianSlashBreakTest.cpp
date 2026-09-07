#include <gtest/gtest.h>

#include <algorithm>
#include <string>
#include <vector>

#include "lib/Epub/Epub/hyphenation/Hyphenator.h"

namespace {

const Hyphenator::BreakInfo* findBreak(const std::vector<Hyphenator::BreakInfo>& breaks, const size_t byteOffset) {
  const auto it = std::find_if(breaks.begin(), breaks.end(), [byteOffset](const Hyphenator::BreakInfo& info) {
    return info.byteOffset == byteOffset;
  });
  return it == breaks.end() ? nullptr : &*it;
}

void expectVisibleSeparatorBreak(const std::vector<Hyphenator::BreakInfo>& breaks, const size_t byteOffset) {
  const auto* info = findBreak(breaks, byteOffset);
  ASSERT_NE(info, nullptr) << "Missing break at byte offset " << byteOffset;
  EXPECT_FALSE(info->requiresInsertedHyphen) << "Visible slash must not insert an extra hyphen";
  EXPECT_EQ(info->replacement, Hyphenator::Replacement::None);
}

}  // namespace

TEST(HungarianSlashBreak, ExtendedAllowsEsVagy) {
  Hyphenator::setPreferredLanguage("hu");
  Hyphenator::setHungarianExtended(true);

  const std::string word = "és/vagy";
  const auto breaks = Hyphenator::breakOffsets(word, false);
  expectVisibleSeparatorBreak(breaks, std::string("és/").size());

  Hyphenator::setHungarianExtended(false);
}

TEST(HungarianSlashBreak, ExtendedAllowsMultipleSlashBoundaries) {
  Hyphenator::setPreferredLanguage("hu");
  Hyphenator::setHungarianExtended(true);

  const std::string word = "napok/hetek/hónapok";
  const auto breaks = Hyphenator::breakOffsets(word, false);
  expectVisibleSeparatorBreak(breaks, std::string("napok/").size());
  expectVisibleSeparatorBreak(breaks, std::string("napok/hetek/").size());

  Hyphenator::setHungarianExtended(false);
}

TEST(HungarianSlashBreak, BasicDoesNotAddSlashBoundary) {
  Hyphenator::setPreferredLanguage("hu");
  Hyphenator::setHungarianExtended(false);

  const std::string word = "és/vagy";
  const size_t slashBoundary = std::string("és/").size();
  const auto breaks = Hyphenator::breakOffsets(word, false);
  const auto* info = findBreak(breaks, slashBoundary);
  EXPECT_TRUE(info == nullptr || info->requiresInsertedHyphen)
      << "Basic Hungarian mode must not add a visible-separator slash break";
}

TEST(HungarianSlashBreak, OtherLanguagesDoNotGainSlashBoundary) {
  Hyphenator::setPreferredLanguage("en");
  Hyphenator::setHungarianExtended(true);

  const std::string word = "and/or";
  const size_t slashBoundary = std::string("and/").size();
  const auto breaks = Hyphenator::breakOffsets(word, false);
  const auto* info = findBreak(breaks, slashBoundary);
  EXPECT_TRUE(info == nullptr || info->requiresInsertedHyphen)
      << "Slash handling must remain Hungarian-Extended-only";

  Hyphenator::setHungarianExtended(false);
}

TEST(HungarianSlashBreak, LiangStillRunsInsideSlashSegments) {
  Hyphenator::setPreferredLanguage("hu");
  Hyphenator::setHungarianExtended(true);

  const std::string segment = "hónapok";
  const auto segmentBreaks = Hyphenator::breakOffsets(segment, false);
  ASSERT_FALSE(segmentBreaks.empty()) << "Expected Hungarian Liang breaks inside hónapok";

  const std::string prefix = "napok/";
  const auto combinedBreaks = Hyphenator::breakOffsets(prefix + segment, false);
  for (const auto& segmentBreak : segmentBreaks) {
    const auto* combined = findBreak(combinedBreaks, prefix.size() + segmentBreak.byteOffset);
    ASSERT_NE(combined, nullptr) << "Slash segmentation lost an internal Hungarian break";
    EXPECT_EQ(combined->requiresInsertedHyphen, segmentBreak.requiresInsertedHyphen);
    EXPECT_EQ(combined->replacement, segmentBreak.replacement);
  }

  Hyphenator::setHungarianExtended(false);
}

TEST(HungarianSlashBreak, NumericHyphenRegressionRemainsValid) {
  Hyphenator::setPreferredLanguage("hu");
  Hyphenator::setHungarianExtended(true);

  for (const std::string word : {std::string("2007-ben"), std::string("5-ös")}) {
    const size_t boundary = word.find('-') + 1;
    const auto breaks = Hyphenator::breakOffsets(word, false);
    const auto* info = findBreak(breaks, boundary);
    ASSERT_NE(info, nullptr) << "Existing numeric-prefix hyphen break regressed for " << word;
    EXPECT_FALSE(info->requiresInsertedHyphen) << word;
  }

  Hyphenator::setHungarianExtended(false);
}
