#include "Hyphenator.h"

#include <Utf8.h>

#include <algorithm>
#include <cassert>
#include <vector>

#include "HyphenationCommon.h"
#include "LanguageHyphenator.h"
#include "LanguageRegistry.h"

const LanguageHyphenator* Hyphenator::cachedHyphenator_ = nullptr;
bool Hyphenator::preferredLanguageIsHungarian_ = false;
bool Hyphenator::hungarianExtended_ = false;
bool Hyphenator::softHyphenEnabled_ = false;

namespace {

struct Iso639Mapping {
  const char* iso639_2;
  const char* iso639_1;
};
static constexpr Iso639Mapping kIso639Mappings[] = {{"eng", "en"}, {"fra", "fr"}, {"fre", "fr"}, {"deu", "de"},
                                                    {"ger", "de"}, {"rus", "ru"}, {"spa", "es"}, {"ita", "it"},
                                                    {"ukr", "uk"}, {"swe", "sv"}, {"fin", "fi"}, {"hun", "hu"}};

const LanguageHyphenator* hyphenatorForLanguage(const std::string& langTag) {
  if (langTag.empty()) return nullptr;

  std::string primary;
  primary.reserve(langTag.size());
  for (char c : langTag) {
    if (c == '-' || c == '_') break;
    if (c >= 'A' && c <= 'Z') c = static_cast<char>(c - 'A' + 'a');
    primary.push_back(c);
  }
  if (primary.empty()) return nullptr;

  for (const auto& mapping : kIso639Mappings) {
    if (primary == mapping.iso639_2) {
      primary = mapping.iso639_1;
      break;
    }
  }

  return getLanguageHyphenatorForPrimaryTag(primary);
}

size_t byteOffsetForIndex(const std::vector<CodepointInfo>& cps, const size_t index) {
  return (index < cps.size()) ? cps[index].byteOffset : (cps.empty() ? 0 : cps.back().byteOffset);
}

void normalizeHungarianProcessingCodepoints(std::vector<CodepointInfo>& cps) {
  for (auto& cp : cps) {
    switch (cp.value) {
      case 0x00F5:
      case 0x00F4:
        cp.value = 0x0151;
        break;
      case 0x00D5:
      case 0x00D4:
        cp.value = 0x0150;
        break;
      case 0x00FB:
        cp.value = 0x0171;
        break;
      case 0x00DB:
        cp.value = 0x0170;
        break;
      default:
        break;
    }
  }
}

bool isHungarianClosingQuote(const uint32_t cp) {
  return cp == '"' || cp == 0x00BB || cp == 0x201D;
}

void stripHungarianClosingQuoteBeforeSuffix(std::vector<CodepointInfo>& cps) {
  for (size_t i = 1; i + 2 < cps.size(); ++i) {
    if (!isHungarianClosingQuote(cps[i].value) || !isAlphabetic(cps[i - 1].value) ||
        !isExplicitHyphen(cps[i + 1].value) || isSoftHyphen(cps[i + 1].value) ||
        !isAlphabetic(cps[i + 2].value)) {
      continue;
    }

    bool suffixIsAlphabetic = true;
    for (size_t j = i + 2; j < cps.size(); ++j) {
      if (!isAlphabetic(cps[j].value)) {
        suffixIsAlphabetic = false;
        break;
      }
    }
    if (!suffixIsAlphabetic) continue;

    // CPHUN-66: remove only from the processing copy. Byte offsets still point
    // into the original token, so rendering keeps the closing quote intact.
    cps.erase(cps.begin() + i);
    return;
  }
}

std::vector<Hyphenator::BreakInfo> buildExplicitBreakInfos(const std::vector<CodepointInfo>& cps,
                                                            const bool allowHungarianNumericPrefix) {
  std::vector<Hyphenator::BreakInfo> breaks;

  for (size_t i = 1; i + 1 < cps.size(); ++i) {
    const uint32_t cp = cps[i].value;
    if (!isExplicitHyphen(cp) || !isAlphabetic(cps[i + 1].value)) {
      continue;
    }
    const bool hasAlphabeticLeft = isAlphabetic(cps[i - 1].value);
    const bool hasHungarianNumericLeft =
        allowHungarianNumericPrefix && !isSoftHyphen(cp) && isAsciiDigit(cps[i - 1].value);
    if (!hasAlphabeticLeft && !hasHungarianNumericLeft) {
      continue;
    }
    breaks.push_back({cps[i + 1].byteOffset, isSoftHyphen(cp)});
  }

  return breaks;
}

bool isSegmentSeparator(const uint32_t cp, const bool includeHungarianSlash = false) {
  return isExplicitHyphen(cp) || isApostrophe(cp) || (includeHungarianSlash && cp == '/');
}

void appendSegmentPatternBreaks(const std::vector<CodepointInfo>& cps, const LanguageHyphenator& hyphenator,
                                const bool includeFallback, const bool includeHungarianSlash,
                                std::vector<Hyphenator::BreakInfo>& outBreaks) {
  size_t segStart = 0;

  for (size_t i = 0; i <= cps.size(); ++i) {
    const bool atEnd = i == cps.size();
    const bool atSeparator = !atEnd && isSegmentSeparator(cps[i].value, includeHungarianSlash);
    if (!atEnd && !atSeparator) {
      continue;
    }

    if (i > segStart) {
      std::vector<CodepointInfo> segment(cps.begin() + segStart, cps.begin() + i);
      auto segIndexes = hyphenator.breakIndexes(segment);

      if (includeFallback && segIndexes.empty()) {
        const size_t minPrefix = hyphenator.minPrefix();
        const size_t minSuffix = hyphenator.minSuffix();
        for (size_t idx = minPrefix; idx + minSuffix <= segment.size(); ++idx) {
          segIndexes.push_back(idx);
        }
      }

      for (const size_t idx : segIndexes) {
        assert(idx > 0 && idx < segment.size());
        if (idx == 0 || idx >= segment.size()) continue;
        const size_t cpIdx = segStart + idx;
        if (cpIdx < cps.size()) {
          outBreaks.push_back({cps[cpIdx].byteOffset, true});
        }
      }
    }

    segStart = i + 1;
  }
}

void appendHungarianSlashBreaks(const std::vector<CodepointInfo>& cps,
                                std::vector<Hyphenator::BreakInfo>& outBreaks) {
  for (size_t i = 1; i + 1 < cps.size(); ++i) {
    if (cps[i].value != '/' || !isAlphabetic(cps[i - 1].value) || !isAlphabetic(cps[i + 1].value)) {
      continue;
    }
    // The slash is already visible, so a line break after it must not insert '-'.
    outBreaks.push_back({cps[i + 1].byteOffset, false});
  }
}

void appendApostropheContractionBreaks(const std::vector<CodepointInfo>& cps,
                                       std::vector<Hyphenator::BreakInfo>& outBreaks) {
  constexpr size_t kMinLeftSegmentLen = 3;
  constexpr size_t kMinRightSegmentLen = 3;
  size_t segmentStart = 0;

  for (size_t i = 0; i < cps.size(); ++i) {
    if (isSegmentSeparator(cps[i].value)) {
      if (isApostrophe(cps[i].value) && i > 0 && i + 1 < cps.size() && isAlphabetic(cps[i - 1].value) &&
          isAlphabetic(cps[i + 1].value)) {
        size_t leftPrefixLen = 0;
        for (size_t j = segmentStart; j < i; ++j) {
          if (isAlphabetic(cps[j].value)) {
            ++leftPrefixLen;
          }
        }

        size_t rightSuffixLen = 0;
        for (size_t j = i + 1; j < cps.size() && !isSegmentSeparator(cps[j].value); ++j) {
          if (isAlphabetic(cps[j].value)) {
            ++rightSuffixLen;
          }
        }

        if (leftPrefixLen >= kMinLeftSegmentLen && rightSuffixLen >= kMinRightSegmentLen) {
          outBreaks.push_back({cps[i + 1].byteOffset, false});
        }
      }
      segmentStart = i + 1;
    }
  }
}

bool isHungarianVowel(const uint32_t cp) {
  switch (cp) {
    case 'a':
    case 'A':
    case 0x00E1:
    case 0x00C1:
    case 'e':
    case 'E':
    case 0x00E9:
    case 0x00C9:
    case 'i':
    case 'I':
    case 0x00ED:
    case 0x00CD:
    case 'o':
    case 'O':
    case 0x00F3:
    case 0x00D3:
    case 0x00F6:
    case 0x00D6:
    case 0x0151:
    case 0x0150:
    case 'u':
    case 'U':
    case 0x00FA:
    case 0x00DA:
    case 0x00FC:
    case 0x00DC:
    case 0x0171:
    case 0x0170:
      return true;
    default:
      return false;
  }
}

bool hasHungarianVowel(const std::vector<CodepointInfo>& cps, const size_t begin, const size_t end) {
  for (size_t i = begin; i < end; ++i) {
    if (isHungarianVowel(cps[i].value)) return true;
  }
  return false;
}

uint32_t asciiLower(const uint32_t cp) {
  return (cp >= 'A' && cp <= 'Z') ? cp + ('a' - 'A') : cp;
}

struct HungarianCompoundStemRule {
  const char32_t* left;
  const char32_t* rightStem;
};

static constexpr HungarianCompoundStemRule kHungarianCompoundStemRules[] = {
    {U"meg", U"gyull"},       {U"meg", U"gyón"},         {U"meg", U"győz"},
    {U"meg", U"gyaláz"},      {U"kis", U"szék"},         {U"kis", U"szoba"},
    {U"kis", U"szekrény"},    {U"ruhás", U"szekrény"},   {U"vas", U"szeg"},
    {U"cipős", U"szekrény"},  {U"hús", U"szelet"},      {U"ideg", U"gyógyász"},
    {U"gyors", U"szolgálat"}, {U"okos", U"szemüveg"},    {U"nyolc", U"csillag"},
    {U"arc", U"csont"},       {U"szín", U"nyom"},        {U"tánc", U"csoport"},
    {U"rossz", U"indulat"},    {U"rossz", U"íz"},
};

size_t utf32Length(const char32_t* text) {
  size_t length = 0;
  while (text[length] != U'\0') ++length;
  return length;
}

bool matchesHungarianStem(const std::vector<CodepointInfo>& cps, const size_t start, const char32_t* stem) {
  for (size_t i = 0; stem[i] != U'\0'; ++i) {
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

bool isInsideHungarianCompoundLeft(const std::vector<CodepointInfo>& cps, const size_t split) {
  for (const auto& rule : kHungarianCompoundStemRules) {
    const size_t leftLength = utf32Length(rule.left);
    if (split >= leftLength) continue;
    if (!matchesHungarianStem(cps, 0, rule.left)) continue;
    if (matchesHungarianStem(cps, leftLength, rule.rightStem)) return true;
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

size_t hungarianConsonantGraphemeLength(const std::vector<CodepointInfo>& cps, const size_t start) {
  if (start >= cps.size()) return 0;
  const uint32_t first = asciiLower(cps[start].value);
  if (!isAlphabetic(cps[start].value) || isHungarianVowel(cps[start].value)) return 0;

  const uint32_t second = start + 1 < cps.size() ? asciiLower(cps[start + 1].value) : 0;
  const uint32_t third = start + 2 < cps.size() ? asciiLower(cps[start + 2].value) : 0;

  if (first == 'd' && second == 'z' && third == 's') return 3;
  if ((first == 'c' && second == 's') || (first == 'd' && second == 'z') ||
      (first == 'g' && second == 'y') || (first == 'l' && second == 'y') ||
      (first == 'n' && second == 'y') || (first == 's' && second == 'z') ||
      (first == 't' && second == 'y') || (first == 'z' && second == 's')) {
    return 2;
  }
  return 1;
}

void appendHungarianSingleLetterPrefixBreak(const std::vector<CodepointInfo>& cps,
                                             const LanguageHyphenator& hyphenator,
                                             std::vector<Hyphenator::BreakInfo>& outBreaks) {
  if (hyphenator.minPrefix() != 1 || cps.size() < 3) return;
  if (cps.size() - 1 < hyphenator.minSuffix()) return;
  if (!isHungarianVowel(cps[0].value)) return;

  const size_t consonantLen = hungarianConsonantGraphemeLength(cps, 1);
  if (consonantLen == 0) return;
  const size_t nextVowel = 1 + consonantLen;
  if (nextVowel >= cps.size() || !isHungarianVowel(cps[nextVowel].value)) return;

  outBreaks.push_back({byteOffsetForIndex(cps, 1), true});
}

void appendHungarianExtendedBreaks(const std::vector<CodepointInfo>& cps,
                                   std::vector<Hyphenator::BreakInfo>& outBreaks) {
  struct Rule {
    const char* compact;
    size_t length;
    Hyphenator::Replacement replacement;
  };
  static constexpr Rule rules[] = {
      {"ccs", 3, Hyphenator::Replacement::AppendS},   {"ggy", 3, Hyphenator::Replacement::AppendY},
      {"lly", 3, Hyphenator::Replacement::AppendY},   {"nny", 3, Hyphenator::Replacement::AppendY},
      {"ssz", 3, Hyphenator::Replacement::AppendZ},   {"tty", 3, Hyphenator::Replacement::AppendY},
      {"zzs", 3, Hyphenator::Replacement::AppendS},   {"ddz", 3, Hyphenator::Replacement::AppendZ},
      {"ddzs", 4, Hyphenator::Replacement::AppendZS},
  };

  for (size_t i = 0; i < cps.size(); ++i) {
    for (const auto& rule : rules) {
      if (i + rule.length > cps.size()) continue;
      bool matches = true;
      for (size_t j = 0; j < rule.length; ++j) {
        if (asciiLower(cps[i + j].value) != static_cast<uint32_t>(rule.compact[j])) {
          matches = false;
          break;
        }
      }
      if (!matches) continue;

      if (i == 0 || i + rule.length >= cps.size()) continue;
      if (!isHungarianVowel(cps[i - 1].value) || !isHungarianVowel(cps[i + rule.length].value)) continue;

      const size_t split = i + 1;
      if (split == 0 || split >= cps.size()) continue;
      if (isHungarianCompoundBoundary(cps, split) || isInsideHungarianCompoundLeft(cps, split)) continue;
      if (!hasHungarianVowel(cps, 0, split) || !hasHungarianVowel(cps, split, cps.size())) continue;
      outBreaks.push_back({byteOffsetForIndex(cps, split), true, rule.replacement});
    }
  }
}

void sortAndDedupeBreakInfos(std::vector<Hyphenator::BreakInfo>& infos) {
  std::sort(infos.begin(), infos.end(), [](const Hyphenator::BreakInfo& a, const Hyphenator::BreakInfo& b) {
    if (a.byteOffset != b.byteOffset) {
      return a.byteOffset < b.byteOffset;
    }
    if (a.replacement != b.replacement) return a.replacement > b.replacement;
    return a.requiresInsertedHyphen < b.requiresInsertedHyphen;
  });

  infos.erase(std::unique(infos.begin(), infos.end(),
                          [](const Hyphenator::BreakInfo& a, const Hyphenator::BreakInfo& b) {
                            return a.byteOffset == b.byteOffset;
                          }),
              infos.end());
}

}  // namespace

std::vector<Hyphenator::BreakInfo> Hyphenator::breakOffsets(const std::string& word, const bool includeFallback) {
  if (word.empty()) {
    return {};
  }

  auto cps = collectCodepoints(word);
  if (!softHyphenEnabled_) {
    cps.erase(std::remove_if(cps.begin(), cps.end(), [](const CodepointInfo& cp) { return isSoftHyphen(cp.value); }), cps.end());
  }
  if (preferredLanguageIsHungarian_) {
    normalizeHungarianProcessingCodepoints(cps);
  }
  trimSurroundingPunctuationAndFootnote(cps);
  const auto* hyphenator = cachedHyphenator_;
  const bool useHungarianExtended = hungarianExtended_ && preferredLanguageIsHungarian_;
  if (useHungarianExtended) {
    stripHungarianClosingQuoteBeforeSuffix(cps);
  }

  bool hasApostropheLikeSeparator = false;
  bool hasHungarianSlashSeparator = false;
  for (const auto& cp : cps) {
    if (isApostrophe(cp.value)) {
      hasApostropheLikeSeparator = true;
    }
    if (useHungarianExtended && cp.value == '/') {
      hasHungarianSlashSeparator = true;
    }
  }

  auto explicitBreakInfos = buildExplicitBreakInfos(cps, useHungarianExtended);
  if (!explicitBreakInfos.empty()) {
    if (hyphenator) {
      appendSegmentPatternBreaks(cps, *hyphenator, /*includeFallback=*/false, useHungarianExtended,
                                 explicitBreakInfos);
    }
    if (hasApostropheLikeSeparator) {
      appendApostropheContractionBreaks(cps, explicitBreakInfos);
    }
    if (useHungarianExtended) {
      appendHungarianSlashBreaks(cps, explicitBreakInfos);
      appendHungarianExtendedBreaks(cps, explicitBreakInfos);
    }
    sortAndDedupeBreakInfos(explicitBreakInfos);
    return explicitBreakInfos;
  }

  if (hasApostropheLikeSeparator || hasHungarianSlashSeparator) {
    std::vector<BreakInfo> segmentedBreaks;
    if (hyphenator) {
      appendSegmentPatternBreaks(cps, *hyphenator, includeFallback, useHungarianExtended, segmentedBreaks);
    }
    if (hasApostropheLikeSeparator) {
      appendApostropheContractionBreaks(cps, segmentedBreaks);
    }
    if (useHungarianExtended) {
      appendHungarianSlashBreaks(cps, segmentedBreaks);
      appendHungarianExtendedBreaks(cps, segmentedBreaks);
    }
    sortAndDedupeBreakInfos(segmentedBreaks);
    return segmentedBreaks;
  }

  std::vector<size_t> indexes;
  if (hyphenator) {
    indexes = hyphenator->breakIndexes(cps);
  }

  if (includeFallback && indexes.empty()) {
    const size_t minPrefix = hyphenator ? hyphenator->minPrefix() : LiangWordConfig::kDefaultMinPrefix;
    const size_t minSuffix = hyphenator ? hyphenator->minSuffix() : LiangWordConfig::kDefaultMinSuffix;
    for (size_t idx = minPrefix; idx + minSuffix <= cps.size(); ++idx) {
      indexes.push_back(idx);
    }
  }

  std::vector<Hyphenator::BreakInfo> breaks;
  if (preferredLanguageIsHungarian_ && hyphenator) {
    appendHungarianSingleLetterPrefixBreak(cps, *hyphenator, breaks);
    appendHungarianCompoundBoundaryBreaks(cps, breaks);
  }
  if (useHungarianExtended) {
    appendHungarianExtendedBreaks(cps, breaks);
  }

  if (indexes.empty() && breaks.empty()) {
    return {};
  }

  breaks.reserve(breaks.size() + indexes.size());
  for (const size_t idx : indexes) {
    bool needsHyphen = true;
    if (idx < cps.size() && utf8IsCjkBreakable(cps[idx].value)) {
      needsHyphen = false;
    } else if (idx > 0 && utf8IsCjkBreakable(cps[idx - 1].value)) {
      needsHyphen = false;
    }
    breaks.push_back({byteOffsetForIndex(cps, idx), needsHyphen});
  }

  sortAndDedupeBreakInfos(breaks);
  return breaks;
}

std::vector<Hyphenator::BreakInfo> Hyphenator::softHyphenBreakOffsets(const std::string& word) {
  auto cps = collectCodepoints(word);
  std::vector<BreakInfo> out;
  for (size_t i = 1; i + 1 < cps.size(); ++i) {
    if (isSoftHyphen(cps[i].value) && isAlphabetic(cps[i - 1].value) && isAlphabetic(cps[i + 1].value)) {
      out.push_back({cps[i + 1].byteOffset, true});
    }
  }
  return out;
}

std::vector<Hyphenator::BreakInfo> Hyphenator::breakOffsetsForLanguage(const std::string& word,
                                                                       const bool includeFallback,
                                                                       const std::string& language) {
  const auto* previousHyphenator = cachedHyphenator_;
  const bool previousHungarian = preferredLanguageIsHungarian_;
  setPreferredLanguage(language);
  auto breaks = breakOffsets(word, includeFallback);
  cachedHyphenator_ = previousHyphenator;
  preferredLanguageIsHungarian_ = previousHungarian;
  return breaks;
}

void Hyphenator::setPreferredLanguage(const std::string& lang) {
  cachedHyphenator_ = hyphenatorForLanguage(lang);
  std::string primary;
  primary.reserve(lang.size());
  for (char c : lang) {
    if (c == '-' || c == '_') break;
    if (c >= 'A' && c <= 'Z') c = static_cast<char>(c - 'A' + 'a');
    primary.push_back(c);
  }
  preferredLanguageIsHungarian_ = primary == "hu" || primary == "hun";
}

void Hyphenator::setHungarianExtended(const bool enabled) { hungarianExtended_ = enabled; }
void Hyphenator::setSoftHyphenEnabled(const bool enabled) { softHyphenEnabled_ = enabled; }