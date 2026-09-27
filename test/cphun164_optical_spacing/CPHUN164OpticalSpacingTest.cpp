#include <OpticalLineCorrection.h>
#include <gtest/gtest.h>

#include <vector>

namespace {
std::vector<int> allocation(int slots, int pixels) {
  std::vector<int> result;
  for (int i = 0; i < slots; ++i)
    result.push_back(OpticalLineCorrection::extraForSlot(i, slots, pixels));
  return result;
}
}  // namespace

TEST(CPHUN164OpticalSpacing, ExactlyFivePixelsAcrossAllAvailableGaps) {
  EXPECT_EQ((std::vector<int>{1, 1, 1, 1, 1}), allocation(5, 5));
  EXPECT_EQ((std::vector<int>{1, 1, 1, 2}), allocation(4, 5));
  EXPECT_EQ((std::vector<int>{1, 2, 2}), allocation(3, 5));
  EXPECT_EQ((std::vector<int>{2, 3}), allocation(2, 5));
  EXPECT_EQ((std::vector<int>{5}), allocation(1, 5));
  EXPECT_TRUE(allocation(0, 5).empty());
}

TEST(CPHUN164OpticalSpacing, MoreSpacesThanPixelsAreDistributed) {
  EXPECT_EQ((std::vector<int>{0, 1, 0, 1, 0, 1}), allocation(6, 3));
  EXPECT_EQ((std::vector<int>{0, 0, 1, 0, 1}), allocation(5, 2));
}

TEST(CPHUN164OpticalSpacing, StandaloneWordUsesAvailablePixelsWithoutExtraSpace) {
  const auto code = OpticalLineCorrection::encodeStandaloneBudget(7);
  ASSERT_TRUE(OpticalLineCorrection::isStandaloneWordSpacing(code));
  ASSERT_EQ(7, OpticalLineCorrection::standaloneBudget(code));
  int total = 0;
  for (int i = 0; i < 20; ++i)
    total += OpticalLineCorrection::extraForSlot(i, 20, OpticalLineCorrection::standaloneBudget(code));
  EXPECT_EQ(7, total);
  EXPECT_EQ(31, OpticalLineCorrection::encodeStandaloneBudget(99));
  EXPECT_EQ(0, OpticalLineCorrection::encodeStandaloneBudget(0));
}

TEST(CPHUN164OpticalSpacing, PureTrackingAndOptimizerCodesRemainDistinct) {
  EXPECT_FALSE(OpticalLineCorrection::isStandaloneWordSpacing(0));
  EXPECT_FALSE(OpticalLineCorrection::isStandaloneWordSpacing(1));
  EXPECT_FALSE(OpticalLineCorrection::isStandaloneWordSpacing(32));
}

TEST(CPHUN164OpticalSpacing, GuardAAAndBothSidesOfABAWhenOptimizationIsOn) {
  using OpticalLineCorrection::isProtectedPair;
  // meddig: dd; tovább: bb.
  EXPECT_TRUE(isProtectedPair('e', 'd', 'd', 'i'));
  EXPECT_TRUE(isProtectedPair(0x00E1u, 'b', 'b', 0));
  // kerestek: both e-r and r-e in the e-r-e triplet are protected.
  EXPECT_TRUE(isProtectedPair('k', 'e', 'r', 'e'));
  EXPECT_TRUE(isProtectedPair('e', 'r', 'e', 's'));
  // The remaining ordinary word pairs must stay eligible.
  EXPECT_FALSE(isProtectedPair(0, 'k', 'e', 'r'));
  EXPECT_FALSE(isProtectedPair('r', 'e', 's', 't'));
}

TEST(CPHUN164OpticalSpacing, RenderTimeInkClosureAfterBitmapLoad) {
  // Logical advance reaches the right edge, but visible ink ends 3px short.
  EXPECT_EQ(3, OpticalLineCorrection::missingFinalInkPixels(460, 381, 79, 3));
  EXPECT_EQ(5, OpticalLineCorrection::missingFinalInkPixels(460, 381, 79, 8));
  EXPECT_EQ(2, OpticalLineCorrection::missingFinalInkPixels(460, 381, 77, 0));
  EXPECT_EQ(0, OpticalLineCorrection::missingFinalInkPixels(460, 381, 81, 0));
  // Missing/unloaded bitmap is NOT treated as an exact visual alignment.
  EXPECT_EQ(0, OpticalLineCorrection::missingFinalInkPixels(460, 381, 79, -1));
  EXPECT_EQ(0, OpticalLineCorrection::missingFinalInkPixels(0, 381, 79, 3));
}

TEST(CPHUN164OpticalSpacing, MeasuredAdvanceVersusPaintedKerningRegression) {
  // CPHUN-166 measured 137px for "kerestek" but the last glyph's own
  // bitmap reported no inset. Three pixels of cross-pair kerning are enough
  // to make the *full* rendered word three pixels shorter.
  EXPECT_EQ(3, OpticalLineCorrection::effectiveFinalInkInset(137, 137, 134, 0));
  EXPECT_EQ(3, OpticalLineCorrection::missingFinalInkPixels(
      446, 309, 137, OpticalLineCorrection::effectiveFinalInkInset(137, 137, 134, 0)));
  EXPECT_EQ(5, OpticalLineCorrection::effectiveFinalInkInset(137, 137, 128, 5) > 5
                   ? OpticalLineCorrection::missingFinalInkPixels(446, 309, 137,
                       OpticalLineCorrection::effectiveFinalInkInset(137, 137, 128, 5))
                   : 0);
  // Already reserved tracking shifts glyphs and must not count as missing ink.
  EXPECT_EQ(3, OpticalLineCorrection::effectiveFinalInkInset(140, 137, 134, 0));
  EXPECT_EQ(0, OpticalLineCorrection::effectiveFinalInkInset(137, 137, 137, 0));
  EXPECT_EQ(-1, OpticalLineCorrection::effectiveFinalInkInset(137, 138, 134, 0));
}
