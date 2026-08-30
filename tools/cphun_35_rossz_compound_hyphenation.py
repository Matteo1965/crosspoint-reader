from pathlib import Path

HY = Path('lib/Epub/Epub/hyphenation/Hyphenator.cpp')
TEST = Path('test/hyphenation_eval/HyphenationEvaluationTest.cpp')
BUILD = Path('src/CPHUNBuildId.h')

hy = HY.read_text(encoding='utf-8')

# Add the two CPHUN-35 compound families when running from the CPHUN-34 base.
if '{U"rossz", U"indulat"}' not in hy:
    old = '    {U"arc", U"csont"},       {U"szín", U"nyom"},        {U"tánc", U"csoport"},\n};'
    new = '    {U"arc", U"csont"},       {U"szín", U"nyom"},        {U"tánc", U"csoport"},\n    {U"rossz", U"indulat"},    {U"rossz", U"íz"},\n};'
    if old not in hy:
        raise SystemExit('CPHUN-35: compound rule anchor not found')
    hy = hy.replace(old, new, 1)

# A verified compound can contain a compact doubled digraph inside its left component.
# Example: rosszízű has a valid compound boundary at rossz|ízű, but the compact "ssz"
# must not additionally create rosz-szízű. Suppress only replacement breaks that fall
# strictly inside the verified left component; genuine standalone forms remain unchanged.
if 'isInsideHungarianCompoundLeft' not in hy:
    anchor = '''bool isHungarianCompoundBoundary(const std::vector<CodepointInfo>& cps, const size_t split) {
  for (const auto& rule : kHungarianCompoundStemRules) {
    const size_t leftLength = utf32Length(rule.left);
    if (split != leftLength) continue;
    if (!matchesHungarianStem(cps, 0, rule.left)) continue;
    if (matchesHungarianStem(cps, split, rule.rightStem)) return true;
  }
  return false;
}
'''
    replacement = anchor + '''\nbool isInsideHungarianCompoundLeft(const std::vector<CodepointInfo>& cps, const size_t split) {
  for (const auto& rule : kHungarianCompoundStemRules) {
    const size_t leftLength = utf32Length(rule.left);
    if (split >= leftLength) continue;
    if (!matchesHungarianStem(cps, 0, rule.left)) continue;
    if (matchesHungarianStem(cps, leftLength, rule.rightStem)) return true;
  }
  return false;
}
'''
    if anchor not in hy:
        raise SystemExit('CPHUN-35: compound boundary helper anchor not found')
    hy = hy.replace(anchor, replacement, 1)

old_guard = '''      if (isHungarianCompoundBoundary(cps, split)) continue;
      // Secondary readability guard: both rendered word parts must contain a vowel.
'''
new_guard = '''      if (isHungarianCompoundBoundary(cps, split) || isInsideHungarianCompoundLeft(cps, split)) continue;
      // Secondary readability guard: both rendered word parts must contain a vowel.
'''
if old_guard in hy:
    hy = hy.replace(old_guard, new_guard, 1)
elif new_guard not in hy:
    raise SystemExit('CPHUN-35: extended replacement guard anchor not found')

HY.write_text(hy, encoding='utf-8')

build = BUILD.read_text(encoding='utf-8')
if 'CPHUN-260830-34' in build:
    build = build.replace('CPHUN-260830-34', 'CPHUN-260830-35', 1)
elif 'CPHUN-260830-35' not in build:
    raise SystemExit('CPHUN-35: expected build id not found')
BUILD.write_text(build, encoding='utf-8')

test = TEST.read_text(encoding='utf-8')
anchor = 'TEST(HyphenationEval, HungarianGenuineDoubledDigraphsRemainExtended) {'
if anchor not in test:
    raise SystemExit('CPHUN-35: test insertion anchor not found')

if 'TEST(HyphenationEval, HungarianRosszCompoundBoundaries)' not in test:
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

TEST(HyphenationEval, HungarianRosszInflectionControls) {
  struct InflectedCase {
    const char* word;
    const char* left;
  };
  static constexpr InflectedCase cases[] = {
      {"rossznak", "rossz"},
      {"rosszból", "rossz"},
      {"rossztól", "rossz"},
      {"rosszban", "rossz"},
  };

  Hyphenator::setPreferredLanguage("hu");
  Hyphenator::setHungarianExtended(true);

  for (const auto& tc : cases) {
    const size_t expectedOffset = std::string(tc.left).size();
    const auto breaks = Hyphenator::breakOffsets(tc.word, false);
    const auto it = std::find_if(breaks.begin(), breaks.end(), [expectedOffset](const Hyphenator::BreakInfo& info) {
      return info.byteOffset == expectedOffset;
    });
    ASSERT_NE(it, breaks.end()) << "Missing normal inflection break for " << tc.word;
    EXPECT_TRUE(it->requiresInsertedHyphen) << tc.word;
    EXPECT_EQ(it->replacement, Hyphenator::Replacement::None) << "Unexpected replacement break in " << tc.word;
  }

  Hyphenator::setHungarianExtended(false);
}

'''
    test = test.replace(anchor, extra + anchor, 1)

# Strengthen the compound test: no replacement break may remain inside the verified
# left component (this is the exact regression that rendered rosszízű as rosz-szízű).
marker = 'Unexpected internal replacement break in rossz compound'
if marker not in test:
    old_assert = '''    EXPECT_EQ(it->replacement, Hyphenator::Replacement::None) << "Replacement break leaked into " << tc.word;
  }

  Hyphenator::setHungarianExtended(false);
}

TEST(HyphenationEval, HungarianRosszInflectionControls)'''
    new_assert = '''    EXPECT_EQ(it->replacement, Hyphenator::Replacement::None) << "Replacement break leaked into " << tc.word;
    const auto internalReplacement = std::find_if(
        breaks.begin(), breaks.end(), [expectedOffset](const Hyphenator::BreakInfo& info) {
          return info.byteOffset < expectedOffset && info.replacement != Hyphenator::Replacement::None;
        });
    EXPECT_EQ(internalReplacement, breaks.end()) << "Unexpected internal replacement break in rossz compound " << tc.word;
  }

  Hyphenator::setHungarianExtended(false);
}

TEST(HyphenationEval, HungarianRosszInflectionControls)'''
    if old_assert not in test:
        raise SystemExit('CPHUN-35: rossz compound assertion anchor not found')
    test = test.replace(old_assert, new_assert, 1)

TEST.write_text(test, encoding='utf-8')
