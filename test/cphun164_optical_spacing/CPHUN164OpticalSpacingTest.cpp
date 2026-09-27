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
