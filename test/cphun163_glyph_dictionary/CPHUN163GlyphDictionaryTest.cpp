#include <DictWordEdges.h>
#include <ReaderGlyphFallback.h>
#include <gtest/gtest.h>

#include <cstring>
#include <string>

namespace {
std::string trim(const char* s) {
  const auto [a, b] = DictWordEdges::trim(s);
  return std::string(s + a, b - a);
}
}  // namespace

TEST(CPHUN163DictionaryTest, HungarianGuillemetsWithTrailingComma) {
  EXPECT_EQ("tisztelni", trim("»tisztelni«,"));
  EXPECT_EQ("tisztelni", trim("«tisztelni»"));
  EXPECT_EQ("tisztelni", trim("„»tisztelni«,”"));
}

TEST(CPHUN163DictionaryTest, EnglishAndFrenchQuotationMarks) {
  EXPECT_EQ("hello", trim("“hello,”"));
  EXPECT_EQ("bonjour", trim("«bonjour»"));
  EXPECT_EQ("tisztelni", trim("tisztelni"));
}

TEST(CPHUN163DictionaryTest, InternalPunctuationRemainsUnmodified) {
  EXPECT_EQ("ha-ha", trim("«ha-ha»!"));
  EXPECT_EQ("O’Neill", trim("«O’Neill»"));
  EXPECT_EQ("a«b", trim("«a«b»"));
}

TEST(CPHUN163GlyphFallbackTest, MathematicalMinusUsesPrimaryEnDashWhenPresent) {
  const auto contains = [](uint32_t cp) { return cp == 0x2013; };
  EXPECT_EQ(0x2013u, ReaderGlyphFallback::localSubstitute(0x2212, contains));
}

TEST(CPHUN163GlyphFallbackTest, PreservesNativeMinusOrUnknownGlyphs) {
  const auto containsMinus = [](uint32_t cp) { return cp == 0x2212 || cp == 0x2013; };
  const auto containsNothing = [](uint32_t) { return false; };
  EXPECT_EQ(0x2212u, ReaderGlyphFallback::localSubstitute(0x2212, containsMinus));
  EXPECT_EQ(0x2212u, ReaderGlyphFallback::localSubstitute(0x2212, containsNothing));
  EXPECT_EQ(0x2014u, ReaderGlyphFallback::localSubstitute(0x2014, containsNothing));
}
