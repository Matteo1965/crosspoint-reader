"""Reapply the chapter-position adapter after the tested CPHUN-152 patch chain.

That legacy chain regenerates EpubReaderActivity.cpp and removes the early CPHUN-157
chapter-position change. Port it back onto the newly generated file rather than
replacing the whole reader and losing CPHUN-152 export/reindex features.
"""
from pathlib import Path

h = Path("src/activities/reader/EpubReaderActivity.h")
s = h.read_text(encoding="utf-8")
if '#include "ChapterPosition.h"' not in s:
    assert '#include "BookmarkEntry.h"' in s
    s = s.replace('#include "BookmarkEntry.h"', '#include "BookmarkEntry.h"\n#include "ChapterPosition.h"', 1)
if "ChapterPosition chapterPosition() const;" not in s:
    assert "  void openReaderMenu(bool startOnBookTab = false);" in s
    s = s.replace("  void openReaderMenu(bool startOnBookTab = false);",
                  "  ChapterPosition chapterPosition() const;\n"
                  "  int bookPercentFor(const ChapterPosition& position) const;\n"
                  "  void openReaderMenu(bool startOnBookTab = false);", 1)
h.write_text(s, encoding="utf-8")

p = Path("src/activities/reader/EpubReaderActivity.cpp")
s = p.read_text(encoding="utf-8")
if "ChapterPosition EpubReaderActivity::chapterPosition() const" not in s:
    begin = s.index("void EpubReaderActivity::openReaderMenu(const bool startOnBookTab) {")
    end = s.index("  startActivityForResult(", begin)
    replacement = """ChapterPosition EpubReaderActivity::chapterPosition() const {
  if (section) return {section->currentPage, section->estimatedTotalPages()};
  return {nextPageNumber, cachedChapterTotalPageCount};
}

int EpubReaderActivity::bookPercentFor(const ChapterPosition& position) const {
  if (!epub || epub->getBookSize() == 0 || !position.hasTotal()) return 0;
  const float progress = epub->calculateProgress(
      currentSpineIndex, std::clamp(position.chapterFraction(), 0.0f, 1.0f));
  return clampPercent(static_cast<int>(std::clamp(progress, 0.0f, 1.0f) * 100.0f + 0.5f));
}

void EpubReaderActivity::openReaderMenu(const bool startOnBookTab) {
  pendingManualTurn = 0;
  const ChapterPosition position = chapterPosition();
  const int currentPage = position.displayPage();
  const int totalPages = position.totalPages;
  const int bookProgressPercent = bookPercentFor(position);
"""
    prefix = s[begin:end]
    assert "const int currentPage" in prefix and "bookProgressPercent" in prefix, (
        "Reader menu structure changed; do not replace unknown upstream logic"
    )
    s = s[:begin] + replacement + s[end:]
    p.write_text(s, encoding="utf-8")
print("CPHUN-157 chapter-position repair applied after CPHUN-152 chain")
