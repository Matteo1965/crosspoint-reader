from pathlib import Path


def replace_once(path: str, old: str, new: str) -> None:
    p = Path(path)
    text = p.read_text(encoding="utf-8")
    if old not in text:
        raise SystemExit(f"Expected text not found in {path}: {old[:120]!r}")
    if text.count(old) != 1:
        raise SystemExit(f"Expected exactly one match in {path}, found {text.count(old)}")
    p.write_text(text.replace(old, new, 1), encoding="utf-8")


replace_once(
    "src/CPHUNBuildId.h",
    "CPHUN-260910-86",
    "CPHUN-260910-87",
)

replace_once(
    "lib/Epub/Epub/hyphenation/Hyphenator.cpp",
    """bool isSegmentSeparator(const uint32_t cp, const bool includeHungarianSlash = false) {\n  return isExplicitHyphen(cp) || isApostrophe(cp) || (includeHungarianSlash && cp == '/');\n}\n""",
    """bool isHungarianExtendedSegmentSeparator(const uint32_t cp) {\n  return cp == '/' || cp == '(' || cp == ')';\n}\n\nbool isSegmentSeparator(const uint32_t cp, const bool includeHungarianExtendedSeparators = false) {\n  return isExplicitHyphen(cp) || isApostrophe(cp) ||\n         (includeHungarianExtendedSeparators && isHungarianExtendedSegmentSeparator(cp));\n}\n""",
)

replace_once(
    "lib/Epub/Epub/hyphenation/Hyphenator.cpp",
    """  bool hasApostropheLikeSeparator = false;\n  bool hasHungarianSlashSeparator = false;\n  for (const auto& cp : cps) {\n    if (isApostrophe(cp.value)) {\n      hasApostropheLikeSeparator = true;\n    }\n    if (useHungarianExtended && cp.value == '/') {\n      hasHungarianSlashSeparator = true;\n    }\n  }\n""",
    """  bool hasApostropheLikeSeparator = false;\n  bool hasHungarianExtendedSegmentSeparator = false;\n  for (const auto& cp : cps) {\n    if (isApostrophe(cp.value)) {\n      hasApostropheLikeSeparator = true;\n    }\n    if (useHungarianExtended && isHungarianExtendedSegmentSeparator(cp.value)) {\n      hasHungarianExtendedSegmentSeparator = true;\n    }\n  }\n""",
)

replace_once(
    "lib/Epub/Epub/hyphenation/Hyphenator.cpp",
    "if (hasApostropheLikeSeparator || hasHungarianSlashSeparator) {",
    "if (hasApostropheLikeSeparator || hasHungarianExtendedSegmentSeparator) {",
)

# Keep the existing generic breakOffsetsForLanguage() semantics intact.  The
# dictionary gets a dedicated explicit-language entry point that temporarily
# enables Hungarian Extended and restores all reader-global hyphenation state.
replace_once(
    "lib/Epub/Epub/hyphenation/Hyphenator.h",
    """  static std::vector<BreakInfo> breakOffsetsForLanguage(const std::string& word, bool includeFallback,\n                                                        const std::string& language);\n""",
    """  static std::vector<BreakInfo> breakOffsetsForLanguage(const std::string& word, bool includeFallback,\n                                                        const std::string& language);\n  static std::vector<BreakInfo> breakOffsetsForLanguageExtended(const std::string& word, bool includeFallback,\n                                                                const std::string& language);\n""",
)

replace_once(
    "lib/Epub/Epub/hyphenation/Hyphenator.cpp",
    """std::vector<Hyphenator::BreakInfo> Hyphenator::breakOffsetsForLanguage(const std::string& word,\n                                                                       const bool includeFallback,\n                                                                       const std::string& language) {\n  const auto* previousHyphenator = cachedHyphenator_;\n  const bool previousHungarian = preferredLanguageIsHungarian_;\n  setPreferredLanguage(language);\n  auto breaks = breakOffsets(word, includeFallback);\n  cachedHyphenator_ = previousHyphenator;\n  preferredLanguageIsHungarian_ = previousHungarian;\n  return breaks;\n}\n""",
    """std::vector<Hyphenator::BreakInfo> Hyphenator::breakOffsetsForLanguage(const std::string& word,\n                                                                       const bool includeFallback,\n                                                                       const std::string& language) {\n  const auto* previousHyphenator = cachedHyphenator_;\n  const bool previousHungarian = preferredLanguageIsHungarian_;\n  setPreferredLanguage(language);\n  auto breaks = breakOffsets(word, includeFallback);\n  cachedHyphenator_ = previousHyphenator;\n  preferredLanguageIsHungarian_ = previousHungarian;\n  return breaks;\n}\n\nstd::vector<Hyphenator::BreakInfo> Hyphenator::breakOffsetsForLanguageExtended(const std::string& word,\n                                                                               const bool includeFallback,\n                                                                               const std::string& language) {\n  const auto* previousHyphenator = cachedHyphenator_;\n  const bool previousHungarian = preferredLanguageIsHungarian_;\n  const bool previousHungarianExtended = hungarianExtended_;\n  setPreferredLanguage(language);\n  if (preferredLanguageIsHungarian_) hungarianExtended_ = true;\n  auto breaks = breakOffsets(word, includeFallback);\n  cachedHyphenator_ = previousHyphenator;\n  preferredLanguageIsHungarian_ = previousHungarian;\n  hungarianExtended_ = previousHungarianExtended;\n  return breaks;\n}\n""",
)

replace_once(
    "src/activities/reader/DictionaryDefinitionActivity.cpp",
    "Hyphenator::breakOffsetsForLanguage(token, false, \"hu\")",
    "Hyphenator::breakOffsetsForLanguageExtended(token, false, \"hu\")",
)

# Add focused regressions to the existing Hungarian hyphenation test target.
test_path = Path("test/hyphenation_eval/HungarianSlashBreakTest.cpp")
test_text = test_path.read_text(encoding="utf-8")
marker = "TEST(HungarianQuotedSuffix, ExtendedPreservesLiangBreaksBeforeClosingQuoteSuffix) {"
if marker not in test_text:
    raise SystemExit("Test insertion marker not found")
new_tests = r'''TEST(HungarianParentheses, ExtendedRunsLiangInsideBothAlphabeticSegments) {
  Hyphenator::setPreferredLanguage("hu");
  Hyphenator::setHungarianExtended(true);

  const std::string left = "terület";
  const std::string right = "részterület";
  const auto leftBreaks = Hyphenator::breakOffsets(left, false);
  const auto rightBreaks = Hyphenator::breakOffsets(right, false);
  ASSERT_FALSE(leftBreaks.empty());
  ASSERT_FALSE(rightBreaks.empty());

  const std::string prefix = left + "(";
  const std::string combined = prefix + right + ")";
  const auto combinedBreaks = Hyphenator::breakOffsets(combined, false);

  for (const auto& info : leftBreaks) {
    ASSERT_NE(findBreak(combinedBreaks, info.byteOffset), nullptr)
        << "Parenthesis segmentation lost a break in the left segment";
  }
  for (const auto& info : rightBreaks) {
    ASSERT_NE(findBreak(combinedBreaks, prefix.size() + info.byteOffset), nullptr)
        << "Parenthesis segmentation lost a break in the right segment";
  }

  EXPECT_EQ(findBreak(combinedBreaks, left.size()), nullptr)
      << "Do not insert a break directly before '('";
  EXPECT_EQ(findBreak(combinedBreaks, prefix.size()), nullptr)
      << "Do not insert a break directly after '('";

  Hyphenator::setHungarianExtended(false);
}

TEST(HungarianParentheses, BasicDoesNotEnableParenthesisSegmentation) {
  Hyphenator::setPreferredLanguage("hu");
  Hyphenator::setHungarianExtended(false);

  const auto breaks = Hyphenator::breakOffsets("terület(részterület)", false);
  EXPECT_TRUE(breaks.empty()) << "Parenthesis segmentation must remain Hungarian-Extended-only";
}

TEST(HungarianDictionaryHyphenation, ExplicitHungarianEnablesDoubledMultigraphCorrection) {
  Hyphenator::setPreferredLanguage("en");
  Hyphenator::setHungarianExtended(false);

  for (const std::string& word : {std::string("összes"), std::string("mindösszesen")}) {
    const auto breaks = Hyphenator::breakOffsetsForLanguageExtended(word, false, "hu");
    const size_t split = word == "összes" ? std::string("ös").size() : std::string("mindös").size();
    const auto* info = findBreak(breaks, split);
    ASSERT_NE(info, nullptr) << "Missing doubled-sz correction for " << word;
    EXPECT_TRUE(info->requiresInsertedHyphen);
    EXPECT_EQ(info->replacement, Hyphenator::Replacement::AppendZ);
  }

  // The explicit dictionary call must restore the reader's current mode.
  const auto englishModeBreaks = Hyphenator::breakOffsets("összes", false);
  for (const auto& info : englishModeBreaks) {
    EXPECT_NE(info.replacement, Hyphenator::Replacement::AppendZ);
  }
}

TEST(HungarianDictionaryHyphenation, ExplicitHungarianAlsoSegmentsParentheses) {
  Hyphenator::setPreferredLanguage("en");
  Hyphenator::setHungarianExtended(false);

  const std::string left = "terület";
  const std::string right = "részterület";
  const auto rightBreaks = Hyphenator::breakOffsetsForLanguageExtended(right, false, "hu");
  ASSERT_FALSE(rightBreaks.empty());

  const std::string prefix = left + "(";
  const auto combinedBreaks = Hyphenator::breakOffsetsForLanguageExtended(prefix + right + ")", false, "hu");
  for (const auto& info : rightBreaks) {
    ASSERT_NE(findBreak(combinedBreaks, prefix.size() + info.byteOffset), nullptr);
  }
}

'''
test_path.write_text(test_text.replace(marker, new_tests + marker, 1), encoding="utf-8")

print("CPHUN-87 Hungarian hyphenation patch applied")
