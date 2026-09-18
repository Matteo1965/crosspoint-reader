from pathlib import Path
import re

def rep(path, old, new, label):
    p = Path(path)
    s = p.read_text(encoding="utf-8")
    n = s.count(old)
    if n != 1:
        raise SystemExit(f"CPHUN-137 {label}: expected 1 match, found {n}")
    p.write_text(s.replace(old, new, 1), encoding="utf-8")

# Settings: independent normalized pair-score cutoff, default 60.
rep("src/CrossPointSettings.h",
'''  // Final semantics: 0=off, 4=on (fixed validated 100% profile).
  // Legacy stored values 1..3 normalize to 4 on load.
  uint8_t letterSpacingOptimization = 0;''',
'''  // Final semantics: 0=off, 4=on (fixed validated 100% profile).
  // Legacy stored values 1..3 normalize to 4 on load.
  uint8_t letterSpacingOptimization = 0;
  // Bitter 12/14/16/18 normalized pair-score cutoff. 60 preserves the
  // historical Bitter 16 pt 655-pair behavior.
  uint8_t letterSpacingOptimizationThreshold = 60;''',
"settings field")

rep("src/CrossPointSettings.cpp",
'''  doc["letterSpacingOptimization"] = letterSpacingOptimization;
  doc["hyphenationThreshold"] = hyphenationThreshold;''',
'''  doc["letterSpacingOptimization"] = letterSpacingOptimization;
  doc["letterSpacingOptimizationThreshold"] = letterSpacingOptimizationThreshold;
  doc["hyphenationThreshold"] = hyphenationThreshold;''',
"save threshold")

rep("src/CrossPointSettings.cpp",
'''  letterSpacingOptimization =
      (doc["letterSpacingOptimization"] | (uint8_t)0) ? 4 : 0;
  minimumSpacePercent = doc["minimumSpacePercent"] | (uint8_t)100;''',
'''  letterSpacingOptimization =
      (doc["letterSpacingOptimization"] | (uint8_t)0) ? 4 : 0;
  letterSpacingOptimizationThreshold =
      doc["letterSpacingOptimizationThreshold"] | (uint8_t)60;
  if (letterSpacingOptimizationThreshold < 50 || letterSpacingOptimizationThreshold > 75 ||
      letterSpacingOptimizationThreshold % 5 != 0) {
    letterSpacingOptimizationThreshold = 60;
    needsResave = true;
  }
  minimumSpacePercent = doc["minimumSpacePercent"] | (uint8_t)100;''',
"load threshold")

rep("src/CrossPointSettings.cpp",
'''  const uint8_t bitter16OptimizationProfile =
      letterSpacingLimitPercent > 0 && (isBitterExperimentalSize || isNotoSerif16)
          ? std::min<uint8_t>(letterSpacingOptimization, 4)
          : 0;
  // Bits 13..15 carry the 0..4 optimizer profile to ParsedText; thresholds
  // remain below 0x2000 and therefore keep their original numeric meaning.
  spec.letterSpacingLimitPercent = static_cast<uint16_t>(
      (letterSpacingLimitPercent & 0x1FFFu) |
      (static_cast<uint16_t>(bitter16OptimizationProfile) << 13));''',
'''  const uint8_t optimizationThresholdCode =
      letterSpacingLimitPercent > 0 && letterSpacingOptimization &&
              (isBitterExperimentalSize || isNotoSerif16)
          ? static_cast<uint8_t>((letterSpacingOptimizationThreshold - 45u) / 5u)
          : 0;
  // Bits 13..15 carry 0=off or threshold code 1..6 (50..75) to ParsedText.
  // Noto Serif 16 keeps its dedicated fixed pair table; the score cutoff applies to Bitter.
  spec.letterSpacingLimitPercent = static_cast<uint16_t>(
      (letterSpacingLimitPercent & 0x1FFFu) |
      (static_cast<uint16_t>(optimizationThresholdCode) << 13));''',
"encode threshold")

# UI row.
rep("src/activities/settings/TextSettingsActivity.h",
'''    LetterSpacingCorrection,
    LetterSpacingOptimization,
    ScreenMargin,''',
'''    LetterSpacingCorrection,
    LetterSpacingOptimization,
    LetterSpacingOptimizationThreshold,
    ScreenMargin,''',
"layout enum")

rep("src/activities/settings/TextSettingsActivity.cpp",
'''        } else if (i == static_cast<int>(LayoutRow::LetterSpacingOptimization)) {
          item.label = I18N.getLanguage() == Language::HU ? "Betűköz optimalizálás" : "Letter spacing optimization";
        } else if (i == static_cast<int>(LayoutRow::ScreenMargin)) {''',
'''        } else if (i == static_cast<int>(LayoutRow::LetterSpacingOptimization)) {
          item.label = I18N.getLanguage() == Language::HU ? "Betűköz optimalizálás" : "Letter spacing optimization";
        } else if (i == static_cast<int>(LayoutRow::LetterSpacingOptimizationThreshold)) {
          item.label = I18N.getLanguage() == Language::HU ? "Optimalizációs küszöb" : "Optimization threshold";
        } else if (i == static_cast<int>(LayoutRow::ScreenMargin)) {''',
"row label")

rep("src/activities/settings/TextSettingsActivity.cpp",
'''    case LayoutRow::LetterSpacingOptimization:
      if (SETTINGS.letterSpacingLimitPercent == 0) {
        requestUpdate();
        break;
      }
      SETTINGS.letterSpacingOptimization = SETTINGS.letterSpacingOptimization ? 0 : 4;
      SETTINGS.saveToFile();
      requestUpdate();
      break;
    case LayoutRow::ShortHyphen:''',
'''    case LayoutRow::LetterSpacingOptimization:
      if (SETTINGS.letterSpacingLimitPercent == 0) {
        requestUpdate();
        break;
      }
      SETTINGS.letterSpacingOptimization = SETTINGS.letterSpacingOptimization ? 0 : 4;
      SETTINGS.saveToFile();
      requestUpdate();
      break;
    case LayoutRow::LetterSpacingOptimizationThreshold: {
      const char* options[] = {"50", "55", "60", "65", "70", "75"};
      const int cur = std::clamp<int>((SETTINGS.letterSpacingOptimizationThreshold - 50) / 5, 0, 5);
      optionPopup_.show(
          I18N.getLanguage() == Language::HU ? "Optimalizációs küszöb" : "Optimization threshold",
          options, 6, cur, [](int idx) {
            SETTINGS.letterSpacingOptimizationThreshold =
                static_cast<uint8_t>(50 + std::clamp(idx, 0, 5) * 5);
            SETTINGS.saveToFile();
          });
      requestUpdate();
      break;
    }
    case LayoutRow::ShortHyphen:''',
"threshold picker")

rep("src/activities/settings/TextSettingsActivity.cpp",
'''    case LayoutRow::LetterSpacingOptimization:
      return SETTINGS.letterSpacingOptimization ? tr(STR_STATE_ON) : tr(STR_STATE_OFF);
    case LayoutRow::ScreenMargin:''',
'''    case LayoutRow::LetterSpacingOptimization:
      return SETTINGS.letterSpacingOptimization ? tr(STR_STATE_ON) : tr(STR_STATE_OFF);
    case LayoutRow::LetterSpacingOptimizationThreshold:
      return std::to_string(SETTINGS.letterSpacingOptimizationThreshold);
    case LayoutRow::ScreenMargin:''',
"threshold display")

# ParsedText high bits now carry a threshold code, not the retired profile.
rep("lib/Epub/Epub/ParsedText.h",
"  uint8_t letterSpacingOptimizationProfile;\n",
"  uint8_t letterSpacingOptimizationThresholdCode;\n",
"ParsedText member")
rep("lib/Epub/Epub/ParsedText.h",
'''        letterSpacingOptimizationProfile(
            static_cast<uint8_t>((letterSpacingLimitPercent >> 13) & 0x07u)),''',
'''        letterSpacingOptimizationThresholdCode(
            static_cast<uint8_t>((letterSpacingLimitPercent >> 13) & 0x07u)),''',
"ParsedText decode")

# Score table replaces the historical 655-entry Bitter list.
p = Path("lib/Epub/Epub/LetterSpacingOptimization.h")
s = p.read_text(encoding="utf-8")
s = s.replace('#include <Utf8.h>\n', '#include <Utf8.h>\n#include <algorithm>\n#include "BitterSpacingScores.h"\n', 1)
s, n = re.subn(
    r'constexpr uint32_t OPTIMIZABLE_PAIRS\[\] = \{[\s\S]*?static_assert\(sizeof\(OPTIMIZABLE_PAIRS\) / sizeof\(OPTIMIZABLE_PAIRS\[0\]\) == 655,\n\s*"Optimizable pair table must contain 655 entries"\);\n',
    '', s, count=1)
if n != 1:
    raise SystemExit(f"CPHUN-137 remove old Bitter table: matches={n}")

old = '''constexpr uint8_t PACKED_FLAG = 0x80u;
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
'''
new = '''constexpr uint8_t PACKED_THRESHOLD_SHIFT = 5;
constexpr uint8_t PACKED_THRESHOLD_MASK = 0xE0u;
constexpr uint8_t PACKED_BUDGET_MASK = 0x1Fu;
constexpr uint8_t FIXED_PROFILE_LEVEL = 4;

inline uint8_t clampProfile(const uint8_t level) {
  return level > 4 ? 4 : level;
}

inline const Profile& profile(const uint8_t level) {
  return PROFILES[clampProfile(level)];
}

inline uint8_t thresholdFromCode(const uint8_t code) {
  return code >= 1 && code <= 6 ? static_cast<uint8_t>(45u + code * 5u) : 60u;
}

inline uint8_t packConfig(const uint8_t thresholdCode, const uint8_t budgetPx) {
  if (thresholdCode < 1 || thresholdCode > 6 || budgetPx == 0) return 0;
  return static_cast<uint8_t>((thresholdCode << PACKED_THRESHOLD_SHIFT) |
                              std::min<uint8_t>(budgetPx, PACKED_BUDGET_MASK));
}

inline bool isPackedConfig(const uint8_t value) {
  const uint8_t code = static_cast<uint8_t>((value & PACKED_THRESHOLD_MASK) >> PACKED_THRESHOLD_SHIFT);
  return code >= 1 && code <= 6;
}

inline uint8_t unpackThresholdCode(const uint8_t value) {
  return isPackedConfig(value)
             ? static_cast<uint8_t>((value & PACKED_THRESHOLD_MASK) >> PACKED_THRESHOLD_SHIFT)
             : 0;
}

inline uint8_t unpackBudget(const uint8_t value) {
  return isPackedConfig(value) ? static_cast<uint8_t>(value & PACKED_BUDGET_MASK) : 0;
}
'''
if s.count(old) != 1:
    raise SystemExit(f"CPHUN-137 packed config matches={s.count(old)}")
s = s.replace(old, new, 1)

old = '''struct Accumulator {
  uint8_t profileLevel = 0;
  uint8_t fp4 = 0;
  uint8_t usedPx = 0;
  uint8_t usedWordPx = 0;
  uint8_t budgetPx = 0;
  PairTable pairTable = PairTable::Bitter16;

  Accumulator() = default;
  Accumulator(const uint8_t level, const uint8_t budget,
              const PairTable table = PairTable::Bitter16)
      : profileLevel(clampProfile(level)),
        budgetPx(std::min<uint8_t>(budget, profile(level).maxPxPerLine)),
        pairTable(table) {}
};

inline bool isOptimizablePair(const uint32_t left, const uint32_t right,
                              const PairTable table) {
  if (left > 0xFFFFu || right > 0xFFFFu) return false;
  const uint32_t key = (left << 16) | right;
  const uint32_t* pairs = table == PairTable::NotoSerif16
                              ? NOTOSERIF_16_OPTIMIZABLE_PAIRS
                              : OPTIMIZABLE_PAIRS;
  const size_t count = table == PairTable::NotoSerif16
                           ? sizeof(NOTOSERIF_16_OPTIMIZABLE_PAIRS) /
                                 sizeof(NOTOSERIF_16_OPTIMIZABLE_PAIRS[0])
                           : sizeof(OPTIMIZABLE_PAIRS) / sizeof(OPTIMIZABLE_PAIRS[0]);
  size_t lo = 0;
  size_t hi = count;
  while (lo < hi) {
    const size_t mid = lo + (hi - lo) / 2;
    if (pairs[mid] < key)
      lo = mid + 1;
    else
      hi = mid;
  }
  return lo < count && pairs[lo] == key;
}
'''
new = '''inline uint8_t pointSizeForFont(const EpdFontFamily& font, const PairTable table) {
  if (table == PairTable::NotoSerif16) return 16;
  const EpdFontData* data = font.getData(EpdFontFamily::REGULAR);
  if (!data) return 16;
  switch (data->advanceY) {
    case 30: return 12;
    case 35: return 14;
    case 40: return 16;
    case 45: return 18;
    default: return 16;
  }
}

struct Accumulator {
  uint8_t profileLevel = 0;
  uint8_t fp4 = 0;
  uint8_t usedPx = 0;
  uint8_t usedWordPx = 0;
  uint8_t budgetPx = 0;
  uint8_t threshold = 60;
  uint8_t pointSize = 16;
  PairTable pairTable = PairTable::Bitter16;

  Accumulator() = default;
  Accumulator(const uint8_t thresholdCode, const uint8_t budget,
              const PairTable table = PairTable::Bitter16,
              const uint8_t size = 16)
      : profileLevel(thresholdCode ? FIXED_PROFILE_LEVEL : 0),
        budgetPx(std::min<uint8_t>(budget, profile(FIXED_PROFILE_LEVEL).maxPxPerLine)),
        threshold(thresholdFromCode(thresholdCode)),
        pointSize(size),
        pairTable(table) {}
};

inline bool isOptimizablePair(const uint32_t left, const uint32_t right,
                              const PairTable table, const uint8_t pointSize,
                              const uint8_t threshold) {
  if (left > 0xFFFFu || right > 0xFFFFu) return false;
  if (table == PairTable::Bitter16) {
    return BitterSpacingScores::scoreForPair(left, right, pointSize) >= threshold;
  }
  const uint32_t key = (left << 16) | right;
  const size_t count = sizeof(NOTOSERIF_16_OPTIMIZABLE_PAIRS) /
                       sizeof(NOTOSERIF_16_OPTIMIZABLE_PAIRS[0]);
  size_t lo = 0;
  size_t hi = count;
  while (lo < hi) {
    const size_t mid = lo + (hi - lo) / 2;
    if (NOTOSERIF_16_OPTIMIZABLE_PAIRS[mid] < key)
      lo = mid + 1;
    else
      hi = mid;
  }
  return lo < count && NOTOSERIF_16_OPTIMIZABLE_PAIRS[lo] == key;
}
'''
if s.count(old) != 1:
    raise SystemExit(f"CPHUN-137 accumulator/pairs matches={s.count(old)}")
s = s.replace(old, new, 1)
s = s.replace('!isOptimizablePair(left, right, acc.pairTable)) {',
              '!isOptimizablePair(left, right, acc.pairTable, acc.pointSize, acc.threshold)) {', 1)
p.write_text(s, encoding="utf-8")

# Layout path.
p = Path("lib/Epub/Epub/ParsedText.cpp")
s = p.read_text(encoding="utf-8")
old = '''        if (letterSpacingOptimizationProfile > 0 && spareSpace > 1) {
          const auto& optProfile =
              LetterSpacingOptimization::profile(letterSpacingOptimizationProfile);
          const uint8_t availableBudget = static_cast<uint8_t>(
              std::min<int>(optProfile.maxPxPerLine, spareSpace - 1));
          LetterSpacingOptimization::Accumulator optAcc(
              letterSpacingOptimizationProfile, availableBudget,
              LetterSpacingOptimization::tableForFontId(fontId));
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
new = '''        if (letterSpacingOptimizationThresholdCode > 0 && spareSpace > 1) {
          const auto& optProfile =
              LetterSpacingOptimization::profile(LetterSpacingOptimization::FIXED_PROFILE_LEVEL);
          const uint8_t availableBudget = static_cast<uint8_t>(
              std::min<int>(optProfile.maxPxPerLine, spareSpace - 1));
          const auto pairTable = LetterSpacingOptimization::tableForFontId(fontId);
          const auto fontIt = renderer.getFontMap().find(fontId);
          const uint8_t pointSize = fontIt == renderer.getFontMap().end()
                                        ? 16
                                        : LetterSpacingOptimization::pointSizeForFont(
                                              fontIt->second, pairTable);
          LetterSpacingOptimization::Accumulator optAcc(
              letterSpacingOptimizationThresholdCode, availableBudget, pairTable, pointSize);
          for (size_t i = 0; i < lineWords.size(); ++i) {
            trackingExtraTotal += LetterSpacingOptimization::consumeWord(
                lineWords[i].c_str(), lineWordStyles[i], optAcc);
          }
          if (trackingExtraTotal > 0) {
            letterSpacingPx = LetterSpacingOptimization::packConfig(
                letterSpacingOptimizationThresholdCode,
                static_cast<uint8_t>(trackingExtraTotal));
          }
        } else {'''
if s.count(old) != 1:
    raise SystemExit(f"CPHUN-137 layout block matches={s.count(old)}")
s = s.replace(old, new, 1)

old = '''      LetterSpacingOptimization::Accumulator optPositionAcc(
          LetterSpacingOptimization::unpackProfile(letterSpacingPx),
          LetterSpacingOptimization::unpackBudget(letterSpacingPx),
          LetterSpacingOptimization::tableForFontId(fontId));'''
new = '''      const auto positionPairTable = LetterSpacingOptimization::tableForFontId(fontId);
      const auto positionFontIt = renderer.getFontMap().find(fontId);
      const uint8_t positionPointSize = positionFontIt == renderer.getFontMap().end()
                                            ? 16
                                            : LetterSpacingOptimization::pointSizeForFont(
                                                  positionFontIt->second, positionPairTable);
      LetterSpacingOptimization::Accumulator optPositionAcc(
          LetterSpacingOptimization::unpackThresholdCode(letterSpacingPx),
          LetterSpacingOptimization::unpackBudget(letterSpacingPx),
          positionPairTable, positionPointSize);'''
if s.count(old) != 1:
    raise SystemExit(f"CPHUN-137 position accumulator matches={s.count(old)}")
p.write_text(s.replace(old, new, 1), encoding="utf-8")

# Render path.
p = Path("lib/Epub/Epub/blocks/TextBlock.cpp")
s = p.read_text(encoding="utf-8")
old = '''    LetterSpacingOptimization::Accumulator optimizationAcc(
        LetterSpacingOptimization::unpackProfile(letterSpacingPx),
        LetterSpacingOptimization::unpackBudget(letterSpacingPx),
        LetterSpacingOptimization::tableForFontId(fontId));'''
new = '''    const auto pairTable = LetterSpacingOptimization::tableForFontId(fontId);
    const auto optimizationFontIt = renderer.getFontMap().find(fontId);
    const uint8_t optimizationPointSize = optimizationFontIt == renderer.getFontMap().end()
                                              ? 16
                                              : LetterSpacingOptimization::pointSizeForFont(
                                                    optimizationFontIt->second, pairTable);
    LetterSpacingOptimization::Accumulator optimizationAcc(
        LetterSpacingOptimization::unpackThresholdCode(letterSpacingPx),
        LetterSpacingOptimization::unpackBudget(letterSpacingPx),
        pairTable, optimizationPointSize);'''
if s.count(old) != 1:
    raise SystemExit(f"CPHUN-137 simple render accumulator matches={s.count(old)}")
s = s.replace(old, new, 1)

old = '''  LetterSpacingOptimization::Accumulator optimizationAcc(
      LetterSpacingOptimization::unpackProfile(letterSpacingPx),
      LetterSpacingOptimization::unpackBudget(letterSpacingPx),
      LetterSpacingOptimization::tableForFontId(fontId));'''
new = '''  const auto pairTable = LetterSpacingOptimization::tableForFontId(fontId);
  const auto optimizationFontIt = renderer.getFontMap().find(fontId);
  const uint8_t optimizationPointSize = optimizationFontIt == renderer.getFontMap().end()
                                            ? 16
                                            : LetterSpacingOptimization::pointSizeForFont(
                                                  optimizationFontIt->second, pairTable);
  LetterSpacingOptimization::Accumulator optimizationAcc(
      LetterSpacingOptimization::unpackThresholdCode(letterSpacingPx),
      LetterSpacingOptimization::unpackBudget(letterSpacingPx),
      pairTable, optimizationPointSize);'''
if s.count(old) != 1:
    raise SystemExit(f"CPHUN-137 complex render accumulator matches={s.count(old)}")
p.write_text(s.replace(old, new, 1), encoding="utf-8")

print("CPHUN-137 applied: Bitter 12/14/16/18 normalized score threshold 50..75, default 60")
