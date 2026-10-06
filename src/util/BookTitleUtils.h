#pragma once

#include <string>
#include <string_view>
#include <utility>

namespace bookui {

inline std::string trimTechnicalSeparators(std::string value) {
  const auto first = value.find_first_not_of(" \t\r\n-_");
  if (first == std::string::npos) return {};
  const auto last = value.find_last_not_of(" \t\r\n-_");
  return value.substr(first, last - first + 1);
}

inline std::string asciiLower(std::string value) {
  for (char& c : value) {
    if (c >= 'A' && c <= 'Z') c = static_cast<char>(c - 'A' + 'a');
  }
  return value;
}

// Remove known workflow/device suffixes only when they are standalone tokens
// at the very end of the displayed title. Real words containing these strings
// are left untouched.
inline std::string cleanDisplayedBookTitle(std::string title) {
  title = trimTechnicalSeparators(std::move(title));
  const std::string lower = asciiLower(title);
  static constexpr const char* suffixes[] = {"ok", "x4", "test", "korr", "jav"};
  for (const char* suffix : suffixes) {
    const std::string_view token(suffix);
    if (lower.size() < token.size() ||
        lower.compare(lower.size() - token.size(), token.size(), token) != 0) {
      continue;
    }
    const size_t start = lower.size() - token.size();
    if (start > 0 && lower[start - 1] != ' ' && lower[start - 1] != '\t' &&
        lower[start - 1] != '-' && lower[start - 1] != '_') {
      continue;
    }
    title = trimTechnicalSeparators(title.substr(0, start));
    break;
  }
  return title;
}

}  // namespace bookui
