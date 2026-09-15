from pathlib import Path


def replace_once(path, old, new):
    p = Path(path)
    text = p.read_text(encoding="utf-8")
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"CPHUN-131: {path}: expected one match, found {count}: {old[:100]!r}")
    p.write_text(text.replace(old, new, 1), encoding="utf-8")


# Persisted setting: five threshold pairs, default index 2 = 2-2.
replace_once(
    "src/CrossPointSettings.h",
    "  uint8_t hyphenationEnabled = 0;\n  uint8_t hungarianHyphenationExtended = 0;\n  uint8_t softHyphenEnabled = 0;",
    "  uint8_t hyphenationEnabled = 0;\n  uint8_t hungarianHyphenationExtended = 0;\n  // Hungarian Liang minPrefix/minSuffix preset: 0=1-1, 1=1-2, 2=2-2, 3=2-3, 4=3-3.\n  uint8_t hyphenationThreshold = 2;\n  uint8_t softHyphenEnabled = 0;",
)
replace_once(
    "src/CrossPointSettings.cpp",
    '  doc["softHyphenEnabled"] = softHyphenEnabled;',
    '  doc["hyphenationThreshold"] = hyphenationThreshold;\n  doc["softHyphenEnabled"] = softHyphenEnabled;',
)
replace_once(
    "src/CrossPointSettings.cpp",
    '  softHyphenEnabled = (doc["softHyphenEnabled"] | (uint8_t)0) ? 1 : 0;',
    '  hyphenationThreshold = doc["hyphenationThreshold"] | (uint8_t)2;\n  if (hyphenationThreshold > 4) {\n    hyphenationThreshold = 2;\n    needsResave = true;\n  }\n  softHyphenEnabled = (doc["softHyphenEnabled"] | (uint8_t)0) ? 1 : 0;',
)
replace_once(
    "src/CrossPointSettings.cpp",
    "  spec.hungarianHyphenationExtended = hungarianHyphenationExtended != 0;",
    "  spec.hungarianHyphenationExtended = hungarianHyphenationExtended != 0;\n  static constexpr uint8_t kHyphenMinPrefix[] = {1, 1, 2, 2, 3};\n  static constexpr uint8_t kHyphenMinSuffix[] = {1, 2, 2, 3, 3};\n  const uint8_t threshold = hyphenationThreshold <= 4 ? hyphenationThreshold : 2;\n  spec.hungarianMinPrefix = kHyphenMinPrefix[threshold];\n  spec.hungarianMinSuffix = kHyphenMinSuffix[threshold];",
)

# The render spec carries the selected minima so cache validation notices changes.
replace_once(
    "lib/Epub/Epub/ReaderRenderSpec.h",
    "  bool hungarianHyphenationExtended = false;\n  bool softHyphenEnabled = false;",
    "  bool hungarianHyphenationExtended = false;\n  uint8_t hungarianMinPrefix = 2;\n  uint8_t hungarianMinSuffix = 2;\n  bool softHyphenEnabled = false;",
)

# Runtime minima: update only the Hungarian LanguageHyphenator; English remains 3/3.
replace_once(
    "lib/Epub/Epub/hyphenation/LanguageHyphenator.h",
    "  size_t minSuffix() const { return config_.minSuffix; }",
    "  size_t minSuffix() const { return config_.minSuffix; }\n  void setMinima(const size_t minPrefix, const size_t minSuffix) {\n    config_.minPrefix = minPrefix;\n    config_.minSuffix = minSuffix;\n  }",
)
replace_once(
    "lib/Epub/Epub/hyphenation/LanguageRegistry.h",
    "LanguageEntryView getLanguageEntries();",
    "LanguageEntryView getLanguageEntries();\nvoid setHungarianHyphenationMinima(size_t minPrefix, size_t minSuffix);",
)
replace_once(
    "lib/Epub/Epub/hyphenation/LanguageRegistry.cpp",
    "LanguageEntryView getLanguageEntries() {\n  const auto& allEntries = entries();\n  return LanguageEntryView{allEntries.data(), allEntries.size()};\n}",
    "LanguageEntryView getLanguageEntries() {\n  const auto& allEntries = entries();\n  return LanguageEntryView{allEntries.data(), allEntries.size()};\n}\n\nvoid setHungarianHyphenationMinima(const size_t minPrefix, const size_t minSuffix) {\n  hungarianHyphenator.setMinima(minPrefix, minSuffix);\n}",
)
replace_once(
    "lib/Epub/Epub/hyphenation/Hyphenator.h",
    "  static void setHungarianExtended(bool enabled);",
    "  static void setHungarianExtended(bool enabled);\n  static void setHungarianMinima(size_t minPrefix, size_t minSuffix);",
)
replace_once(
    "lib/Epub/Epub/hyphenation/Hyphenator.cpp",
    "void Hyphenator::setHungarianExtended(const bool enabled) { hungarianExtended_ = enabled; }",
    "void Hyphenator::setHungarianExtended(const bool enabled) { hungarianExtended_ = enabled; }\n\nvoid Hyphenator::setHungarianMinima(const size_t minPrefix, const size_t minSuffix) {\n  setHungarianHyphenationMinima(minPrefix, minSuffix);\n}",
)

# Cache format + application at section-build start.
replace_once("lib/Epub/Epub/Section.cpp", "constexpr uint8_t SECTION_FILE_VERSION = 56;", "constexpr uint8_t SECTION_FILE_VERSION = 57;")
replace_once("lib/Epub/Epub/Section.cpp", "constexpr uint32_t HEADER_SIZE = 46;", "constexpr uint32_t HEADER_SIZE = 48;")
replace_once(
    "lib/Epub/Epub/Section.cpp",
    "                                   sizeof(spec.hyphenationEnabled) + sizeof(spec.hungarianHyphenationExtended) +\n                                   sizeof(spec.hangingPunctuationLimitPx)",
    "                                   sizeof(spec.hyphenationEnabled) + sizeof(spec.hungarianHyphenationExtended) +\n                                   sizeof(spec.hungarianMinPrefix) + sizeof(spec.hungarianMinSuffix) +\n                                   sizeof(spec.hangingPunctuationLimitPx)",
)
replace_once(
    "lib/Epub/Epub/Section.cpp",
    "  serialization::writePod(file, spec.hungarianHyphenationExtended);\n  serialization::writePod(file, spec.hangingPunctuationLimitPx);",
    "  serialization::writePod(file, spec.hungarianHyphenationExtended);\n  serialization::writePod(file, spec.hungarianMinPrefix);\n  serialization::writePod(file, spec.hungarianMinSuffix);\n  serialization::writePod(file, spec.hangingPunctuationLimitPx);",
)
replace_once(
    "lib/Epub/Epub/Section.cpp",
    "    bool fileHungarianHyphenationExtended;\n    uint8_t fileHangingPunctuationLimitPx;",
    "    bool fileHungarianHyphenationExtended;\n    uint8_t fileHungarianMinPrefix;\n    uint8_t fileHungarianMinSuffix;\n    uint8_t fileHangingPunctuationLimitPx;",
)
replace_once(
    "lib/Epub/Epub/Section.cpp",
    "    serialization::readPod(file, fileHungarianHyphenationExtended);\n    serialization::readPod(file, fileHangingPunctuationLimitPx);",
    "    serialization::readPod(file, fileHungarianHyphenationExtended);\n    serialization::readPod(file, fileHungarianMinPrefix);\n    serialization::readPod(file, fileHungarianMinSuffix);\n    serialization::readPod(file, fileHangingPunctuationLimitPx);",
)
replace_once(
    "lib/Epub/Epub/Section.cpp",
    "        spec.hungarianHyphenationExtended != fileHungarianHyphenationExtended ||\n        spec.hangingPunctuationLimitPx != fileHangingPunctuationLimitPx",
    "        spec.hungarianHyphenationExtended != fileHungarianHyphenationExtended ||\n        spec.hungarianMinPrefix != fileHungarianMinPrefix || spec.hungarianMinSuffix != fileHungarianMinSuffix ||\n        spec.hangingPunctuationLimitPx != fileHangingPunctuationLimitPx",
)
replace_once(
    "lib/Epub/Epub/Section.cpp",
    "  Hyphenator::setHungarianExtended(spec.hungarianHyphenationExtended);",
    "  Hyphenator::setHungarianExtended(spec.hungarianHyphenationExtended);\n  Hyphenator::setHungarianMinima(spec.hungarianMinPrefix, spec.hungarianMinSuffix);",
)

# Style menu: Elválasztás -> Elválasztási küszöb -> Beágyazott elválasztás.
replace_once(
    "src/activities/settings/TextSettingsActivity.h",
    "  enum class StyleRow { FocusReading, Hyphenation, SoftHyphen, EmbeddedStyle, AntiAliasing, Count };",
    "  enum class StyleRow { FocusReading, Hyphenation, HyphenationThreshold, SoftHyphen, EmbeddedStyle, AntiAliasing, Count };",
)
replace_once(
    "src/activities/settings/TextSettingsActivity.cpp",
    "constexpr StrId STYLE_ROW_NAME_IDS[] = {StrId::STR_FOCUS_READING, StrId::STR_HYPHENATION, StrId::STR_HYPHENATION,\n                                        StrId::STR_EMBEDDED_STYLE, StrId::STR_TEXT_AA};",
    "constexpr StrId STYLE_ROW_NAME_IDS[] = {StrId::STR_FOCUS_READING, StrId::STR_HYPHENATION, StrId::STR_HYPHENATION,\n                                        StrId::STR_HYPHENATION, StrId::STR_EMBEDDED_STYLE, StrId::STR_TEXT_AA};",
)
replace_once(
    "src/activities/settings/TextSettingsActivity.cpp",
    "        if (i == static_cast<int>(StyleRow::SoftHyphen)) {\n          item.label = I18N.getLanguage() == Language::HU ? \"Beágyazott elválasztás\" : \"Embedded hyphenation\";",
    "        if (i == static_cast<int>(StyleRow::HyphenationThreshold)) {\n          item.label = I18N.getLanguage() == Language::HU ? \"Elválasztási küszöb\" : \"Hyphenation threshold\";\n        } else if (i == static_cast<int>(StyleRow::SoftHyphen)) {\n          item.label = I18N.getLanguage() == Language::HU ? \"Beágyazott elválasztás\" : \"Embedded hyphenation\";",
)
replace_once(
    "src/activities/settings/TextSettingsActivity.cpp",
    "    case Tab::Style:\n      return tr(STR_TOGGLE);",
    "    case Tab::Style:\n      return ringPos() > 0 && static_cast<StyleRow>(ringPos() - 1) == StyleRow::HyphenationThreshold\n                 ? tr(STR_SELECT)\n                 : tr(STR_TOGGLE);",
)
replace_once(
    "src/activities/settings/TextSettingsActivity.cpp",
    "    case StyleRow::SoftHyphen:\n      SETTINGS.softHyphenEnabled = !SETTINGS.softHyphenEnabled;",
    "    case StyleRow::HyphenationThreshold: {\n      const char* options[] = {\"1-1\", \"1-2\", \"2-2\", \"2-3\", \"3-3\"};\n      const int cur = std::min<int>(SETTINGS.hyphenationThreshold, 4);\n      optionPopup_.show(I18N.getLanguage() == Language::HU ? \"Elválasztási küszöb\" : \"Hyphenation threshold\",\n                        options, 5, cur, [](int idx) {\n                          SETTINGS.hyphenationThreshold = static_cast<uint8_t>(idx);\n                          SETTINGS.saveToFile();\n                        });\n      requestUpdate();\n      return;\n    }\n    case StyleRow::SoftHyphen:\n      SETTINGS.softHyphenEnabled = !SETTINGS.softHyphenEnabled;",
)
replace_once(
    "src/activities/settings/TextSettingsActivity.cpp",
    "    case StyleRow::SoftHyphen:\n      return SETTINGS.softHyphenEnabled ? tr(STR_STATE_ON) : tr(STR_STATE_OFF);",
    "    case StyleRow::HyphenationThreshold: {\n      static constexpr const char* labels[] = {\"1-1\", \"1-2\", \"2-2\", \"2-3\", \"3-3\"};\n      return labels[std::min<uint8_t>(SETTINGS.hyphenationThreshold, 4)];\n    }\n    case StyleRow::SoftHyphen:\n      return SETTINGS.softHyphenEnabled ? tr(STR_STATE_ON) : tr(STR_STATE_OFF);",
)
replace_once(
    "src/activities/settings/TextSettingsActivity.cpp",
    "  return row == StyleRow::Hyphenation || row == StyleRow::SoftHyphen || row == StyleRow::EmbeddedStyle ||",
    "  return row == StyleRow::Hyphenation || row == StyleRow::HyphenationThreshold || row == StyleRow::SoftHyphen ||\n         row == StyleRow::EmbeddedStyle ||",
)

# Build identifier.
replace_once(
    "src/CPHUNBuildId.h",
    "CPHUN-260914-130-EXP",
    "CPHUN-260915-131-EXP",
)
