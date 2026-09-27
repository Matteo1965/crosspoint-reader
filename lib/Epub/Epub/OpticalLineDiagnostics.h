#pragma once
#include <cstddef>
#include <cstdint>
#include <cstdio>
#include <cstring>

// Fixed-size, allocation-free diagnostic ring. Every ordinary text line rendered
// since boot contributes one entry. The last 64 entries accompany each BMP
// screenshot as a same-name .txt sidecar on the SD card.
namespace OpticalLineDiagnostics {
struct Entry {
  char ending[40]{};
  char status[20]{};
  int16_t target = 0;
  int16_t finalWordX = 0;
  int16_t finalAdvance = 0;
  int16_t inset = -1;
  int16_t gaps = 0;
  int16_t correction = 0;
  int16_t normalRightExclusive = -1;
  int16_t paintedRightExclusive = -1;
  int16_t normalMarginDelta = 0;
};
struct Store {
  Entry rows[64]{};
  unsigned head = 0;
  unsigned used = 0;
};
inline Store& store() {
  static Store state;
  return state;
}
inline void record(const char* lastWord, const char* status,
                   int target, int wordX, int advance, int inset,
                   int gaps, int extra, int screenX) {
  auto& s = store();
  auto& e = s.rows[s.head];
  std::snprintf(e.ending, sizeof(e.ending), "%s", lastWord ? lastWord : "");
  std::snprintf(e.status, sizeof(e.status), "%s", status ? status : "");
  e.target = static_cast<int16_t>(target);
  e.finalWordX = static_cast<int16_t>(wordX);
  e.finalAdvance = static_cast<int16_t>(advance);
  e.inset = static_cast<int16_t>(inset);
  e.gaps = static_cast<int16_t>(gaps);
  e.correction = static_cast<int16_t>(extra);
  // Right boundary is EXCLUSIVE; the final admissible pixel is right - 1.
  // Hyphenated lines are excluded from optical closure and may hang outward.
  if (target > 0 && inset >= 0) {
    const int right = screenX + target;
    const int painted = screenX + wordX + advance - inset + extra;
    e.normalRightExclusive = static_cast<int16_t>(right);
    e.paintedRightExclusive = static_cast<int16_t>(painted);
    e.normalMarginDelta = static_cast<int16_t>(right - painted);
  } else {
    e.normalRightExclusive = -1;
    e.paintedRightExclusive = -1;
    e.normalMarginDelta = 0;
  }
  s.head = (s.head + 1) % 64;
  if (s.used < 64) ++s.used;
}
inline const Entry& oldestAt(unsigned index) {
  const auto& s = store();
  return s.rows[(s.head + 64 - s.used + index) % 64];
}
} // namespace OpticalLineDiagnostics
