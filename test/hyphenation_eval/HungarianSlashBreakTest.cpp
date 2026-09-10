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

TEST(HungarianParentheses, ExtendedRunsLiangInsideBothAlphabeticSegments) {
  Hyphenator::setPreferredLanguage("hu");
  Hyphenator::setHungarianExtended(true);

  const std::string left = "terület";
  const std::string right = "részterület";
  const auto leftBreaks = Hyphenator::breakOffsets(left, false);
  const auto rightBreaks = Hyphenator::breakOffsets(right, false);
  ASSERT_FALSE(leftBreaks.empty());
  ASSERT_FALSE(rightBreaks.empty());

  const std::string prefix = left + "(";
  const std::string combined = prefix + right + ")";
  const auto combinedBreaks = Hyphenator::breakOffsets(combined, false);

  for (const auto& info : leftBreaks) {
    ASSERT_NE(findBreak(combinedBreaks, info.byteOffset), nullptr)
        << "Parenthesis segmentation lost a break in the left segment";
  }
  for (const auto& info : rightBreaks) {
    ASSERT_NE(findBreak(combinedBreaks, prefix.size() + info.byteOffset), nullptr)
        << "Parenthesis segmentation lost a break in the right segment";
  }

  EXPECT_EQ(findBreak(combinedBreaks, left.size()), nullptr)
      << "Do not insert a break directly before '('";
  EXPECT_EQ(findBreak(combinedBreaks, prefix.size()), nullptr)
      << "Do not insert a break directly after '('";

  Hyphenator::setHungarianExtended(false);
}

TEST(HungarianParentheses, BasicDoesNotEnableParenthesisSegmentation) {
  Hyphenator::setPreferredLanguage("hu");
  Hyphenator::setHungarianExtended(false);

  const auto breaks = Hyphenator::breakOffsets("terület(részterület)", false);
  EXPECT_TRUE(breaks.empty()) << "Parenthesis segmentation must remain Hungarian-Extended-only";
}

TEST(HungarianDictionaryHyphenation, ExplicitHungarianEnablesDoubledMultigraphCorrection) {
  Hyphenator::setPreferredLanguage("en");
  Hyphenator::setHungarianExtended(false);

  for (const std::string& word : {std::string("összes"), std::string("mindösszesen")}) {
    const auto breaks = Hyphenator::breakOffsetsForLanguageExtended(word, false, "hu");
    const size_t split = word == "összes" ? std::string("ös").size() : std::string("mindös").size();
    const auto* info = findBreak(breaks, split);
    ASSERT_NE(info, nullptr) << "Missing doubled-sz correction for " << word;
    EXPECT_TRUE(info->requiresInsertedHyphen);
    EXPECT_EQ(info->replacement, Hyphenator::Replacement::AppendZ);
  }

  // The explicit dictionary call must restore the reader's current mode.
  const auto englishModeBreaks = Hyphenator::breakOffsets("összes", false);
  for (const auto& info : englishModeBreaks) {
    EXPECT_NE(info.replacement, Hyphenator::Replacement::AppendZ);
  }
}

TEST(HungarianDictionaryHyphenation, ExplicitHungarianAlsoSegmentsParentheses) {
  Hyphenator::setPreferredLanguage("en");
  Hyphenator::setHungarianExtended(false);

  const std::string left = "terület";
  const std::string right = "részterület";
  const auto rightBreaks = Hyphenator::breakOffsetsForLanguageExtended(right, false, "hu");
  ASSERT_FALSE(rightBreaks.empty());

  const std::string prefix = left + "(";
  const auto combinedBreaks = Hyphenator::breakOffsetsForLanguageExtended(prefix + right + ")", false, "hu");
  for (const auto& info : rightBreaks) {
    ASSERT_NE(findBreak(combinedBreaks, prefix.size() + info.byteOffset), nullptr);
  }
}

TEST(HungarianQuotedSuffix, ExtendedPreservesLiangBreaksBeforeClosingQuoteSuffix) {
  Hyphenator::setPreferredLanguage("hu");
  Hyphenator::setHungarianExtended(true);

  const std::string plain = "tovább";
  const auto plainBreaks = Hyphenator::breakOffsets(plain, false);
  ASSERT_FALSE(plainBreaks.empty()) << "Expected Hungarian Liang breaks inside tovább";

  const std::string quotedSuffix = "tovább”-hoz";
  const auto quotedBreaks = Hyphenator::breakOffsets(quotedSuffix, false);
  for (const auto& plainBreak : plainBreaks) {
    const auto* quoted = findBreak(quotedBreaks, plainBreak.byteOffset);
    ASSERT_NE(quoted, nullptr) << "Closing quote before -hoz blocked a Liang break inside tovább";
    EXPECT_EQ(quoted->requiresInsertedHyphen, plainBreak.requiresInsertedHyphen);
    EXPECT_EQ(quoted->replacement, plainBreak.replacement);
  }

  Hyphenator::setHungarianExtended(false);
}

TEST(HungarianQuotedSuffix, ExtendedKeepsVisibleSuffixHyphenBreak) {
  Hyphenator::setPreferredLanguage("hu");
  Hyphenator::setHungarianExtended(true);

  const std::string word = "tovább”-hoz";
  const size_t suffixBoundary = std::string("tovább”-").size();
  const auto breaks = Hyphenator::breakOffsets(word, false);
  const auto* info = findBreak(breaks, suffixBoundary);
  ASSERT_NE(info, nullptr) << "Expected a legal break after the existing suffix hyphen";
  EXPECT_FALSE(info->requiresInsertedHyphen) << "Existing suffix hyphen must not insert another hyphen";

  Hyphenator::setHungarianExtended(false);
}

TEST(HungarianQuotedSuffix, BasicDoesNotEnableQuotedSuffixNormalization) {
  Hyphenator::setPreferredLanguage("hu");
  Hyphenator::setHungarianExtended(false);

  const std::string plain = "tovább";
  const auto plainBreaks = Hyphenator::breakOffsets(plain, false);
  ASSERT_FALSE(plainBreaks.empty());

  const auto quotedBreaks = Hyphenator::breakOffsets("tovább”-hoz", false);
  for (const auto& plainBreak : plainBreaks) {
    EXPECT_EQ(findBreak(quotedBreaks, plainBreak.byteOffset), nullptr)
        << "Basic Hungarian mode unexpectedly enabled quoted-suffix normalization";
  }
}

TEST(HungarianQuotedSuffix, OtherLanguagesDoNotEnableQuotedSuffixNormalization) {
  Hyphenator::setPreferredLanguage("en");
  Hyphenator::setHungarianExtended(true);

  const auto breaks = Hyphenator::breakOffsets("tovább”-hoz", false);
  EXPECT_TRUE(breaks.empty()) << "Quoted-suffix normalization must remain Hungarian-Extended-only";

  Hyphenator::setHungarianExtended(false);
}