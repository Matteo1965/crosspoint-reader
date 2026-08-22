from pathlib import Path


def patch(path, old, new, marker=None):
    p = Path(path)
    text = p.read_text(encoding='utf-8')
    if marker and marker in text:
        return
    count = text.count(old)
    if count != 1:
        raise SystemExit(f'{path}: expected exactly one match, got {count}')
    p.write_text(text.replace(old, new, 1), encoding='utf-8')

# Reader render spec / persistent setting
patch('lib/Epub/Epub/ReaderRenderSpec.h',
      '  bool hyphenationEnabled = false;\n  bool embeddedStyle = true;',
      '  bool hyphenationEnabled = false;\n  bool hungarianHyphenationExtended = false;\n  bool embeddedStyle = true;',
      'hungarianHyphenationExtended')

patch('src/CrossPointSettings.h',
      '  uint8_t hyphenationEnabled = 0;\n\n  // Reader screen margin settings',
      '  uint8_t hyphenationEnabled = 0;\n  uint8_t hungarianHyphenationExtended = 0;\n\n  // Reader screen margin settings',
      'uint8_t hungarianHyphenationExtended')

patch('src/CrossPointSettings.cpp',
      '  spec.hyphenationEnabled = hyphenationEnabled != 0;\n  spec.embeddedStyle = embeddedStyle != 0;',
      '  spec.hyphenationEnabled = hyphenationEnabled != 0;\n  spec.hungarianHyphenationExtended = hungarianHyphenationExtended != 0;\n  spec.embeddedStyle = embeddedStyle != 0;',
      'spec.hungarianHyphenationExtended')

patch('src/SettingsListBase.h',
      '        SettingInfo::Toggle(StrId::STR_HYPHENATION, &CrossPointSettings::hyphenationEnabled, "hyphenationEnabled",\n                            StrId::STR_CAT_READER)\n            .withTextSettings(),',
      '        SettingInfo::Toggle(StrId::STR_HYPHENATION, &CrossPointSettings::hyphenationEnabled, "hyphenationEnabled",\n                            StrId::STR_CAT_READER)\n            .withTextSettings(),\n        SettingInfo::Toggle(StrId::STR_HYPHENATION, &CrossPointSettings::hungarianHyphenationExtended,\n                            "hungarianHyphenationExtended", StrId::STR_CAT_READER)\n            .withTextSettings(),',
      '"hungarianHyphenationExtended"')

# Hyphenator API
patch('lib/Epub/Epub/hyphenation/Hyphenator.h',
      '#include <cstddef>\n#include <string>',
      '#include <cstddef>\n#include <cstdint>\n#include <string>',
      '#include <cstdint>')
patch('lib/Epub/Epub/hyphenation/Hyphenator.h',
      'class Hyphenator {\n public:\n  struct BreakInfo {',
      'class Hyphenator {\n public:\n  enum class Replacement : uint8_t { None = 0, AppendY, AppendZ, AppendS, AppendZS };\n\n  struct BreakInfo {',
      'enum class Replacement')
patch('lib/Epub/Epub/hyphenation/Hyphenator.h',
      '                                  //         (explicit \'-\' or eligible apostrophe contraction boundary).\n  };',
      '                                  //         (explicit \'-\' or eligible apostrophe contraction boundary).\n    Replacement replacement = Replacement::None;\n  };',
      'Replacement replacement')
patch('lib/Epub/Epub/hyphenation/Hyphenator.h',
      '  static void setPreferredLanguage(const std::string& lang);\n\n private:\n  static const LanguageHyphenator* cachedHyphenator_;',
      '  static void setPreferredLanguage(const std::string& lang);\n  static void setHungarianExtended(bool enabled);\n\n private:\n  static const LanguageHyphenator* cachedHyphenator_;\n  static bool preferredLanguageIsHungarian_;\n  static bool hungarianExtended_;',
      'setHungarianExtended')

# Hyphenator implementation
patch('lib/Epub/Epub/hyphenation/Hyphenator.cpp',
      'const LanguageHyphenator* Hyphenator::cachedHyphenator_ = nullptr;\n',
      'const LanguageHyphenator* Hyphenator::cachedHyphenator_ = nullptr;\nbool Hyphenator::preferredLanguageIsHungarian_ = false;\nbool Hyphenator::hungarianExtended_ = false;\n',
      'preferredLanguageIsHungarian_ = false')
patch('lib/Epub/Epub/hyphenation/Hyphenator.cpp',
      '{"ukr", "uk"}, {"swe", "sv"}, {"fin", "fi"}};',
      '{"ukr", "uk"}, {"swe", "sv"}, {"fin", "fi"}, {"hun", "hu"}};',
      '{"hun", "hu"}')

helpers = r'''bool isHungarianVowel(const uint32_t cp) {
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

      const size_t split = i + 1;
      if (split == 0 || split >= cps.size()) continue;
      // Readability guard: do not create a special split if either rendered
      // word part would contain no Hungarian vowel (e.g. gally -> galy-ly).
      if (!hasHungarianVowel(cps, 0, split) || !hasHungarianVowel(cps, split, cps.size())) continue;
      outBreaks.push_back({byteOffsetForIndex(cps, split), true, rule.replacement});
    }
  }
}

'''
patch('lib/Epub/Epub/hyphenation/Hyphenator.cpp',
      'void sortAndDedupeBreakInfos(std::vector<Hyphenator::BreakInfo>& infos) {',
      helpers + 'void sortAndDedupeBreakInfos(std::vector<Hyphenator::BreakInfo>& infos) {',
      'appendHungarianExtendedBreaks')
patch('lib/Epub/Epub/hyphenation/Hyphenator.cpp',
      '    if (a.byteOffset != b.byteOffset) {\n      return a.byteOffset < b.byteOffset;\n    }\n    return a.requiresInsertedHyphen < b.requiresInsertedHyphen;',
      '    if (a.byteOffset != b.byteOffset) {\n      return a.byteOffset < b.byteOffset;\n    }\n    if (a.replacement != b.replacement) return a.replacement > b.replacement;\n    return a.requiresInsertedHyphen < b.requiresInsertedHyphen;',
      'a.replacement != b.replacement')
patch('lib/Epub/Epub/hyphenation/Hyphenator.cpp',
      '    // Merge all break points into ascending byte-offset order.\n    sortAndDedupeBreakInfos(explicitBreakInfos);',
      '    // Merge all break points into ascending byte-offset order.\n    if (hungarianExtended_ && preferredLanguageIsHungarian_) {\n      appendHungarianExtendedBreaks(cps, explicitBreakInfos);\n    }\n    sortAndDedupeBreakInfos(explicitBreakInfos);',
      'appendHungarianExtendedBreaks(cps, explicitBreakInfos)')
patch('lib/Epub/Epub/hyphenation/Hyphenator.cpp',
      '    appendApostropheContractionBreaks(cps, segmentedBreaks);\n    sortAndDedupeBreakInfos(segmentedBreaks);',
      '    appendApostropheContractionBreaks(cps, segmentedBreaks);\n    if (hungarianExtended_ && preferredLanguageIsHungarian_) {\n      appendHungarianExtendedBreaks(cps, segmentedBreaks);\n    }\n    sortAndDedupeBreakInfos(segmentedBreaks);',
      'appendHungarianExtendedBreaks(cps, segmentedBreaks)')
patch('lib/Epub/Epub/hyphenation/Hyphenator.cpp',
      '  if (indexes.empty()) {\n    return {};\n  }\n\n  std::vector<Hyphenator::BreakInfo> breaks;\n  breaks.reserve(indexes.size());',
      '  std::vector<Hyphenator::BreakInfo> breaks;\n  if (hungarianExtended_ && preferredLanguageIsHungarian_) {\n    appendHungarianExtendedBreaks(cps, breaks);\n  }\n\n  if (indexes.empty() && breaks.empty()) {\n    return {};\n  }\n\n  breaks.reserve(breaks.size() + indexes.size());',
      'indexes.empty() && breaks.empty()')
patch('lib/Epub/Epub/hyphenation/Hyphenator.cpp',
      '  return breaks;\n}\n\nstd::vector<Hyphenator::BreakInfo> Hyphenator::breakOffsetsForLanguage',
      '  sortAndDedupeBreakInfos(breaks);\n  return breaks;\n}\n\nstd::vector<Hyphenator::BreakInfo> Hyphenator::breakOffsetsForLanguage',
      'sortAndDedupeBreakInfos(breaks);\n  return breaks;\n}\n\nstd::vector<Hyphenator::BreakInfo> Hyphenator::breakOffsetsForLanguage')
patch('lib/Epub/Epub/hyphenation/Hyphenator.cpp',
      '  const auto* previousHyphenator = cachedHyphenator_;\n  cachedHyphenator_ = hyphenatorForLanguage(language);\n  auto breaks = breakOffsets(word, includeFallback);\n  cachedHyphenator_ = previousHyphenator;\n  return breaks;',
      '  const auto* previousHyphenator = cachedHyphenator_;\n  const bool previousHungarian = preferredLanguageIsHungarian_;\n  setPreferredLanguage(language);\n  auto breaks = breakOffsets(word, includeFallback);\n  cachedHyphenator_ = previousHyphenator;\n  preferredLanguageIsHungarian_ = previousHungarian;\n  return breaks;',
      'const bool previousHungarian')
patch('lib/Epub/Epub/hyphenation/Hyphenator.cpp',
      'void Hyphenator::setPreferredLanguage(const std::string& lang) { cachedHyphenator_ = hyphenatorForLanguage(lang); }',
      '''void Hyphenator::setPreferredLanguage(const std::string& lang) {
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

void Hyphenator::setHungarianExtended(const bool enabled) { hungarianExtended_ = enabled; }''',
      'void Hyphenator::setHungarianExtended')

# ParsedText replacement-aware split, adapted to the current focus-reading implementation
patch('lib/Epub/Epub/ParsedText.cpp',
      '  bool chosenNeedsHyphen = true;\n',
      '  bool chosenNeedsHyphen = true;\n  Hyphenator::Replacement chosenReplacement = Hyphenator::Replacement::None;\n',
      'chosenReplacement = Hyphenator::Replacement::None')
patch('lib/Epub/Epub/ParsedText.cpp',
      '    const bool needsHyphen = info.requiresInsertedHyphen;\n    const int prefixWidth = measureFocusWordWidth(renderer, fontId, word.substr(0, offset), style,\n                                                  focusBoundaryBefore(focusBoundary, offset), needsHyphen);',
      '''    const bool needsHyphen = info.requiresInsertedHyphen;
    std::string candidatePrefix = word.substr(0, offset);
    const bool replacementUppercase = offset > 0 && word[offset - 1] >= 'A' && word[offset - 1] <= 'Z';
    switch (info.replacement) {
      case Hyphenator::Replacement::AppendY:
        candidatePrefix.push_back(replacementUppercase ? 'Y' : 'y');
        break;
      case Hyphenator::Replacement::AppendZ:
        candidatePrefix.push_back(replacementUppercase ? 'Z' : 'z');
        break;
      case Hyphenator::Replacement::AppendS:
        candidatePrefix.push_back(replacementUppercase ? 'S' : 's');
        break;
      case Hyphenator::Replacement::AppendZS:
        candidatePrefix += replacementUppercase ? "ZS" : "zs";
        break;
      default:
        break;
    }
    const int prefixWidth = measureFocusWordWidth(renderer, fontId, candidatePrefix, style,
                                                  focusBoundaryBefore(focusBoundary, offset), needsHyphen);''',
      'switch (info.replacement)')
patch('lib/Epub/Epub/ParsedText.cpp',
      '    chosenOffset = offset;\n    chosenNeedsHyphen = needsHyphen;\n',
      '    chosenOffset = offset;\n    chosenNeedsHyphen = needsHyphen;\n    chosenReplacement = info.replacement;\n',
      'chosenReplacement = info.replacement')
patch('lib/Epub/Epub/ParsedText.cpp',
      '  std::string remainder = word.substr(chosenOffset);\n  words[wordIndex].resize(chosenOffset);\n  if (chosenNeedsHyphen) {',
      '''  std::string remainder = word.substr(chosenOffset);
  words[wordIndex].resize(chosenOffset);
  const bool replacementUppercase =
      chosenOffset > 0 && word[chosenOffset - 1] >= 'A' && word[chosenOffset - 1] <= 'Z';
  switch (chosenReplacement) {
    case Hyphenator::Replacement::AppendY:
      words[wordIndex].push_back(replacementUppercase ? 'Y' : 'y');
      break;
    case Hyphenator::Replacement::AppendZ:
      words[wordIndex].push_back(replacementUppercase ? 'Z' : 'z');
      break;
    case Hyphenator::Replacement::AppendS:
      words[wordIndex].push_back(replacementUppercase ? 'S' : 's');
      break;
    case Hyphenator::Replacement::AppendZS:
      words[wordIndex] += replacementUppercase ? "ZS" : "zs";
      break;
    default:
      break;
  }
  if (chosenNeedsHyphen) {''',
      'switch (chosenReplacement)')

# Cache key / section version
patch('lib/Epub/Epub/Section.cpp',
      'constexpr uint8_t SECTION_FILE_VERSION = 39;',
      'constexpr uint8_t SECTION_FILE_VERSION = 40;',
      'constexpr uint8_t SECTION_FILE_VERSION = 40;')
patch('lib/Epub/Epub/Section.cpp',
      '                                 sizeof(uint16_t) + sizeof(uint16_t) + sizeof(uint16_t) + sizeof(bool) + sizeof(bool) +\n                                 sizeof(uint8_t) + sizeof(bool)',
      '                                 sizeof(uint16_t) + sizeof(uint16_t) + sizeof(uint16_t) + sizeof(bool) + sizeof(bool) +\n                                 sizeof(bool) + sizeof(uint8_t) + sizeof(bool)',
      'sizeof(bool) + sizeof(bool) +\n                                 sizeof(bool) + sizeof(uint8_t)')
patch('lib/Epub/Epub/Section.cpp',
      '                                   sizeof(spec.hyphenationEnabled) + sizeof(spec.embeddedStyle) +',
      '                                   sizeof(spec.hyphenationEnabled) + sizeof(spec.hungarianHyphenationExtended) +\n                                   sizeof(spec.embeddedStyle) +',
      'sizeof(spec.hungarianHyphenationExtended)')
patch('lib/Epub/Epub/Section.cpp',
      '  serialization::writePod(file, spec.hyphenationEnabled);\n  serialization::writePod(file, spec.embeddedStyle);',
      '  serialization::writePod(file, spec.hyphenationEnabled);\n  serialization::writePod(file, spec.hungarianHyphenationExtended);\n  serialization::writePod(file, spec.embeddedStyle);',
      'serialization::writePod(file, spec.hungarianHyphenationExtended)')
patch('lib/Epub/Epub/Section.cpp',
      '    bool fileHyphenationEnabled;\n    bool fileEmbeddedStyle;',
      '    bool fileHyphenationEnabled;\n    bool fileHungarianHyphenationExtended;\n    bool fileEmbeddedStyle;',
      'bool fileHungarianHyphenationExtended')
patch('lib/Epub/Epub/Section.cpp',
      '    serialization::readPod(file, fileHyphenationEnabled);\n    serialization::readPod(file, fileEmbeddedStyle);',
      '    serialization::readPod(file, fileHyphenationEnabled);\n    serialization::readPod(file, fileHungarianHyphenationExtended);\n    serialization::readPod(file, fileEmbeddedStyle);',
      'serialization::readPod(file, fileHungarianHyphenationExtended)')
patch('lib/Epub/Epub/Section.cpp',
      '        spec.hyphenationEnabled != fileHyphenationEnabled || spec.embeddedStyle != fileEmbeddedStyle ||',
      '        spec.hyphenationEnabled != fileHyphenationEnabled ||\n        spec.hungarianHyphenationExtended != fileHungarianHyphenationExtended ||\n        spec.embeddedStyle != fileEmbeddedStyle ||',
      'spec.hungarianHyphenationExtended != fileHungarianHyphenationExtended')
patch('lib/Epub/Epub/Section.cpp',
      '  Hyphenator::setPreferredLanguage(epub->getLanguage());\n  build_ = std::move(ctx);',
      '  Hyphenator::setPreferredLanguage(epub->getLanguage());\n  Hyphenator::setHungarianExtended(spec.hungarianHyphenationExtended);\n  build_ = std::move(ctx);',
      'Hyphenator::setHungarianExtended')

# Text settings UI
patch('src/activities/settings/TextSettingsActivity.h',
      '  enum class StyleRow { FocusReading, Hyphenation, EmbeddedStyle, AntiAliasing, Count };',
      '  enum class StyleRow { FocusReading, Hyphenation, HungarianHyphenation, EmbeddedStyle, AntiAliasing, Count };',
      'HungarianHyphenation')
patch('src/activities/settings/TextSettingsActivity.cpp',
      'constexpr StrId STYLE_ROW_NAME_IDS[] = {StrId::STR_FOCUS_READING, StrId::STR_HYPHENATION, StrId::STR_EMBEDDED_STYLE,\n                                        StrId::STR_TEXT_AA};',
      'constexpr StrId STYLE_ROW_NAME_IDS[] = {StrId::STR_FOCUS_READING, StrId::STR_HYPHENATION, StrId::STR_HYPHENATION,\n                                        StrId::STR_EMBEDDED_STYLE, StrId::STR_TEXT_AA};',
      'StrId::STR_HYPHENATION, StrId::STR_HYPHENATION')
patch('src/activities/settings/TextSettingsActivity.cpp',
      '      case Tab::Style:\n        item.label = I18N.get(STYLE_ROW_NAME_IDS[i]);\n        break;',
      '      case Tab::Style:\n        item.label = i == static_cast<int>(StyleRow::HungarianHyphenation) ? "Magyar elválasztás"\n                                                                           : I18N.get(STYLE_ROW_NAME_IDS[i]);\n        break;',
      '"Magyar elválasztás"')
patch('src/activities/settings/TextSettingsActivity.cpp',
      '    case StyleRow::Hyphenation:\n      SETTINGS.hyphenationEnabled = !SETTINGS.hyphenationEnabled;\n      break;\n    case StyleRow::EmbeddedStyle:',
      '    case StyleRow::Hyphenation:\n      SETTINGS.hyphenationEnabled = !SETTINGS.hyphenationEnabled;\n      break;\n    case StyleRow::HungarianHyphenation:\n      SETTINGS.hungarianHyphenationExtended = !SETTINGS.hungarianHyphenationExtended;\n      break;\n    case StyleRow::EmbeddedStyle:',
      'SETTINGS.hungarianHyphenationExtended = !SETTINGS.hungarianHyphenationExtended')
patch('src/activities/settings/TextSettingsActivity.cpp',
      '    case StyleRow::Hyphenation:\n      return SETTINGS.hyphenationEnabled ? tr(STR_STATE_ON) : tr(STR_STATE_OFF);\n    case StyleRow::EmbeddedStyle:',
      '    case StyleRow::Hyphenation:\n      return SETTINGS.hyphenationEnabled ? tr(STR_STATE_ON) : tr(STR_STATE_OFF);\n    case StyleRow::HungarianHyphenation:\n      return SETTINGS.hungarianHyphenationExtended ? "Kiterjesztett" : "Alap";\n    case StyleRow::EmbeddedStyle:',
      '"Kiterjesztett" : "Alap"')
patch('src/activities/settings/TextSettingsActivity.cpp',
      '  return row == StyleRow::Hyphenation || row == StyleRow::EmbeddedStyle || row == StyleRow::AntiAliasing;',
      '  return row == StyleRow::Hyphenation || row == StyleRow::HungarianHyphenation ||\n         row == StyleRow::EmbeddedStyle || row == StyleRow::AntiAliasing;',
      'row == StyleRow::HungarianHyphenation')

print('Extended Hungarian hyphenation merge applied successfully.')
