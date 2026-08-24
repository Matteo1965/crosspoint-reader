#include <gtest/gtest.h>

#include <algorithm>
#include <cstddef>
#include <string>
#include <vector>

#include "lib/Epub/Epub/hyphenation/Hyphenator.h"

namespace {

using Replacement = Hyphenator::Replacement;

struct CompoundBoundaryCase {
  const char* word;
  const char* leftPart;
};

struct GenuineDoublingCase {
  const char* word;
  const char* sourcePrefix;
  Replacement replacement;
};

const Hyphenator::BreakInfo* findBreakAt(const std::vector<Hyphenator::BreakInfo>& breaks, const size_t byteOffset) {
  const auto it = std::find_if(breaks.begin(), breaks.end(),
                               [byteOffset](const Hyphenator::BreakInfo& info) { return info.byteOffset == byteOffset; });
  return it == breaks.end() ? nullptr : &*it;
}

class HungarianExtendedRegressionTest : public ::testing::Test {
 protected:
  void SetUp() override {
    Hyphenator::setPreferredLanguage("hu");
    Hyphenator::setHungarianExtended(true);
  }
};

// These words contain a sequence that looks like a compact doubled Hungarian
// digraph/trigraph only because a compound/morpheme boundary joins the last
// letter of the left member with the first letters of the right member.
// At the boundary we want a normal inserted hyphen and Replacement::None.
TEST_F(HungarianExtendedRegressionTest, CompoundBoundariesMustNotTriggerCompactDoublingReplacement) {
  static constexpr CompoundBoundaryCase cases[] = {
      // s + sz... -> apparent ssz
      {"zokogásszerűség", "zokogás"},
      {"zokogásszerű", "zokogás"},
      {"írásszerű", "írás"},
      {"írásszerűség", "írás"},
      {"mozgásszerv", "mozgás"},
      {"mozgásszervi", "mozgás"},
      {"hússzelet", "hús"},
      {"hússzeletelő", "hús"},
      {"olvasásszeretet", "olvasás"},
      {"lakásszám", "lakás"},

      // g + gy... -> apparent ggy
      {"anyaggyűjtés", "anyag"},
      {"anyaggyűjtő", "anyag"},
      {"maggyűjtés", "mag"},
      {"virággyűjtés", "virág"},
      {"világgyűlés", "világ"},

      // l + ly... -> apparent lly
      {"fallyuk", "fal"},
      {"fallyukasztás", "fal"},
      {"acéllyukasztás", "acél"},

      // n + ny... -> apparent nny
      {"szénnyomás", "szén"},
      {"ínnyújtás", "ín"},

      // z + zs... -> apparent zzs
      {"vízzsák", "víz"},
      {"gázzsák", "gáz"},
      {"tűzzsák", "tűz"},

      // c + cs... -> apparent ccs
      {"léccsere", "léc"},
  };

  for (const auto& tc : cases) {
    SCOPED_TRACE(tc.word);
    const auto breaks = Hyphenator::breakOffsets(tc.word, /*includeFallback=*/false);
    const size_t boundary = std::string(tc.leftPart).size();
    const auto* info = findBreakAt(breaks, boundary);
    ASSERT_NE(info, nullptr) << "Expected a break at the compound boundary after " << tc.leftPart;
    EXPECT_TRUE(info->requiresInsertedHyphen);
    EXPECT_EQ(info->replacement, Replacement::None)
        << "Compound boundary must outrank compact doubled-consonant reconstruction";
  }
}

// Positive controls: genuine compact doubled multi-letter consonants must keep
// the Hungarian reconstruction on the left side (asz-szony, meny-nyi, etc.).
TEST_F(HungarianExtendedRegressionTest, GenuineCompactDoublingsMustKeepReplacement) {
  static constexpr GenuineDoublingCase cases[] = {
      // ssz -> AppendZ
      {"asszony", "as", Replacement::AppendZ},
      {"asszonyok", "as", Replacement::AppendZ},
      {"asszonnyal", "as", Replacement::AppendZ},
      {"hosszú", "hos", Replacement::AppendZ},
      {"hosszan", "hos", Replacement::AppendZ},

      // nny -> AppendY
      {"mennyi", "men", Replacement::AppendY},
      {"mennyire", "men", Replacement::AppendY},
      {"könnyű", "kön", Replacement::AppendY},
      {"könnyen", "kön", Replacement::AppendY},

      // ccs -> AppendS
      {"meccsen", "mec", Replacement::AppendS},
      {"meccsek", "mec", Replacement::AppendS},

      // lly -> AppendY
      {"gallyak", "gal", Replacement::AppendY},
      {"gallyal", "gal", Replacement::AppendY},

      // ggy -> AppendY
      {"meggy", "meg", Replacement::AppendY},
      {"meggyel", "meg", Replacement::AppendY},

      // tty -> AppendY
      {"hattyú", "hat", Replacement::AppendY},
  };

  for (const auto& tc : cases) {
    SCOPED_TRACE(tc.word);
    const auto breaks = Hyphenator::breakOffsets(tc.word, /*includeFallback=*/false);
    const size_t split = std::string(tc.sourcePrefix).size();
    const auto* info = findBreakAt(breaks, split);
    ASSERT_NE(info, nullptr) << "Expected extended Hungarian break after source prefix " << tc.sourcePrefix;
    EXPECT_TRUE(info->requiresInsertedHyphen);
    EXPECT_EQ(info->replacement, tc.replacement);
  }
}

}  // namespace
