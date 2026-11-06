#pragma once
#include <EpdFontFamily.h>
#include <Utf8.h>
#include <algorithm>
#include "BitterSpacingScores.h"
#include "OpticalLineCorrection.h"
#include <cstddef>
#include <cstdint>
namespace LetterSpacingOptimization {
constexpr uint32_t NOTOSERIF_16_OPTIMIZABLE_PAIRS[] = {
    0x00620063u, 0x00620065u, 0x0062006Fu, 0x00620071u, 0x00620073u, 0x00630073u, 0x00650073u, 0x00670067u,
    0x0067006Au, 0x00670073u, 0x006F0061u, 0x006F0063u, 0x006F0064u, 0x006F0065u, 0x006F0067u, 0x006F006Fu,
    0x006F0071u, 0x006F0073u, 0x006F00E1u, 0x006F00E9u, 0x006F00F3u, 0x006F00F6u, 0x006F0151u, 0x00700063u,
    0x00700064u, 0x00700065u, 0x0070006Fu, 0x00700073u, 0x007000E9u, 0x007000F3u, 0x007000F6u, 0x00700151u,
    0x00730061u, 0x00730062u, 0x0073006Au, 0x00730070u, 0x00730074u, 0x007300E1u, 0x00E90073u, 0x00F30061u,
    0x00F30063u, 0x00F30064u, 0x00F30065u, 0x00F30067u, 0x00F3006Fu, 0x00F30071u, 0x00F30073u, 0x00F300E9u,
    0x00F300F3u, 0x00F300F6u, 0x00F30151u, 0x00F60061u, 0x00F60063u, 0x00F60064u, 0x00F60065u, 0x00F60067u,
    0x00F6006Fu, 0x00F60071u, 0x00F60073u, 0x00F600E9u, 0x00F600F3u, 0x00F600F6u, 0x00F60151u, 0x01510061u,
    0x01510063u, 0x01510064u, 0x01510065u, 0x01510067u, 0x0151006Fu, 0x01510071u, 0x01510073u, 0x015100E9u,
    0x015100F3u, 0x015100F6u, 0x01510151u,
};
static_assert(sizeof(NOTOSERIF_16_OPTIMIZABLE_PAIRS) /
                  sizeof(NOTOSERIF_16_OPTIMIZABLE_PAIRS[0]) == 75,
              "Noto Serif 16 pair table must contain 75 entries");

enum class PairTable : uint8_t { Bitter16, NotoSerif16 };
constexpr int NOTOSERIF_16_OPTIMIZATION_FONT_ID = 17214534;

inline PairTable tableForFontId(const int fontId) {
  return fontId == NOTOSERIF_16_OPTIMIZATION_FONT_ID
             ? PairTable::NotoSerif16
             : PairTable::Bitter16;
}

constexpr uint8_t ONE_PX_FP4 = 16;

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

constexpr uint8_t PACKED_THRESHOLD_SHIFT = 5;
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
  return code == 7 ? 0u : (code >= 1 && code <= 6
                            ? static_cast<uint8_t>(45u + code * 5u) : 60u);
}

inline uint8_t packConfig(const uint8_t thresholdCode, const uint8_t budgetPx) {
  if (thresholdCode < 1 || thresholdCode > 7 || budgetPx == 0) return 0;
  return static_cast<uint8_t>((thresholdCode << PACKED_THRESHOLD_SHIFT) |
                              std::min<uint8_t>(budgetPx, PACKED_BUDGET_MASK));
}

inline bool isPackedConfig(const uint8_t value) {
  const uint8_t code = static_cast<uint8_t>((value & PACKED_THRESHOLD_MASK) >> PACKED_THRESHOLD_SHIFT);
  return code >= 1 && code <= 7;
}

inline uint8_t unpackThresholdCode(const uint8_t value) {
  return isPackedConfig(value)
             ? static_cast<uint8_t>((value & PACKED_THRESHOLD_MASK) >> PACKED_THRESHOLD_SHIFT)
             : 0;
}

inline uint8_t unpackBudget(const uint8_t value) {
  return isPackedConfig(value) ? static_cast<uint8_t>(value & PACKED_BUDGET_MASK) : 0;
}

inline uint8_t pointSizeForFont(const EpdFontFamily& font, const PairTable table) {
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
    const uint8_t score = BitterSpacingScores::scoreForPair(left, right, pointSize);
    return score > 0 && (threshold == 0 || score >= threshold);
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
  const bool notoMeasured60 = lo < count && NOTOSERIF_16_OPTIMIZABLE_PAIRS[lo] == key;
  if (threshold == 60) return notoMeasured60;
  const uint8_t proxy = BitterSpacingScores::scoreForPair(left, right, pointSize);
  if (threshold == 0) return proxy > 0;
  if (threshold < 60) return notoMeasured60 || proxy >= threshold;
  return notoMeasured60 && proxy >= threshold;
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
      !isOptimizablePair(left, right, acc.pairTable, acc.pointSize, acc.threshold)) {
    return 0;
  }
  acc.fp4 = static_cast<uint8_t>(acc.fp4 + limits.stepFp4);
  if (acc.fp4 < ONE_PX_FP4) return 0;
  acc.fp4 = static_cast<uint8_t>(acc.fp4 - ONE_PX_FP4);
  ++acc.usedPx;
  ++acc.usedWordPx;
  return 1;
}

// CPHUN-164: shared AA/ABA zero-extra rule. Called exclusively when
// Betűköz optimalizálás is ON, with the same neighbor context in both the
// measurement and rasterizer paths. The correction-only path is unchanged.
inline uint8_t consumeGuardedPair(const uint32_t beforeLeft, const uint32_t left,
                                  const uint32_t right, const uint32_t afterRight,
                                  const EpdFontFamily::Style style, Accumulator& acc) {
  if (OpticalLineCorrection::isProtectedPair(beforeLeft, left, right, afterRight)) return 0;
  return consumePair(left, right, style, acc);
}

inline uint8_t consumeWord(const char* text, const EpdFontFamily::Style style,
                           Accumulator& acc) {
  if (!beginWord(text, style, acc)) return 0;
  const auto* cursor = reinterpret_cast<const uint8_t*>(text);
  uint32_t prevPrev = 0;
  uint32_t prev = 0;
  uint8_t extra = 0;
  while (*cursor) {
    const uint32_t cp = utf8NextCodepoint(&cursor);
    if (!cp) break;
    const auto* lookahead = cursor;
    const uint32_t next = *lookahead ? utf8NextCodepoint(&lookahead) : 0;
    if (prev) {
      extra = static_cast<uint8_t>(extra +
          consumeGuardedPair(prevPrev, prev, cp, next, style, acc));
    }
    prevPrev = prev;
    prev = cp;
  }
  return extra;
}
}  // namespace LetterSpacingOptimization
