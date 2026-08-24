from pathlib import Path


def replace_once(path: str, old: str, new: str, label: str):
    p = Path(path)
    text = p.read_text(encoding="utf-8")
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{label}: expected exactly one match, found {count}")
    p.write_text(text.replace(old, new, 1), encoding="utf-8")


# -----------------------------------------------------------------------------
# 1) Min. spacing final-line repair: choose the LATEST legal split, not the first.
#    This prevents 50% spacing from pushing whole fitting words to a new line.
# -----------------------------------------------------------------------------
parsed = Path("lib/Epub/Epub/ParsedText.cpp")
text = parsed.read_text(encoding="utf-8")
old = '''      size_t correctedBreak = finalEnd;
      for (size_t candidate = finalStart + 1; candidate < finalEnd; ++candidate) {
        if (!TokenBoundary::allowsBreak(wordContinues[candidate], wordNoSpaceBefore[candidate])) continue;
        if (naturalLineWidth(candidate, finalEnd) <= pageWidth) {
          correctedBreak = candidate;
          break;
        }
      }
'''
new = '''      size_t correctedBreak = finalEnd;
      // Search backwards: move only the minimum amount of text needed to make the
      // natural-100% final line fit. Searching forwards caused severe early wraps
      // at low Min. spacing values (e.g. 50%).
      for (size_t candidate = finalEnd - 1; candidate > finalStart; --candidate) {
        if (!TokenBoundary::allowsBreak(wordContinues[candidate], wordNoSpaceBefore[candidate])) continue;
        if (naturalLineWidth(candidate, finalEnd) <= pageWidth) {
          correctedBreak = candidate;
          break;
        }
      }
'''
if text.count(old) != 1:
    raise SystemExit(f"ParsedText final-line correction: expected 1 match, found {text.count(old)}")
text = text.replace(old, new, 1)

# Paragraph-final last-syllable guard. A word may still be hyphenated at paragraph
# end when two or more syllabic pieces remain; only the final possible piece is protected.
marker = '''  size_t chosenOffset = 0;
  int chosenWidth = -1;
  bool chosenNeedsHyphen = true;
  Hyphenator::Replacement chosenReplacement = Hyphenator::Replacement::None;

  // Iterate over each legal breakpoint and retain the widest prefix that still fits.
'''
insert = '''  size_t chosenOffset = 0;
  int chosenWidth = -1;
  bool chosenNeedsHyphen = true;
  Hyphenator::Replacement chosenReplacement = Hyphenator::Replacement::None;

  // Paragraph-end protection: punctuation after the current token does not make it
  // a non-final word. If this is the final lexical word, do not choose a breakpoint
  // that leaves only the last hyphenation piece on a new final line.
  const auto tokenHasWordCharacter = [](const std::string& token) {
    const auto* ptr = reinterpret_cast<const unsigned char*>(token.c_str());
    while (*ptr) {
      if (isWordCharacter(utf8NextCodepoint(&ptr))) return true;
    }
    return false;
  };
  bool isParagraphFinalLexicalWord = true;
  for (size_t trailing = wordIndex + 1; trailing < words.size(); ++trailing) {
    if (tokenHasWordCharacter(words[trailing])) {
      isParagraphFinalLexicalWord = false;
      break;
    }
  }

  // Iterate over each legal breakpoint and retain the widest prefix that still fits.
'''
if text.count(marker) != 1:
    raise SystemExit(f"ParsedText hyphen-choice marker: expected 1 match, found {text.count(marker)}")
text = text.replace(marker, insert, 1)

loop_marker = '''    const bool needsHyphen = info.requiresInsertedHyphen;
    std::string candidatePrefix = word.substr(0, offset);
'''
loop_insert = '''    const bool needsHyphen = info.requiresInsertedHyphen;

    if (isParagraphFinalLexicalWord && needsHyphen) {
      bool hasLaterAutomaticBreak = false;
      for (const auto& later : breakInfos) {
        if (later.requiresInsertedHyphen && later.byteOffset > offset && later.byteOffset < word.size()) {
          hasLaterAutomaticBreak = true;
          break;
        }
      }
      if (!hasLaterAutomaticBreak) {
        continue;  // Would leave only the final hyphenation piece on the last line.
      }
    }

    std::string candidatePrefix = word.substr(0, offset);
'''
if text.count(loop_marker) != 1:
    raise SystemExit(f"ParsedText final-syllable guard marker: expected 1 match, found {text.count(loop_marker)}")
text = text.replace(loop_marker, loop_insert, 1)
parsed.write_text(text, encoding="utf-8")


# -----------------------------------------------------------------------------
# 2) Hungarian hyphenation guards.
#    a) Normal language-pattern break wins over an extended replacement at same offset.
#    b) For <=5-codepoint Hungarian words, every inserted-hyphen candidate must leave
#       at least one Hungarian vowel on both sides (Tuck/Lizzy/Jack/Alby/Jimmy/Chuck/Puck).
# -----------------------------------------------------------------------------
hyp = Path("lib/Epub/Epub/hyphenation/Hyphenator.cpp")
h = hyp.read_text(encoding="utf-8")

helper_marker = '''bool hasHungarianVowel(const std::vector<CodepointInfo>& cps, const size_t begin, const size_t end) {
  for (size_t i = begin; i < end; ++i) {
    if (isHungarianVowel(cps[i].value)) return true;
  }
  return false;
}

'''
helper = helper_marker + '''void filterShortHungarianAutomaticBreaks(const std::vector<CodepointInfo>& cps,
                                         std::vector<Hyphenator::BreakInfo>& breaks) {
  constexpr size_t kShortWordMaxCodepoints = 5;
  if (cps.size() > kShortWordMaxCodepoints) return;

  breaks.erase(std::remove_if(breaks.begin(), breaks.end(), [&](const Hyphenator::BreakInfo& info) {
                 if (!info.requiresInsertedHyphen) return false;
                 size_t split = cps.size();
                 for (size_t i = 1; i < cps.size(); ++i) {
                   if (cps[i].byteOffset == info.byteOffset) {
                     split = i;
                     break;
                   }
                 }
                 if (split == 0 || split >= cps.size()) return true;
                 return !hasHungarianVowel(cps, 0, split) || !hasHungarianVowel(cps, split, cps.size());
               }),
               breaks.end());
}

'''
if h.count(helper_marker) != 1:
    raise SystemExit(f"Hyphenator vowel helper marker: expected 1 match, found {h.count(helper_marker)}")
h = h.replace(helper_marker, helper, 1)

old_sort = '''    if (a.replacement != b.replacement) return a.replacement > b.replacement;
    return a.requiresInsertedHyphen < b.requiresInsertedHyphen;
'''
new_sort = '''    // Prefer an ordinary language-pattern break at the same byte offset over
    // a heuristic extended replacement. This fixes compound-boundary collisions
    // such as zokogás-szerűség while leaving genuine compact doublings alone when
    // no ordinary break exists at that position.
    if (a.replacement != b.replacement) return a.replacement < b.replacement;
    return a.requiresInsertedHyphen < b.requiresInsertedHyphen;
'''
if h.count(old_sort) != 1:
    raise SystemExit(f"Hyphenator dedupe ordering: expected 1 match, found {h.count(old_sort)}")
h = h.replace(old_sort, new_sort, 1)

old_return = '''    sortAndDedupeBreakInfos(explicitBreakInfos);
    return explicitBreakInfos;
'''
new_return = '''    sortAndDedupeBreakInfos(explicitBreakInfos);
    if (preferredLanguageIsHungarian_) filterShortHungarianAutomaticBreaks(cps, explicitBreakInfos);
    return explicitBreakInfos;
'''
if h.count(old_return) != 1:
    raise SystemExit("Hyphenator explicit return marker missing")
h = h.replace(old_return, new_return, 1)

old_return2 = '''    sortAndDedupeBreakInfos(segmentedBreaks);
    return segmentedBreaks;
'''
new_return2 = '''    sortAndDedupeBreakInfos(segmentedBreaks);
    if (preferredLanguageIsHungarian_) filterShortHungarianAutomaticBreaks(cps, segmentedBreaks);
    return segmentedBreaks;
'''
if h.count(old_return2) != 1:
    raise SystemExit("Hyphenator segmented return marker missing")
h = h.replace(old_return2, new_return2, 1)

old_final = '''  sortAndDedupeBreakInfos(breaks);
  return breaks;
}
'''
new_final = '''  sortAndDedupeBreakInfos(breaks);
  if (preferredLanguageIsHungarian_) filterShortHungarianAutomaticBreaks(cps, breaks);
  return breaks;
}
'''
if h.count(old_final) != 1:
    raise SystemExit(f"Hyphenator final return marker: expected 1 match, found {h.count(old_final)}")
h = h.replace(old_final, new_final, 1)
hyp.write_text(h, encoding="utf-8")


# -----------------------------------------------------------------------------
# 3) Focused regression tests.
# -----------------------------------------------------------------------------
test_cpp = Path("test/hyphenation_eval/HungarianTypographyRegressionTest.cpp")
test_cpp.write_text(r'''#include <gtest/gtest.h>

#include <algorithm>
#include <string>
#include <vector>

#include "lib/Epub/Epub/hyphenation/Hyphenator.h"

namespace {

using Replacement = Hyphenator::Replacement;

const Hyphenator::BreakInfo* findAt(const std::vector<Hyphenator::BreakInfo>& breaks, size_t offset) {
  auto it = std::find_if(breaks.begin(), breaks.end(), [offset](const auto& b) { return b.byteOffset == offset; });
  return it == breaks.end() ? nullptr : &*it;
}

class HungarianTypographyRegression : public ::testing::Test {
 protected:
  void SetUp() override {
    Hyphenator::setPreferredLanguage("hu");
    Hyphenator::setHungarianExtended(true);
  }
};

TEST_F(HungarianTypographyRegression, ShortForeignNamesDoNotLeaveVowellessRemainders) {
  static constexpr const char* words[] = {"Tuck", "Lizzy", "Jack", "Alby", "Jimmy", "Chuck", "Puck"};
  for (const char* word : words) {
    SCOPED_TRACE(word);
    const auto breaks = Hyphenator::breakOffsets(word, true);
    EXPECT_TRUE(breaks.empty());
  }
}

TEST_F(HungarianTypographyRegression, CompoundBoundaryBeatsFalseExtendedReplacement) {
  struct Case { const char* word; const char* left; };
  static constexpr Case cases[] = {
      {"zokogásszerűség", "zokogás"}, {"írásszerű", "írás"}, {"mozgásszerv", "mozgás"},
      {"hússzelet", "hús"}, {"anyaggyűjtés", "anyag"}, {"virággyűjtés", "virág"},
      {"szénnyomás", "szén"}, {"vízzsák", "víz"}, {"léccsere", "léc"},
  };
  for (const auto& tc : cases) {
    SCOPED_TRACE(tc.word);
    const auto breaks = Hyphenator::breakOffsets(tc.word, false);
    const auto* info = findAt(breaks, std::string(tc.left).size());
    ASSERT_NE(info, nullptr);
    EXPECT_EQ(info->replacement, Replacement::None);
  }
}

TEST_F(HungarianTypographyRegression, GenuineCompactDoublingsKeepReplacement) {
  struct Case { const char* word; const char* prefix; Replacement replacement; };
  static constexpr Case cases[] = {
      {"asszony", "as", Replacement::AppendZ}, {"hosszú", "hos", Replacement::AppendZ},
      {"mennyi", "men", Replacement::AppendY}, {"könnyű", "kön", Replacement::AppendY},
      {"meccsen", "mec", Replacement::AppendS}, {"gallyak", "gal", Replacement::AppendY},
      {"meggyel", "meg", Replacement::AppendY}, {"hattyú", "hat", Replacement::AppendY},
  };
  for (const auto& tc : cases) {
    SCOPED_TRACE(tc.word);
    const auto breaks = Hyphenator::breakOffsets(tc.word, false);
    const auto* info = findAt(breaks, std::string(tc.prefix).size());
    ASSERT_NE(info, nullptr);
    EXPECT_EQ(info->replacement, tc.replacement);
  }
}

}  // namespace
''', encoding="utf-8")

cmake = Path("test/hyphenation_eval/CMakeLists.txt")
c = cmake.read_text(encoding="utf-8")
needle = '''add_executable(HyphenationEvaluationTest
  HyphenationEvaluationTest.cpp
'''
replacement = '''add_executable(HyphenationEvaluationTest
  HyphenationEvaluationTest.cpp
  HungarianTypographyRegressionTest.cpp
'''
if c.count(needle) != 1:
    raise SystemExit(f"hyphenation_eval CMake marker: expected 1 match, found {c.count(needle)}")
cmake.write_text(c.replace(needle, replacement, 1), encoding="utf-8")
