#include <ScreenshotSequence.h>
#include <gtest/gtest.h>
#include <cstdint>
#include <cstring>

TEST(CPHUN166ScreenshotSequence, StartsAt0001AndSortsLexicographically) {
  char id[20];
  ScreenshotSequence::formatId(id, sizeof(id), 1);
  EXPECT_STREQ("0001", id);
  ScreenshotSequence::formatId(id, sizeof(id), 10);
  EXPECT_STREQ("0010", id);
  ScreenshotSequence::formatId(id, sizeof(id), 9999);
  EXPECT_STREQ("9999", id);
  ScreenshotSequence::formatId(id, sizeof(id), 10000);
  EXPECT_STREQ("10000", id);
}

TEST(CPHUN166ScreenshotSequence, PersistsAcrossRestart) {
  uint32_t last = 0;
  EXPECT_TRUE(ScreenshotSequence::parseLastReserved("12\n", last));
  uint32_t next = 0;
  ASSERT_TRUE(ScreenshotSequence::next(last, next));
  EXPECT_EQ(13u, next);
  char id[20];
  ScreenshotSequence::formatId(id, sizeof(id), next);
  EXPECT_STREQ("0013", id);
}

TEST(CPHUN166ScreenshotSequence, DoesNotAllowCorruptOrOverflowCounters) {
  uint32_t last = 9;
  EXPECT_FALSE(ScreenshotSequence::parseLastReserved("", last));
  EXPECT_FALSE(ScreenshotSequence::parseLastReserved("-1", last));
  EXPECT_FALSE(ScreenshotSequence::parseLastReserved("12garbage", last));
  EXPECT_FALSE(ScreenshotSequence::parseLastReserved("4294967296", last));
  EXPECT_EQ(9u, last);
  EXPECT_TRUE(ScreenshotSequence::parseLastReserved("4294967295", last));
  uint32_t next = 0;
  EXPECT_FALSE(ScreenshotSequence::next(last, next));
}
