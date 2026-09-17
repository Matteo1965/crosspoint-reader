from pathlib import Path
import re

# CPHUN-135r4k2
# Fix virtual chapters for incremental Section builds.
# Build on top of R4K1 SAFE:
# - virtual chapter rows use estimatedTotalPages(), not currently built pageCount
# - rows carry a relative progress target (permille)
# - selecting a virtual row uses the existing full-build percent-jump path
# - after the full build, snap the target forward to a paragraph boundary
# - no ChapterHtmlSlimParser page-break experiment

# Add a virtual-jump state flag to the reader.
hdr = Path("src/activities/reader/EpubReaderActivity.h")
h = hdr.read_text(encoding="utf-8")
needle = "  bool pendingPercentJump = false;\n  float pendingSpineProgress = 0.0f;\n"
if needle not in h:
    raise SystemExit("R4K2: percent-jump fields not found")
h = h.replace(
    needle,
    "  bool pendingPercentJump = false;\n"
    "  bool pendingVirtualChapterJump = false;\n"
    "  float pendingSpineProgress = 0.0f;\n",
    1,
)
hdr.write_text(h, encoding="utf-8")

# Extend virtual chapter payload with a relative target.
ch = Path("src/activities/reader/EpubReaderChapterSelectionActivity.h")
s = ch.read_text(encoding="utf-8")
old = '''  struct VirtualChapter {
    std::string title;
    int spineIndex = 0;
    uint16_t page = 0;
  };
'''
new = '''  struct VirtualChapter {
    std::string title;
    int spineIndex = 0;
    uint16_t page = 0;
    uint16_t progressPermille = 0;
  };
'''
if old not in s:
    raise SystemExit("R4K2: VirtualChapter struct not found")
s = s.replace(old, new, 1)
ch.write_text(s, encoding="utf-8")

cc = Path("src/activities/reader/EpubReaderChapterSelectionActivity.cpp")
s = cc.read_text(encoding="utf-8")
old = '''  if (virtualIndex >= 0) {
    const auto& v = virtualChapters[virtualIndex];
    setResult(ChapterResult{v.spineIndex, "__cphun_page_" + std::to_string(v.page)});
    finish();
    return;
  }
'''
new = '''  if (virtualIndex >= 0) {
    const auto& v = virtualChapters[virtualIndex];
    if (v.progressPermille > 0) {
      setResult(ChapterResult{v.spineIndex, "__cphun_pct_" + std::to_string(v.progressPermille)});
    } else {
      setResult(ChapterResult{v.spineIndex, "__cphun_page_" + std::to_string(v.page)});
    }
    finish();
    return;
  }
'''
if old not in s:
    raise SystemExit("R4K2: virtual activation block not found")
s = s.replace(old, new, 1)
cc.write_text(s, encoding="utf-8")

reader = Path("src/activities/reader/EpubReaderActivity.cpp")
r = reader.read_text(encoding="utf-8")

# Replace R4K1's pageCount-dependent split generation.
start = r.find("      // CPHUN-135r4k1 SAFE: only physically oversized XHTML spines are")
if start < 0:
    raise SystemExit("R4K2: R4K1 virtual split block start not found")
end_marker = "\n\n      // Release the section while the chapter list is up"
end = r.find(end_marker, start)
if end < 0:
    raise SystemExit("R4K2: virtual split block end not found")

new_split = r'''      // CPHUN-135r4k2: virtual chapter rows must not depend on the small
      // incremental-build watermark (section->pageCount). Use the Section's
      // estimated total instead, and store each target as relative progress.
      // The selected target is resolved after the normal full-build percent path,
      // then snapped to a real paragraph boundary.
      size_t spineBytes = 0;
      const auto spineItemForSplit = epub->getSpineItem(spineIdx);
      const bool oversizedSpine =
          epub->getItemSize(spineItemForSplit.href, &spineBytes) && spineBytes >= (128u * 1024u);

      if (section && oversizedSpine) {
        const uint16_t estimatedPages = section->estimatedTotalPages();
        if (estimatedPages >= 24) {
          int tocIndex = epub->getTocIndexForSpineIndex(spineIdx);
          std::string parentTitle = "Fejezet";
          if (tocIndex >= 0 && tocIndex < epub->getTocItemsCount()) {
            parentTitle = epub->getTocItem(tocIndex).title;
            if (parentTitle.empty()) parentTitle = "Fejezet";
          }

          constexpr uint16_t TARGET_PAGES = 12;
          constexpr uint16_t MIN_TAIL_PAGES = 6;
          uint16_t lastPermille = 0;
          int part = 2;

          for (uint16_t target = TARGET_PAGES;
               target + MIN_TAIL_PAGES < estimatedPages;
               target = static_cast<uint16_t>(target + TARGET_PAGES)) {
            uint16_t permille =
                static_cast<uint16_t>((static_cast<uint32_t>(target) * 1000u) / estimatedPages);
            permille = std::max<uint16_t>(1, std::min<uint16_t>(999, permille));
            if (permille <= lastPermille + 20) continue;

            EpubReaderChapterSelectionActivity::VirtualChapter v;
            v.title = parentTitle + " – " + std::to_string(part++);
            v.spineIndex = spineIdx;
            v.progressPermille = permille;
            virtualChapters.push_back(std::move(v));
            lastPermille = permille;
          }
        }
      }'''
r = r[:start] + new_split + r[end:]

# Handle relative virtual pseudo-anchors before the old page pseudo-anchor.
old = '''            constexpr const char* VIRTUAL_PAGE_PREFIX = "__cphun_page_";
            if (chapterResult.anchor.rfind(VIRTUAL_PAGE_PREFIX, 0) == 0) {
              const int page = std::max(0, atoi(chapterResult.anchor.c_str() + strlen(VIRTUAL_PAGE_PREFIX)));
              pendingAnchor.clear();
              pendingPageJump = static_cast<uint16_t>(std::min(page, static_cast<int>(UINT16_MAX - 1)));
              nextPageNumber = page;
            } else {
              pendingPageJump.reset();
              pendingAnchor = chapterResult.anchor;
              nextPageNumber = 0;
            }
'''
new = '''            constexpr const char* VIRTUAL_PERCENT_PREFIX = "__cphun_pct_";
            constexpr const char* VIRTUAL_PAGE_PREFIX = "__cphun_page_";
            if (chapterResult.anchor.rfind(VIRTUAL_PERCENT_PREFIX, 0) == 0) {
              const int permille =
                  std::clamp(atoi(chapterResult.anchor.c_str() + strlen(VIRTUAL_PERCENT_PREFIX)), 1, 999);
              pendingAnchor.clear();
              pendingPageJump.reset();
              pendingSpineProgress = static_cast<float>(permille) / 1000.0f;
              pendingPercentJump = true;
              pendingVirtualChapterJump = true;
              nextPageNumber = 0;
            } else if (chapterResult.anchor.rfind(VIRTUAL_PAGE_PREFIX, 0) == 0) {
              const int page = std::max(0, atoi(chapterResult.anchor.c_str() + strlen(VIRTUAL_PAGE_PREFIX)));
              pendingAnchor.clear();
              pendingPageJump = static_cast<uint16_t>(std::min(page, static_cast<int>(UINT16_MAX - 1)));
              pendingVirtualChapterJump = false;
              nextPageNumber = page;
            } else {
              pendingPageJump.reset();
              pendingVirtualChapterJump = false;
              pendingAnchor = chapterResult.anchor;
              nextPageNumber = 0;
            }
'''
if old not in r:
    raise SystemExit("R4K2: R4J virtual callback block not found")
r = r.replace(old, new, 1)

# Snap the full-build percentage result to the next real paragraph boundary.
old = '''    if (pendingPercentJump && section->pageCount > 0) {
      int newPage = static_cast<int>(pendingSpineProgress * static_cast<float>(section->pageCount));
      if (newPage >= section->pageCount) newPage = section->pageCount - 1;
      section->currentPage = newPage;
      pendingPercentJump = false;
    }
'''
new = '''    if (pendingPercentJump && section->pageCount > 0) {
      int newPage = static_cast<int>(pendingSpineProgress * static_cast<float>(section->pageCount));
      if (newPage >= section->pageCount) newPage = section->pageCount - 1;

      if (pendingVirtualChapterJump && newPage > 0) {
        constexpr int PARAGRAPH_SEARCH_PAGES = 12;
        const int searchEnd =
            std::min<int>(section->pageCount - 1, newPage + PARAGRAPH_SEARCH_PAGES);
        for (int page = newPage; page <= searchEnd; ++page) {
          const auto here = section->getParagraphIndexForPage(static_cast<uint16_t>(page));
          const auto prev = section->getParagraphIndexForPage(static_cast<uint16_t>(page - 1));
          if (here && prev && *here != *prev) {
            newPage = page;
            break;
          }
        }
      }

      section->currentPage = newPage;
      pendingPercentJump = false;
      pendingVirtualChapterJump = false;
    }
'''
if old not in r:
    raise SystemExit("R4K2: percent jump application block not found")
r = r.replace(old, new, 1)

reader.write_text(r, encoding="utf-8")

print("CPHUN-135r4k2 applied: estimated-total virtual rows + relative full-build jump + paragraph snap")
