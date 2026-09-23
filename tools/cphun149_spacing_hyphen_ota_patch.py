#!/usr/bin/env python3
"""CPHUN-149 post-CPHUN-148 patch: approved spacing, guarded letter pairs,
curated Hungarian prefix boundaries and 1-2 regression tests.
Apply only after tools/build_cphun148_exp.sh on a clean checkout.
"""
from pathlib import Path
import re

def replace_one(path, before, after, label):
    p = Path(path)
    s = p.read_text(encoding="utf-8")
    n = s.count(before)
    if n != 1:
        raise SystemExit(f"CPHUN-149 {label}: expected one anchor, found {n}")
    p.write_text(s.replace(before, after, 1), encoding="utf-8")

# The UI index, persisted threshold, and display all use this single table.
replace_one(
    "src/activities/settings/TextSettingsActivity.cpp",
    "constexpr uint16_t LETTER_SPACING_THRESHOLDS[] = {0, 550, 530, 500, 460, 410, 350, 280};",
    "constexpr uint16_t LETTER_SPACING_THRESHOLDS[] = {0, 550, 520, 480, 430, 370, 300, 220};",
    "approved correction scale",
)
p = Path("src/CrossPointSettings.h")
s = p.read_text(encoding="utf-8")
s = s.replace("word-space stretch threshold in percent (280..550)",
              "word-space stretch threshold in percent (220..550)")
p.write_text(s, encoding="utf-8")

# The same consumeWord() helper is called by measurement, layout-positioning,
# and both renderer paths. Thus none of these can reinsert protected pixels.
header = Path("lib/Epub/Epub/LetterSpacingOptimization.h")
s = header.read_text(encoding="utf-8")
anchor = "inline uint8_t consumePair(const uint32_t left, const uint32_t right,"
if s.count(anchor) != 1:
    raise SystemExit("CPHUN-149: optimizer pair function missing")
s = s.replace(anchor,
    """// An identical pair is always protected, even if its font score is high.
""" + anchor, 1)
pattern = r"(inline uint8_t consumePair\([^)]*\)\s*\{\n\s*const Profile& limits = profile\(acc\.profileLevel\);\n)"
m = re.search(pattern, s)
if not m:
    raise SystemExit("CPHUN-149: consumePair anchor missing")
s = s[:m.end()] + "  if (left == right) return 0;\n" + s[m.end():]

word_start = s.index("inline uint8_t consumeWord(")
word_end = s.index("\n}", word_start) + 2
old_word = s[word_start:word_end]
if "while (*cursor)" not in old_word or "consumePair(prev, cp, style, acc)" not in old_word:
    raise SystemExit("CPHUN-149: consumeWord shape changed")
new_word = """inline uint8_t consumeWord(const char* text, const EpdFontFamily::Style style,
                           Accumulator& acc) {
  if (!beginWord(text, style, acc)) return 0;
  const auto* cursor = reinterpret_cast<const uint8_t*>(text);
  uint32_t prevPrev = 0;
  uint32_t prev = 0;
  uint8_t extra = 0;
  while (*cursor) {
    const uint32_t cp = utf8NextCodepoint(&cursor);
    if (!cp) break;
    // One-codepoint lookahead makes ABA protection symmetrical:
    // the first A-B gap is protected by the next A; the B-A gap by
    // the preceding A. Neither blocked gap consumes fractional budget.
    const auto* lookahead = cursor;
    const uint32_t next = *lookahead ? utf8NextCodepoint(&lookahead) : 0;
    const bool symmetricLeftGap = prev != 0 && next != 0 && prev == next;
    const bool symmetricRightGap = prevPrev != 0 && prevPrev == cp;
    if (prev && prev != cp && !symmetricLeftGap && !symmetricRightGap) {
      extra = static_cast<uint8_t>(extra + consumePair(prev, cp, style, acc));
    }
    prevPrev = prev;
    prev = cp;
  }
  return extra;
}"""
s = s[:word_start] + new_word + s[word_end:]
header.write_text(s, encoding="utf-8")

# This is deliberately a small, explicit family table rather than matching
# any arbitrary word that starts with a prefix. Unverified families remain
# governed by Liang patterns. "utó" is an explicit compound-first element,
# not a blanket verbal-prefix rule.
hy_path = Path("lib/Epub/Epub/hyphenation/Hyphenator.cpp")
s = hy_path.read_text(encoding="utf-8")
family_helpers = """struct HungarianPrefixFamily {
  const char32_t* prefix;
  const char32_t* followingStem;
};

// Explicitly checked samples across the requested 16 prefix spellings.
static constexpr HungarianPrefixFamily kHungarianPrefixFamilies[] = {
    {U"el", U"ad"},     {U"el", U"es"},     {U"el", U"akad"},
    {U"meg", U"ad"},    {U"meg", U"ír"},
    {U"fel", U"ad"},    {U"fel", U"emel"},
    {U"föl", U"emel"},  {U"föl", U"áll"},
    {U"le", U"ad"},     {U"le", U"ír"},
    {U"be", U"ad"},     {U"be", U"ír"},
    {U"ki", U"ad"},     {U"ki", U"ír"},
    {U"át", U"ad"},     {U"át", U"ve"},      {U"át", U"utal"},
    {U"át", U"értékel"}, {U"át", U"alszik"}, {U"át", U"alud"},
    {U"rá", U"ad"},     {U"rá", U"ír"},
    {U"alá", U"ír"},    {U"alá", U"ad"},
    {U"túl", U"ad"},    {U"túl", U"ír"},
    {U"utó", U"irat"},  {U"utó", U"hang"},
    {U"ide", U"ad"},   {U"ide", U"ér"},
    {U"oda", U"ad"},   {U"oda", U"ér"},
    {U"elő", U"ad"},   {U"elő", U"ír"},
    {U"szét", U"ad"},  {U"szét", U"es"},
};

size_t checkedHungarianPrefixLength(const std::vector<CodepointInfo>& cps) {
  for (const auto& family : kHungarianPrefixFamilies) {
    const size_t length = utf32Length(family.prefix);
    if (length >= cps.size() || !matchesHungarianStem(cps, 0, family.prefix)) continue;
    if (matchesHungarianStem(cps, length, family.followingStem)) return length;
  }
  return 0;
}

"""
anchor = "void appendHungarianSingleLetterPrefixBreak("
if s.count(anchor) != 1:
    raise SystemExit("CPHUN-149: Hungarian single-letter helper missing")
s = s.replace(anchor, family_helpers + anchor, 1)
# Normal word branch only: the recognized morphological boundary takes
# precedence over a Liang/single-letter false split (e.g. á-tadható).
normal_anchor = """  std::vector<Hyphenator::BreakInfo> breaks;
  if (preferredLanguageIsHungarian_ && hyphenator) {
    appendHungarianSingleLetterPrefixBreak(cps, *hyphenator, breaks);
    appendHungarianCompoundBoundaryBreaks(cps, breaks);
  }
"""
normal_new = """  std::vector<Hyphenator::BreakInfo> breaks;
  const size_t checkedPrefix =
      preferredLanguageIsHungarian_ ? checkedHungarianPrefixLength(cps) : 0;
  if (preferredLanguageIsHungarian_ && hyphenator) {
    if (checkedPrefix == 0) appendHungarianSingleLetterPrefixBreak(cps, *hyphenator, breaks);
    appendHungarianCompoundBoundaryBreaks(cps, breaks);
  }
  if (checkedPrefix > 0 && hyphenator &&
      checkedPrefix >= hyphenator->minPrefix() &&
      cps.size() - checkedPrefix >= hyphenator->minSuffix()) {
    breaks.push_back({byteOffsetForIndex(cps, checkedPrefix), true});
    // A recognized prefix supersedes any Liang one-letter proposal.
    indexes.erase(std::remove(indexes.begin(), indexes.end(), size_t{1}), indexes.end());
  }
"""
if s.count(normal_anchor) != 1:
    raise SystemExit("CPHUN-149: normal Hungarian break branch missing")
s = s.replace(normal_anchor, normal_new, 1)
hy_path.write_text(s, encoding="utf-8")

# Cover the reported failure, the other requested words, and negative controls.
test_path = Path("test/hyphenation_eval/HyphenationEvaluationTest.cpp")
test = test_path.read_text(encoding="utf-8")
if "CPHUN149HungarianPrefixProtection" in test:
    raise SystemExit("CPHUN-149: test already exists")
test += r'''

TEST(HyphenationEval, CPHUN149HungarianPrefixProtection) {
  Hyphenator::setPreferredLanguage("hu");
  Hyphenator::setHungarianExtended(true);
  Hyphenator::setHungarianMinima(1, 2);
  struct Case { const char* word; const char* prefix; };
  static constexpr Case words[] = {
      {"átadható", "át"}, {"átvehető", "át"}, {"átutal", "át"},
      {"átvesz", "át"}, {"átadás", "át"}, {"átértékel", "át"},
      {"átalszik", "át"}, {"átaludni", "át"},
      {"eladó", "el"}, {"elesett", "el"}, {"elakad", "el"},
      {"megad", "meg"}, {"felad", "fel"}, {"fölemel", "föl"},
      {"lead", "le"}, {"bead", "be"}, {"kiad", "ki"},
      {"ráad", "rá"}, {"aláír", "alá"}, {"túlad", "túl"},
      {"utóirat", "utó"}, {"idead", "ide"}, {"odaad", "oda"},
      {"előad", "elő"}, {"szétad", "szét"},
  };
  for (const auto& item : words) {
    const auto breaks = Hyphenator::breakOffsets(item.word, false);
    const auto expected = std::string(item.prefix).size();
    const auto boundary = std::find_if(breaks.begin(), breaks.end(),
                                      [expected](const auto& b) { return b.byteOffset == expected; });
    EXPECT_NE(boundary, breaks.end()) << item.word;
    if (std::string(item.word).rfind("át", 0) == 0) {
      const auto falseBreak = std::find_if(breaks.begin(), breaks.end(),
          [](const auto& b) { return b.byteOffset == std::string("á").size(); });
      EXPECT_EQ(falseBreak, breaks.end()) << "Invalid á-t...: " << item.word;
    }
  }
  // No blindly forced el-|át- boundary for unrelated words.
  for (const char* word : {"elem", "elefánt", "átok"}) {
    const auto breaks = Hyphenator::breakOffsets(word, false);
    const size_t prohibited = (word[0] == 'e') ? 2 : std::string("át").size();
    EXPECT_EQ(std::find_if(breaks.begin(), breaks.end(),
        [prohibited](const auto& b) { return b.byteOffset == prohibited; }), breaks.end()) << word;
  }
  Hyphenator::setHungarianMinima(2, 2);
  Hyphenator::setHungarianExtended(false);
}
'''
test_path.write_text(test, encoding="utf-8")

# CPHUN-148 has the production OTA comparison. Never re-introduce the
# CPHUN-147 fake baseline and never publish this experimental build.
ota = Path("src/network/OtaUpdater.cpp").read_text(encoding="utf-8")
for required in (
    "https://api.github.com/repos/Matteo1965/crosspoint-reader/releases/latest",
    "const int currentBuild = parseCphunBuildId(CPHUN_BUILD_ID);",
    "return latestBuild > currentBuild;",
):
    if required not in ota:
        raise SystemExit("CPHUN-149: production OTA requirement missing: " + required)
if "CPHUN_OTA_TEST_BASELINE_BUILD" in ota:
    raise SystemExit("CPHUN-149: test OTA baseline leaked into build")

bid = Path("src/CPHUNBuildId.h")
s = bid.read_text(encoding="utf-8")
s, n = re.subn(r'#define CPHUN_BUILD_ID "[^"]+"',
               '#define CPHUN_BUILD_ID "CPHUN-260923-149-EXP"', s, count=1)
if n != 1:
    raise SystemExit("CPHUN-149: build id missing")
s, n = re.subn(r'^#define CPHUN_BUILD_DATE .*$', '#define CPHUN_BUILD_DATE "Sep-23 2026"',
               s, count=1, flags=re.M)
if n != 1:
    raise SystemExit("CPHUN-149: build date missing")
bid.write_text(s, encoding="utf-8")
print("CPHUN-149 patch applied: new scale, AA/ABA pair protection, 16 prefix families, production OTA")
