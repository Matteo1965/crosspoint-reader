#pragma once
#include <cstddef>
#include <cstdint>
#include <cstdio>

// Shared between firmware and native tests. No real-time clock is required.
namespace ScreenshotSequence {
inline bool parseLastReserved(const char* text, uint32_t& value) {
  if (!text || *text < '0' || *text > '9') return false;
  uint32_t parsed = 0;
  const char* p = text;
  for (; *p >= '0' && *p <= '9'; ++p) {
    const uint32_t digit = static_cast<uint32_t>(*p - '0');
    if (parsed > (UINT32_MAX - digit) / 10u) return false;
    parsed = parsed * 10u + digit;
  }
  if (*p == '\r') ++p;
  if (*p == '\n') ++p;
  if (*p != '\0') return false;
  value = parsed;
  return true;
}

inline bool next(uint32_t lastReserved, uint32_t& candidate) {
  if (lastReserved == UINT32_MAX) return false;
  candidate = lastReserved + 1u;
  return true;
}

inline void formatId(char* output, size_t size, uint32_t id) {
  if (!output || size == 0) return;
  // Minimum of four digits; 10000 follows 9999 without wrapping.
  std::snprintf(output, size, "%04lu", static_cast<unsigned long>(id));
}
}  // namespace ScreenshotSequence
