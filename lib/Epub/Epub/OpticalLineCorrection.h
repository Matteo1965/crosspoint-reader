#pragma once

#include <algorithm>
#include <cstdint>

// CPHUN-164: shared, integer-only pixel distribution. The rounding rule gives
// leftover pixels to gaps spread across a line, including the rightmost gap;
// it is deterministic in both layout and rasterization.
namespace OpticalLineCorrection {
constexpr int MAX_INK_CORRECTION_PX = 5;

// slot is zero based. The allocation always sums to extra for slotCount > 0.
inline int extraForSlot(int slot, int slotCount, int extra) {
  if (slotCount <= 0 || slot < 0 || slot >= slotCount || extra <= 0) return 0;
  const int base = extra / slotCount;
  const int remainder = extra % slotCount;
  return base + ((slot + 1) * remainder / slotCount - slot * remainder / slotCount);
}

// Protect native AA pairs and both gaps of ABA only when the optimized
// letter-spacing path is enabled. Case-sensitive Unicode codepoint equality
// matches the calibrated optimizer. The other spacing path never calls this.
inline bool isLatinLetter(uint32_t cp) {
  return (cp >= 'A' && cp <= 'Z') || (cp >= 'a' && cp <= 'z') ||
         (cp >= 0x00C0u && cp <= 0x024Fu);
}
inline bool isProtectedPair(uint32_t beforeLeft, uint32_t left,
                            uint32_t right, uint32_t afterRight) {
  return !isLatinLetter(left) || !isLatinLetter(right) || left == right ||
         (beforeLeft != 0 && beforeLeft == right) ||
         (afterRight != 0 && left == afterRight);
}

// The normal letter-spacing mode uses 0 or 1. Values 2..31 are reserved for
// single-word, no-space lines and encode a total budget of 1..30 pixels.
// Packed font-score optimization (threshold code 1..7) uses values >= 32.
inline bool isStandaloneWordSpacing(uint8_t value) { return value >= 2 && value <= 31; }
inline uint8_t encodeStandaloneBudget(int budget) {
  return budget > 0 ? static_cast<uint8_t>(std::min(budget, 30) + 1) : 0;
}
inline int standaloneBudget(uint8_t value) { return isStandaloneWordSpacing(value) ? value - 1 : 0; }
}  // namespace OpticalLineCorrection
