from pathlib import Path


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: expected exactly one match, found {count}")
    return text.replace(old, new, 1)


root = Path(__file__).resolve().parents[1]
hyphenator_path = root / "lib/Epub/Epub/hyphenation/Hyphenator.cpp"
test_path = root / "test/hyphenation_eval/HyphenationEvaluationTest.cpp"
build_id_path = root / "src/CPHUNBuildId.h"

cpp = hyphenator_path.read_text(encoding="utf-8")

ascii_anchor = """uint32_t asciiLower(const uint32_t cp) {
  return (cp >= 'A' && cp <= 'Z') ? cp + ('a' - 'A') : cp;
}

// Returns the number of Unicode codepoints occupied by one Hungarian consonant
"""

compound_helpers = """uint32_t asciiLower(const uint32_t cp) {
  return (cp >= 'A' && cp <= 'Z') ? cp + ('a' - 'A') : cp;
}

struct HungarianCompoundStemRule {
  const char32_t* left;
  const char32_t* rightStem;
};

// Hungarian compound boundaries cannot be inferred safely from compact doubled
// digraph spellings alone (e.g. meggy is a genuine doubled gy). These stem pairs
// cover verified compound families while allowing inflected/derived right parts.
static constexpr HungarianCompoundStemRule kHungarianCompoundStemRules[] = {
    {U"meg", U"gyull"},       {U"meg", U"gyón"},         {U"meg", U"győz"},
    {U"meg", U"gyaláz"},      {U"kis", U"szék"},         {U"kis", U"szoba"},
    {U"kis", U"szekrény"},    {U"ruhás", U"szekrény"},   {U"vas", U"szeg"},
    {U"cipős", U"szekrény"},  {U"hús", U"szelet"},      {U"ideg", U"gyógyász"},
    {U"gyors", U"szolgálat"}, {U"okos", U"szemüveg"},    {U"nyolc", U"csillag"},
    {U"arc", U"csont"},       {U"szín", U"nyom"},        {U"tánc", U"csoport"},
};

size_t utf32Length(const char32_t* text) {
  size_t length = 0;
  while (text[length] != U'\\0') ++length;
  return length;
}

bool matchesHungarianStem(const std::vector<CodepointInfo>& cps, const size_t start, const char32_t* stem) {
  for (size_t i = 0; stem[i] != U'\\0'; ++i) {
    if (start + i >= cps.size()) return false;
    if (toLowerLatin(cps[start + i].value) != static_cast<uint32_t>(stem[i])) return false;
  }
  return true;
}

bool isHungarianCompoundBoundary(const std::vector<CodepointInfo>& cps, const size_t split) {
  for (const auto& rule : kHungarianCompoundStemRules) {
    const size_t leftLength = utf32Length(rule.left);
    if (split != leftLength) continue;
    if (!matchesHungarianStem(cps, 0, rule.left)) continue;
    if (matchesHungarianStem(cps, split, rule.rightStem)) return true;
  }
  return false;
}

void appendHungarianCompoundBoundaryBreaks(const std::vector<CodepointInfo>& cps,
                                            std::vector<Hyphenator::BreakInfo>& outBreaks) {
  for (size_t split = 1; split < cps.size(); ++split) {
    if (isHungarianCompoundBoundary(cps, split)) {
      outBreaks.push_back({byteOffsetForIndex(cps, split), true});
    }
  }
}

// Returns the number of Unicode codepoints occupied by one Hungarian consonant
"""
cpp = replace_once(cpp, ascii_anchor, compound_helpers, "compound helper insertion")

extended_anchor = """      const size_t split = i + 1;
      if (split == 0 || split >= cps.size()) continue;
      // Secondary readability guard: both rendered word parts must contain a vowel.
"""
extended_replacement = """      const size_t split = i + 1;
      if (split == 0 || split >= cps.size()) continue;
      // A verified compound boundary at the same compact spelling is a normal
      // hyphenation point, not a doubled-digraph replacement break.
      if (isHungarianCompoundBoundary(cps, split)) continue;
      // Secondary readability guard: both rendered word parts must contain a vowel.
"""
cpp = replace_once(cpp, extended_anchor, extended_replacement, "extended compound guard")

normal_anchor = """  std::vector<Hyphenator::BreakInfo> breaks;
  if (preferredLanguageIsHungarian_ && hyphenator) {
    appendHungarianSingleLetterPrefixBreak(cps, *hyphenator, breaks);
  }
  if (useHungarianExtended) {
"""
normal_replacement = """  std::vector<Hyphenator::BreakInfo> breaks;
  if (preferredLanguageIsHungarian_ && hyphenator) {
    appendHungarianSingleLetterPrefixBreak(cps, *hyphenator, breaks);
    appendHungarianCompoundBoundaryBreaks(cps, breaks);
  }
  if (useHungarianExtended) {
"""
cpp = replace_once(cpp, normal_anchor, normal_replacement, "compound break call")

hyphenator_path.write_text(cpp, encoding="utf-8")

test = test_path.read_text(encoding="utf-8")
include_anchor = '#include "lib/Epub/Epub/hyphenation/HyphenationCommon.h"\n'
include_replacement = include_anchor + '#include "lib/Epub/Epub/hyphenation/Hyphenator.h"\n'
test = replace_once(test, include_anchor, include_replacement, "Hyphenator test include")

regression_tests = r'''

TEST(HyphenationEval, HungarianCompoundBoundaryCorrections) {
  struct CompoundCase {
    const char* word;
    const char* left;
  };
  static constexpr CompoundCase cases[] = {
      {"meggyullad", "meg"},       {"meggyón", "meg"},          {"meggyőz", "meg"},
      {"meggyaláz", "meg"},       {"kisszék", "kis"},          {"kisszoba", "kis"},
      {"kisszekrény", "kis"},     {"ruhásszekrény", "ruhás"}, {"vasszeg", "vas"},
      {"cipősszekrény", "cipős"}, {"hússzelet", "hús"},       {"ideggyógyász", "ideg"},
      {"gyorsszolgálat", "gyors"}, {"okosszemüveg", "okos"},   {"nyolccsillagos", "nyolc"},
      {"arccsont", "arc"},         {"színnyomás", "szín"},      {"tánccsoport", "tánc"},
  };

  Hyphenator::setPreferredLanguage("hu");
  Hyphenator::setHungarianExtended(true);

  for (const auto& tc : cases) {
    const size_t expectedOffset = std::string(tc.left).size();
    const auto breaks = Hyphenator::breakOffsets(tc.word, false);
    const auto it = std::find_if(breaks.begin(), breaks.end(), [expectedOffset](const Hyphenator::BreakInfo& info) {
      return info.byteOffset == expectedOffset;
    });
    ASSERT_NE(it, breaks.end()) << "Missing compound boundary for " << tc.word;
    EXPECT_TRUE(it->requiresInsertedHyphen) << tc.word;
    EXPECT_EQ(it->replacement, Hyphenator::Replacement::None) << "Replacement break leaked into " << tc.word;
  }

  Hyphenator::setHungarianExtended(false);
}

TEST(HyphenationEval, HungarianGenuineDoubledDigraphsRemainExtended) {
  struct DoubledCase {
    const char* word;
    size_t expectedOffset;
  };
  static constexpr DoubledCase cases[] = {
      {"meggyes", 3},
      {"asszony", 2},
      {"hosszú", 3},
  };

  Hyphenator::setPreferredLanguage("hu");
  Hyphenator::setHungarianExtended(true);

  for (const auto& tc : cases) {
    const auto breaks = Hyphenator::breakOffsets(tc.word, false);
    const auto it = std::find_if(breaks.begin(), breaks.end(), [&tc](const Hyphenator::BreakInfo& info) {
      return info.byteOffset == tc.expectedOffset;
    });
    ASSERT_NE(it, breaks.end()) << "Missing doubled-digraph break for " << tc.word;
    EXPECT_NE(it->replacement, Hyphenator::Replacement::None) << "Compound correction overmatched " << tc.word;
  }

  Hyphenator::setHungarianExtended(false);
}
'''

if "TEST(HyphenationEval, HungarianCompoundBoundaryCorrections)" in test:
    raise RuntimeError("Hungarian compound regression tests already present")
test_path.write_text(test.rstrip() + regression_tests + "\n", encoding="utf-8")

build_id = build_id_path.read_text(encoding="utf-8")
build_id = replace_once(build_id, 'CPHUN_BUILD_ID "CPHUN-260828-33"',
                        'CPHUN_BUILD_ID "CPHUN-260830-34"', "CPHUN build id")
build_id_path.write_text(build_id, encoding="utf-8")
