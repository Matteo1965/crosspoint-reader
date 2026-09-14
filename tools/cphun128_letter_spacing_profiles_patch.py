from pathlib import Path


def replace_once(path, old, new):
    path = Path(path)
    text = path.read_text(encoding="utf-8")
    count = text.count(old)
    if count != 1:
        raise SystemExit(
            f"CPHUN-128: {path}: expected one match, found {count}: {old[:100]!r}"
        )
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


# Persist a five-state profile instead of coercing the old field to boolean.
replace_once(
    "src/CrossPointSettings.cpp",
    '  letterSpacingOptimization = (doc["letterSpacingOptimization"] | (uint8_t)0) ? 1 : 0;',
    '''  letterSpacingOptimization =
      std::min<uint8_t>(doc["letterSpacingOptimization"] | (uint8_t)0, 4);''',
)

replace_once(
    "src/CrossPointSettings.cpp",
    '''  const bool bitter16Optimization = letterSpacingOptimization && letterSpacingLimitPercent > 0 &&
                                    fontPointSize == 16 && strcmp(sdFontFamilyName, "Bitter") == 0;
  spec.letterSpacingLimitPercent =
      static_cast<uint16_t>(letterSpacingLimitPercent | (bitter16Optimization ? 0x8000u : 0u));''',
    '''  const uint8_t bitter16OptimizationProfile =
      letterSpacingLimitPercent > 0 && fontPointSize == 16 && strcmp(sdFontFamilyName, "Bitter") == 0
          ? std::min<uint8_t>(letterSpacingOptimization, 4)
          : 0;
  // Bits 13..15 carry the 0..4 optimizer profile to ParsedText; thresholds
  // remain below 0x2000 and therefore keep their original numeric meaning.
  spec.letterSpacingLimitPercent = static_cast<uint16_t>(
      (letterSpacingLimitPercent & 0x1FFFu) |
      (static_cast<uint16_t>(bitter16OptimizationProfile) << 13));''',
)

replace_once(
    "src/CrossPointSettings.h",
    "  uint8_t letterSpacingOptimization = 0;",
    '''  // 0=off, 1=25%, 2=50%, 3=75%, 4=100% (Bitter 16 pt pilot).
  uint8_t letterSpacingOptimization = 0;''',
)

# Replace the toggle with a five-choice picker and matching display labels.
replace_once(
    "src/activities/settings/TextSettingsActivity.cpp",
    '''    case LayoutRow::LetterSpacingOptimization:
      if (SETTINGS.letterSpacingLimitPercent == 0) {
        requestUpdate();
        break;
      }
      SETTINGS.letterSpacingOptimization = !SETTINGS.letterSpacingOptimization;
      SETTINGS.saveToFile();
      requestUpdate();
      break;''',
    '''    case LayoutRow::LetterSpacingOptimization: {
      if (SETTINGS.letterSpacingLimitPercent == 0) {
        requestUpdate();
        break;
      }
      const char* options[] = {tr(STR_STATE_OFF), "25%", "50%", "75%", "100%"};
      const int cur = std::clamp<int>(SETTINGS.letterSpacingOptimization, 0, 4);
      optionPopup_.show(
          I18N.getLanguage() == Language::HU ? "Betűköz optimalizálás" : "Letter spacing optimization",
          options, 5, cur, [](int idx) {
            SETTINGS.letterSpacingOptimization = static_cast<uint8_t>(std::clamp(idx, 0, 4));
            SETTINGS.saveToFile();
          });
      requestUpdate();
      break;
    }''',
)

replace_once(
    "src/activities/settings/TextSettingsActivity.cpp",
    '''    case LayoutRow::LetterSpacingOptimization:
      return SETTINGS.letterSpacingOptimization ? tr(STR_STATE_ON) : tr(STR_STATE_OFF);''',
    '''    case LayoutRow::LetterSpacingOptimization: {
      constexpr const char* labels[] = {"", "25%", "50%", "75%", "100%"};
      const uint8_t profile = std::min<uint8_t>(SETTINGS.letterSpacingOptimization, 4);
      return profile == 0 ? tr(STR_STATE_OFF) : labels[profile];
    }''',
)

# Carry the complete profile through the existing compact ReaderConfig field.
replace_once(
    "lib/Epub/Epub/ParsedText.h",
    "  bool letterSpacingOptimization;",
    "  uint8_t letterSpacingOptimizationProfile;",
)

replace_once(
    "lib/Epub/Epub/ParsedText.h",
    '''        letterSpacingLimitPercent(static_cast<uint16_t>(letterSpacingLimitPercent & 0x7FFFu)),
        letterSpacingOptimization((letterSpacingLimitPercent & 0x8000u) != 0),''',
    '''        letterSpacingLimitPercent(static_cast<uint16_t>(letterSpacingLimitPercent & 0x1FFFu)),
        letterSpacingOptimizationProfile(
            static_cast<uint8_t>((letterSpacingLimitPercent >> 13) & 0x07u)),''',
)

# Replace the fixed 0.5 px / 8 px engine with the agreed four profiles.
header_path = Path("lib/Epub/Epub/LetterSpacingOptimization.h")
header = header_path.read_text(encoding="utf-8")
start = header.index("constexpr uint8_t STEP_FP4 = 8;")
end_marker = "}  // namespace LetterSpacingOptimization"
end = header.index(end_marker, start)
new_engine = r'''constexpr uint8_t ONE_PX_FP4 = 16;

struct Profile {
  uint8_t stepFp4;
  uint8_t maxPxPerWord;
  uint8_t maxPxPerLine;
};

constexpr Profile PROFILES[] = {
    {0, 0, 0},    // Off
    {4, 2, 6},    // 25%: 0.25 px/pair
    {8, 3, 9},    // 50%: 0.50 px/pair
    {12, 4, 12},  // 75%: 0.75 px/pair
    {16, 6, 18},  // 100%: 1.00 px/pair
};

constexpr uint8_t PACKED_FLAG = 0x80u;
constexpr uint8_t PACKED_PROFILE_SHIFT = 5;
constexpr uint8_t PACKED_PROFILE_MASK = 0x60u;
constexpr uint8_t PACKED_BUDGET_MASK = 0x1Fu;

inline uint8_t clampProfile(const uint8_t level) {
  return level > 4 ? 4 : level;
}

inline const Profile& profile(const uint8_t level) {
  return PROFILES[clampProfile(level)];
}

inline uint8_t packConfig(const uint8_t level, const uint8_t budgetPx) {
  if (level == 0 || budgetPx == 0) return 0;
  const uint8_t encodedLevel = static_cast<uint8_t>((clampProfile(level) - 1u) << PACKED_PROFILE_SHIFT);
  return static_cast<uint8_t>(PACKED_FLAG | encodedLevel |
                              (std::min<uint8_t>(budgetPx, PACKED_BUDGET_MASK)));
}

inline bool isPackedConfig(const uint8_t value) {
  return (value & PACKED_FLAG) != 0;
}

inline uint8_t unpackProfile(const uint8_t value) {
  return isPackedConfig(value)
             ? static_cast<uint8_t>(((value & PACKED_PROFILE_MASK) >> PACKED_PROFILE_SHIFT) + 1u)
             : 0;
}

inline uint8_t unpackBudget(const uint8_t value) {
  return isPackedConfig(value) ? static_cast<uint8_t>(value & PACKED_BUDGET_MASK) : 0;
}

struct Accumulator {
  uint8_t profileLevel = 0;
  uint8_t fp4 = 0;
  uint8_t usedPx = 0;
  uint8_t usedWordPx = 0;
  uint8_t budgetPx = 0;

  Accumulator() = default;
  Accumulator(const uint8_t level, const uint8_t budget)
      : profileLevel(clampProfile(level)),
        budgetPx(std::min<uint8_t>(budget, profile(level).maxPxPerLine)) {}
};

inline bool isOptimizablePair(uint32_t left, uint32_t right) {
  if (left > 0xFFFFu || right > 0xFFFFu) return false;
  const uint32_t key = (left << 16) | right;
  size_t lo = 0, hi = sizeof(OPTIMIZABLE_PAIRS) / sizeof(OPTIMIZABLE_PAIRS[0]);
  while (lo < hi) {
    const size_t mid = lo + (hi - lo) / 2;
    if (OPTIMIZABLE_PAIRS[mid] < key) lo = mid + 1; else hi = mid;
  }
  return lo < sizeof(OPTIMIZABLE_PAIRS) / sizeof(OPTIMIZABLE_PAIRS[0]) &&
         OPTIMIZABLE_PAIRS[lo] == key;
}

inline bool isLatinLetter(const uint32_t cp) {
  return (cp >= 'A' && cp <= 'Z') || (cp >= 'a' && cp <= 'z') ||
         (cp >= 0x00C0u && cp <= 0x024Fu);
}

inline uint8_t wordLetterCount(const char* text) {
  if (!text) return 0;
  const auto* cursor = reinterpret_cast<const uint8_t*>(text);
  uint8_t count = 0;
  while (*cursor) {
    const uint32_t cp = utf8NextCodepoint(&cursor);
    if (!cp) break;
    if (isLatinLetter(cp) && count < UINT8_MAX) ++count;
  }
  return count;
}

inline bool beginWord(const char* text, const EpdFontFamily::Style style, Accumulator& acc) {
  acc.usedWordPx = 0;
  // Exactly three letters are excluded. Two-letter words remain eligible, and
  // punctuation plus the synthetic hyphen do not contribute to this count.
  return text && *text && style == EpdFontFamily::REGULAR &&
         wordLetterCount(text) != 3 && acc.profileLevel != 0 &&
         acc.usedPx < acc.budgetPx;
}

inline uint8_t consumePair(const uint32_t left, const uint32_t right,
                           const EpdFontFamily::Style style, Accumulator& acc) {
  const Profile& limits = profile(acc.profileLevel);
  if (style != EpdFontFamily::REGULAR || acc.profileLevel == 0 ||
      acc.usedPx >= acc.budgetPx || acc.usedWordPx >= limits.maxPxPerWord ||
      !isOptimizablePair(left, right)) {
    return 0;
  }
  acc.fp4 = static_cast<uint8_t>(acc.fp4 + limits.stepFp4);
  if (acc.fp4 < ONE_PX_FP4) return 0;
  acc.fp4 = static_cast<uint8_t>(acc.fp4 - ONE_PX_FP4);
  ++acc.usedPx;
  ++acc.usedWordPx;
  return 1;
}

inline uint8_t consumeWord(const char* text, const EpdFontFamily::Style style,
                           Accumulator& acc) {
  if (!beginWord(text, style, acc)) return 0;
  const auto* cursor = reinterpret_cast<const uint8_t*>(text);
  uint32_t prev = 0;
  uint8_t extra = 0;
  while (*cursor) {
    const uint32_t cp = utf8NextCodepoint(&cursor);
    if (!cp) break;
    if (prev) extra = static_cast<uint8_t>(extra + consumePair(prev, cp, style, acc));
    prev = cp;
  }
  return extra;
}
'''
header = header[:start] + new_engine + end_marker + header[end + len(end_marker):]
header_path.write_text(header, encoding="utf-8")

# Measure only up to min(profile line cap, spareSpace - 1), then pack the exact
# emitted budget into the TextBlock byte so positioning and rendering reproduce
# the same pixels and higher profiles never disable an otherwise usable line.
parsed_path = Path("lib/Epub/Epub/ParsedText.cpp")
parsed = parsed_path.read_text(encoding="utf-8")
old_measure = '''        if (letterSpacingOptimization) {
          LetterSpacingOptimization::Accumulator optAcc;
          for (size_t i = 0; i < lineWords.size(); ++i) {
            trackingExtraTotal += LetterSpacingOptimization::consumeWord(lineWords[i].c_str(), lineWordStyles[i], optAcc);
          }
          if (trackingExtraTotal > 0 && trackingExtraTotal < spareSpace) letterSpacingPx = 2;
        } else {'''
new_measure = '''        if (letterSpacingOptimizationProfile > 0 && spareSpace > 1) {
          const auto& optProfile =
              LetterSpacingOptimization::profile(letterSpacingOptimizationProfile);
          const uint8_t availableBudget = static_cast<uint8_t>(
              std::min<int>(optProfile.maxPxPerLine, spareSpace - 1));
          LetterSpacingOptimization::Accumulator optAcc(
              letterSpacingOptimizationProfile, availableBudget);
          for (size_t i = 0; i < lineWords.size(); ++i) {
            trackingExtraTotal += LetterSpacingOptimization::consumeWord(
                lineWords[i].c_str(), lineWordStyles[i], optAcc);
          }
          if (trackingExtraTotal > 0) {
            letterSpacingPx = LetterSpacingOptimization::packConfig(
                letterSpacingOptimizationProfile,
                static_cast<uint8_t>(trackingExtraTotal));
          }
        } else {'''
if parsed.count(old_measure) != 1:
    raise SystemExit(f"CPHUN-128: measurement block matches={parsed.count(old_measure)}")
parsed = parsed.replace(old_measure, new_measure, 1)

replace_decl = "      LetterSpacingOptimization::Accumulator optPositionAcc;"
new_decl = '''      LetterSpacingOptimization::Accumulator optPositionAcc(
          LetterSpacingOptimization::unpackProfile(letterSpacingPx),
          LetterSpacingOptimization::unpackBudget(letterSpacingPx));'''
if parsed.count(replace_decl) != 1:
    raise SystemExit(f"CPHUN-128: position accumulator matches={parsed.count(replace_decl)}")
parsed = parsed.replace(replace_decl, new_decl, 1)

old_word_extra = '''        const int wordTrackingExtra = letterSpacingPx == 2
            ? LetterSpacingOptimization::consumeWord(lineWords[wordIdx].c_str(), lineWordStyles[wordIdx], optPositionAcc)
            : (letterSpacingPx ? static_cast<int>(std::max<uint32_t>(1, countCodepoints(lineWords[wordIdx])) - 1) * letterSpacingPx : 0);'''
new_word_extra = '''        const int wordTrackingExtra =
            LetterSpacingOptimization::isPackedConfig(letterSpacingPx)
                ? LetterSpacingOptimization::consumeWord(
                      lineWords[wordIdx].c_str(), lineWordStyles[wordIdx], optPositionAcc)
                : (letterSpacingPx
                       ? static_cast<int>(
                             std::max<uint32_t>(1, countCodepoints(lineWords[wordIdx])) - 1) *
                             letterSpacingPx
                       : 0);'''
if parsed.count(old_word_extra) != 1:
    raise SystemExit(f"CPHUN-128: word extra block matches={parsed.count(old_word_extra)}")
parsed = parsed.replace(old_word_extra, new_word_extra, 1)
parsed_path.write_text(parsed, encoding="utf-8")

# Decode the packed profile/budget in both TextBlock render paths. beginWord()
# resets the per-word counter and rejects exactly-three-letter words before any
# pair can affect the shared line accumulator or its fractional remainder.
textblock_path = Path("lib/Epub/Epub/blocks/TextBlock.cpp")
textblock = textblock_path.read_text(encoding="utf-8")

old_opt_start = '''  if (letterSpacingPx == 2 && optimizationAcc) {
    const auto fontIt = renderer.getFontMap().find(fontId);'''
new_opt_start = '''  const bool packedOptimization =
      LetterSpacingOptimization::isPackedConfig(letterSpacingPx);
  const bool optimizeThisWord =
      packedOptimization && optimizationAcc &&
      LetterSpacingOptimization::beginWord(text, style, *optimizationAcc);

  if (packedOptimization && !optimizeThisWord) {
    if (!adjustTrailingHyphen) {
      renderer.drawText(fontId, x, y, text, true, style, baseDir);
      return;
    }
    const size_t len = strlen(text);
    const std::string prefix(text, len - SHORT_HYPHEN_BYTES);
    if (!prefix.empty()) renderer.drawText(fontId, x, y, prefix.c_str(), true, style, baseDir);
    const int fullAdvance = renderer.getTextAdvanceX(fontId, text, style);
    const int hyphenAdvance = renderer.getTextAdvanceX(fontId, SHORT_HYPHEN_UTF8, style);
    const int hyphenPenX = x + fullAdvance - hyphenAdvance;
    renderer.drawText(fontId, hyphenPenX + trailingShortHyphenInkShift(renderer, fontId, style), y,
                      SHORT_HYPHEN_UTF8, true, style, baseDir);
    return;
  }

  if (optimizeThisWord) {
    const auto fontIt = renderer.getFontMap().find(fontId);'''
if textblock.count(old_opt_start) != 1:
    raise SystemExit(f"CPHUN-128: render optimizer start matches={textblock.count(old_opt_start)}")
textblock = textblock.replace(old_opt_start, new_opt_start, 1)

old_acc = "    LetterSpacingOptimization::Accumulator optimizationAcc;"
new_acc = '''    LetterSpacingOptimization::Accumulator optimizationAcc(
        LetterSpacingOptimization::unpackProfile(letterSpacingPx),
        LetterSpacingOptimization::unpackBudget(letterSpacingPx));'''
if textblock.count(old_acc) != 1:
    raise SystemExit(f"CPHUN-128: simple render accumulator matches={textblock.count(old_acc)}")
textblock = textblock.replace(old_acc, new_acc, 1)

old_acc2 = "  LetterSpacingOptimization::Accumulator optimizationAcc;"
new_acc2 = '''  LetterSpacingOptimization::Accumulator optimizationAcc(
      LetterSpacingOptimization::unpackProfile(letterSpacingPx),
      LetterSpacingOptimization::unpackBudget(letterSpacingPx));'''
if textblock.count(old_acc2) != 1:
    raise SystemExit(f"CPHUN-128: complex render accumulator matches={textblock.count(old_acc2)}")
textblock = textblock.replace(old_acc2, new_acc2, 1)
textblock_path.write_text(textblock, encoding="utf-8")

build_id_path = Path("src/CPHUNBuildId.h")
build_id = build_id_path.read_text(encoding="utf-8")
old_id = '#define CPHUN_BUILD_ID "CPHUN-260914-127"'
new_id = '#define CPHUN_BUILD_ID "CPHUN-260914-128-EXP"'
if build_id.count(old_id) != 1:
    raise SystemExit(f"CPHUN-128: build-id anchor matches={build_id.count(old_id)}")
build_id_path.write_text(build_id.replace(old_id, new_id, 1), encoding="utf-8")
