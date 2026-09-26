#pragma once

// Chapter position stays available when the active section is temporarily released.
struct ChapterPosition {
  int pageIndex = 0;
  int totalPages = 0;
  constexpr int displayPage() const { return pageIndex + 1; }
  constexpr bool hasTotal() const { return totalPages > 0; }
  constexpr float chapterFraction() const {
    return hasTotal() ? static_cast<float>(pageIndex) / static_cast<float>(totalPages) : 0.0f;
  }
};
