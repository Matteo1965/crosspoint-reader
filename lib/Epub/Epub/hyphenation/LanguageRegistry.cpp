#include "LanguageRegistry.h"

#include <algorithm>
#include <array>

#include "HyphenationCommon.h"
// X4 Pro Hungarian Edition is intentionally bilingual (HU/EN).
// Keep the other embedded Liang tries in normal/Picco builds.
#include "generated/hyph-en.trie.h"
#include "generated/hyph-hu.trie.h"
#ifndef CROSSPOINT_HU_EN_HYPHENATION_ONLY
#include "generated/hyph-de.trie.h"
#include "generated/hyph-es.trie.h"
#include "generated/hyph-fi.trie.h"
#include "generated/hyph-fr.trie.h"
#include "generated/hyph-it.trie.h"
#include "generated/hyph-pl.trie.h"
#include "generated/hyph-pt.trie.h"
#include "generated/hyph-sv.trie.h"
#endif

namespace {

// English hyphenation patterns (3/3 minimum prefix/suffix length)
LanguageHyphenator englishHyphenator(en_patterns, isLatinLetter, toLowerLatin, 3, 3);
LanguageHyphenator hungarianHyphenator(hu_patterns, isLatinLetter, toLowerLatin);
#ifndef CROSSPOINT_HU_EN_HYPHENATION_ONLY
LanguageHyphenator frenchHyphenator(fr_patterns, isLatinLetter, toLowerLatin);
LanguageHyphenator germanHyphenator(de_patterns, isLatinLetter, toLowerLatin);
LanguageHyphenator spanishHyphenator(es_patterns, isLatinLetter, toLowerLatin);
LanguageHyphenator italianHyphenator(it_patterns, isLatinLetter, toLowerLatin);
LanguageHyphenator swedishHyphenator(sv_patterns, isLatinLetter, toLowerLatin);
LanguageHyphenator polishHyphenator(pl_patterns, isLatinLetter, toLowerLatin);
LanguageHyphenator finnishHyphenator(fi_patterns, isLatinLetter, toLowerLatin);
LanguageHyphenator portugueseHyphenator(pt_patterns, isLatinLetter, toLowerLatin);
#endif

#ifdef CROSSPOINT_HU_EN_HYPHENATION_ONLY
using EntryArray = std::array<LanguageEntry, 2>;
const EntryArray& entries() {
  static const EntryArray kEntries = {{{"english", "en", &englishHyphenator},
                                       {"hungarian", "hu", &hungarianHyphenator}}};
  return kEntries;
}
#else
using EntryArray = std::array<LanguageEntry, 10>;
const EntryArray& entries() {
  static const EntryArray kEntries = {{{"english", "en", &englishHyphenator},
                                       {"french", "fr", &frenchHyphenator},
                                       {"german", "de", &germanHyphenator},
                                       {"hungarian", "hu", &hungarianHyphenator},
                                       {"spanish", "es", &spanishHyphenator},
                                       {"italian", "it", &italianHyphenator},
                                       {"polish", "pl", &polishHyphenator},
                                       {"swedish", "sv", &swedishHyphenator},
                                       {"finnish", "fi", &finnishHyphenator},
                                       {"portuguese", "pt", &portugueseHyphenator}}};
  return kEntries;
}
#endif

}  // namespace

const LanguageHyphenator* getLanguageHyphenatorForPrimaryTag(const std::string& primaryTag) {
  const auto& allEntries = entries();
  const auto it = std::find_if(allEntries.begin(), allEntries.end(),
                               [&primaryTag](const LanguageEntry& entry) { return primaryTag == entry.primaryTag; });
  return (it != allEntries.end()) ? it->hyphenator : nullptr;
}

LanguageEntryView getLanguageEntries() {
  const auto& allEntries = entries();
  return LanguageEntryView{allEntries.data(), allEntries.size()};
}

void setHungarianHyphenationMinima(const size_t minPrefix, const size_t minSuffix) {
  hungarianHyphenator.setMinima(minPrefix, minSuffix);
}
