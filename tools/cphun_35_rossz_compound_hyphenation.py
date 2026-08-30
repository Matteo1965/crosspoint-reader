from pathlib import Path

HY = Path('lib/Epub/Epub/hyphenation/Hyphenator.cpp')
TEST = Path('test/hyphenation_eval/HyphenationEvaluationTest.cpp')
BUILD = Path('src/CPHUNBuildId.h')

hy = HY.read_text(encoding='utf-8')
old = '    {U"arc", U"csont"},       {U"szín", U"nyom"},        {U"tánc", U"csoport"},\n};'
new = '    {U"arc", U"csont"},       {U"szín", U"nyom"},        {U"tánc", U"csoport"},\n    {U"rossz", U"indulat"},    {U"rossz", U"íz"},\n};'
if old not in hy:
    raise SystemExit('CPHUN-35: compound rule anchor not found')
hy = hy.replace(old, new, 1)
HY.write_text(hy, encoding='utf-8')

build = BUILD.read_text(encoding='utf-8')
if 'CPHUN-260830-34' not in build:
    raise SystemExit('CPHUN-35: expected CPHUN-34 build id not found')
BUILD.write_text(build.replace('CPHUN-260830-34', 'CPHUN-260830-35', 1), encoding='utf-8')

test = TEST.read_text(encoding='utf-8')
anchor = 'TEST(HyphenationEval, HungarianGenuineDoubledDigraphsRemainExtended) {'
if anchor not in test:
    raise SystemExit('CPHUN-35: test insertion anchor not found')
extra = r'''
TEST(HyphenationEval, HungarianRosszCompoundBoundaries) {
  struct CompoundCase {
    const char* word;
    const char* left;
  };
  static constexpr CompoundCase cases[] = {
      {"rosszindulatú", "rossz"},
      {"rosszízű", "rossz"},
  };

  Hyphenator::setPreferredLanguage("hu");
  Hyphenator::setHungarianExtended(true);

  for (const auto& tc : cases) {
    const size_t expectedOffset = std::string(tc.left).size();
    const auto breaks = Hyphenator::breakOffsets(tc.word, false);
    const auto it = std::find_if(breaks.begin(), breaks.end(), [expectedOffset](const Hyphenator::BreakInfo& info) {
      return info.byteOffset == expectedOffset;
    });
    ASSERT_NE(it, breaks.end()) << "Missing rossz compound boundary for " << tc.word;
    EXPECT_TRUE(it->requiresInsertedHyphen) << tc.word;
    EXPECT_EQ(it->replacement, Hyphenator::Replacement::None) << "Replacement break leaked into " << tc.word;
  }

  Hyphenator::setHungarianExtended(false);
}

TEST(HyphenationEval, HungarianRosszNonCompoundControls) {
  static constexpr const char* controls[] = {
      "rosszul", "rosszaság", "rossznak", "rosszból", "rossztól", "rosszban", "rosszullét",
  };

  Hyphenator::setPreferredLanguage("hu");
  Hyphenator::setHungarianExtended(true);

  for (const char* word : controls) {
    const auto breaks = Hyphenator::breakOffsets(word, false);
    const size_t forbiddenCompoundOffset = std::string("rossz").size();
    const auto it = std::find_if(breaks.begin(), breaks.end(), [forbiddenCompoundOffset](const Hyphenator::BreakInfo& info) {
      return info.byteOffset == forbiddenCompoundOffset && info.replacement == Hyphenator::Replacement::None;
    });
    EXPECT_EQ(it, breaks.end()) << "Overbroad rossz+... compound rule matched " << word;
  }

  Hyphenator::setHungarianExtended(false);
}

'''
test = test.replace(anchor, extra + anchor, 1)
TEST.write_text(test, encoding='utf-8')
