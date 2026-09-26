#pragma once

#include <cctype>
#include <cstddef>
#include <cstring>
#include <utility>

namespace DictWordEdges {
// Strip only punctuation at the edges. Preserve interior punctuation and
// hyphens inside compound words. UTF-8 sequences must be removed atomically.
inline std::pair<size_t, size_t> trim(const char* word) {
  if (!word) return {0, 0};
  const auto* b = reinterpret_cast<const unsigned char*>(word);
  size_t start = 0;
  size_t end = std::strlen(word);
  const auto isWordByte = [](unsigned char c) { return c >= 0x80 || std::isalnum(c) != 0; };
  while (start < end) {
    if (b[start] == '-' && start + 1 < end && isWordByte(b[start + 1])) break;
    if (!isWordByte(b[start])) {
      ++start;
    } else if (end - start >= 2 && b[start] == 0xC2 && (b[start + 1] == 0xAB || b[start + 1] == 0xBB)) {
      start += 2;  // U+00AB/U+00BB, French/Hungarian guillemets
    } else if (end - start >= 3 && b[start] == 0xE2 && (b[start + 1] == 0x80 || b[start + 1] == 0x81)) {
      start += 3;  // U+2000..U+206F, includes curly quotation marks
    } else {
      break;
    }
  }
  while (end > start) {
    if (b[end - 1] == '-' && end - start > 1 && isWordByte(b[end - 2])) break;
    if (!isWordByte(b[end - 1])) {
      --end;
    } else if (end - start >= 2 && b[end - 2] == 0xC2 && (b[end - 1] == 0xAB || b[end - 1] == 0xBB)) {
      end -= 2;
    } else if (end - start >= 3 && b[end - 3] == 0xE2 && (b[end - 2] == 0x80 || b[end - 2] == 0x81)) {
      end -= 3;
    } else {
      break;
    }
  }
  return {start, end};
}
}  // namespace DictWordEdges
