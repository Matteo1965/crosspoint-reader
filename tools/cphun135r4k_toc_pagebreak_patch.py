from pathlib import Path
import re

# CPHUN-135r4k
# Layered chapter reconstruction:
#   1) preserve parsed TOC and insert missing meaningful spine XHTML files,
#   2) honour explicit source page-break markers as preferred split points,
#   3) fill only oversized remaining gaps with paragraph-safe virtual chapters.

# ---------------------------------------------------------------------------
# 1) Supplement partial TOCs instead of replacing them.
# ---------------------------------------------------------------------------
hdr = Path("lib/Epub/Epub/BookMetadataCache.h")
h = hdr.read_text(encoding="utf-8")
needle = "  bool replaceTocWithSpineFiles();\n"
if needle not in h:
    raise SystemExit("R4K: replaceTocWithSpineFiles declaration not found")
h = h.replace(needle, needle + "  bool supplementTocWithMissingSpineFiles();\n", 1)
hdr.write_text(h, encoding="utf-8")

cpp = Path("lib/Epub/Epub/BookMetadataCache.cpp")
c = cpp.read_text(encoding="utf-8")
c, n = re.subn(
    r'constexpr uint8_t BOOK_CACHE_VERSION = \d+;[^\n]*',
    'constexpr uint8_t BOOK_CACHE_VERSION = 12;  // v12: preserve partial TOC and insert missing reading spines',
    c,
    count=1,
)
if n != 1:
    raise SystemExit("R4K: BOOK_CACHE_VERSION not found")

insert_before = "bool BookMetadataCache::replaceTocWithSpineFiles() {"
if insert_before not in c:
    raise SystemExit("R4K: replaceTocWithSpineFiles definition not found")

supplement = r'''
bool BookMetadataCache::supplementTocWithMissingSpineFiles() {
  if (!buildMode || !tocFile || !spineFile || tocCount == 0) {
    return false;
  }

  // Flush the parsed TOC before reopening the temp file for reading.
  const bool flushed = !passOut || passOut->flush();
  passOut.reset();
  tocFile.close();
  if (!flushed) {
    LOG_ERR("BMC", "Partial TOC supplement: failed to flush parsed TOC");
    return false;
  }

  HalFile tocIn;
  if (!Storage.openFileForRead("BMC", cachePath + tmpTocBinFile, tocIn)) {
    LOG_ERR("BMC", "Partial TOC supplement: failed to reopen TOC temp file");
    return false;
  }

  std::vector<TocEntry> original;
  original.reserve(tocCount);
  for (int i = 0; i < tocCount; ++i) {
    original.push_back(readTocEntry(tocIn));
  }
  tocIn.close();

  std::vector<bool> covered(spineCount, false);
  for (const auto& item : original) {
    if (item.spineIndex >= 0 && item.spineIndex < spineCount) covered[item.spineIndex] = true;
  }

  struct MissingToc {
    TocEntry entry;
    int spineIndex = -1;
  };
  std::vector<MissingToc> missing;

  spineFile.seek(0);
  for (int spine = 0; spine < spineCount; ++spine) {
    const auto spineEntry = readSpineEntry(spineFile);
    if (covered[spine]) continue;

    std::string lower = spineEntry.href;
    std::transform(lower.begin(), lower.end(), lower.begin(),
                   [](unsigned char ch) { return static_cast<char>(std::tolower(ch)); });
    const auto hash = lower.find('#');
    if (hash != std::string::npos) lower.erase(hash);
    const auto query = lower.find('?');
    if (query != std::string::npos) lower.erase(query);

    const bool html =
        (lower.size() >= 5 && lower.rfind(".html") == lower.size() - 5) ||
        (lower.size() >= 6 && lower.rfind(".xhtml") == lower.size() - 6) ||
        (lower.size() >= 4 && lower.rfind(".htm") == lower.size() - 4);
    if (!html) continue;

    const auto slash = lower.find_last_of('/');
    const std::string base = slash == std::string::npos ? lower : lower.substr(slash + 1);

    // Packaging/navigation matter is not a reading chapter. Footnote/endnote files
    // are intentionally excluded: links still resolve to them, but they should not
    // become normal chapter rows merely because the source TOC omitted them.
    if (base.find("cover") != std::string::npos ||
        base == "nav.xhtml" || base == "nav.html" ||
        base == "toc.xhtml" || base == "toc.html" || base == "toc.htm" ||
        base.find("titlepage") != std::string::npos ||
        base.find("title_page") != std::string::npos ||
        base.find("copyright") != std::string::npos ||
        base.find("colophon") != std::string::npos ||
        base.find("footnote") != std::string::npos ||
        base.find("endnote") != std::string::npos ||
        base == "notes.html" || base == "notes.xhtml" || base == "notes.htm") {
      continue;
    }

    std::string title = FsHelpers::decodeUriEscapes(spineEntry.href);
    const auto titleHash = title.find('#');
    if (titleHash != std::string::npos) title.erase(titleHash);
    const auto titleQuery = title.find('?');
    if (titleQuery != std::string::npos) title.erase(titleQuery);
    const auto titleSlash = title.find_last_of('/');
    if (titleSlash != std::string::npos) title.erase(0, titleSlash + 1);
    const auto dot = title.find_last_of('.');
    if (dot != std::string::npos) title.erase(dot);
    for (char& ch : title) {
      if (ch == '_' || ch == '-') ch = ' ';
    }
    while (!title.empty() && title.front() == ' ') title.erase(title.begin());
    while (!title.empty() && title.back() == ' ') title.pop_back();
    if (title.empty()) title = "Fejezet " + std::to_string(spine + 1);

    MissingToc item;
    item.entry = TocEntry(utf8ComposeNfc(title), spineEntry.href, "", 0, static_cast<int16_t>(spine));
    item.spineIndex = spine;
    missing.push_back(std::move(item));
  }

  if (missing.empty()) {
    if (!Storage.openFileForWrite("BMC", cachePath + tmpTocBinFile, tocFile)) {
      LOG_ERR("BMC", "Partial TOC supplement: failed to reopen TOC temp file");
      return false;
    }
    passOut = makeUniqueNoThrow<serialization::BufferedFileWriter>(tocFile, BUILD_IO_BUFFER_SIZE);
    for (const auto& item : original) {
      if (passOut) writeTocEntryTo(*passOut, item);
      else writeTocEntry(tocFile, item);
    }
    LOG_DBG("BMC", "Partial TOC supplement: all meaningful reading spines already covered");
    return false;
  }

  // Preserve the relative order and titles of all authored TOC rows. Insert each
  // missing spine immediately before the next authored row whose spine comes later.
  std::vector<TocEntry> merged;
  merged.reserve(original.size() + missing.size());
  size_t mi = 0;
  for (const auto& item : original) {
    if (item.spineIndex >= 0) {
      while (mi < missing.size() && missing[mi].spineIndex < item.spineIndex) {
        merged.push_back(std::move(missing[mi].entry));
        ++mi;
      }
    }
    merged.push_back(item);
  }
  while (mi < missing.size()) {
    merged.push_back(std::move(missing[mi].entry));
    ++mi;
  }

  if (!Storage.openFileForWrite("BMC", cachePath + tmpTocBinFile, tocFile)) {
    LOG_ERR("BMC", "Partial TOC supplement: failed to rewrite TOC temp file");
    return false;
  }
  tocCount = 0;
  passOut = makeUniqueNoThrow<serialization::BufferedFileWriter>(tocFile, BUILD_IO_BUFFER_SIZE);
  for (const auto& item : merged) {
    if (passOut) writeTocEntryTo(*passOut, item);
    else writeTocEntry(tocFile, item);
    ++tocCount;
  }

  LOG_DBG("BMC", "Partial TOC supplement: preserved %zu authored rows, inserted %zu missing spine rows",
          original.size(), missing.size());
  return true;
}

'''
c = c.replace(insert_before, supplement + insert_before, 1)
cpp.write_text(c, encoding="utf-8")

epub = Path("lib/Epub/Epub.cpp")
e = epub.read_text(encoding="utf-8")
old = '''  if (bookMetadataCache->getTocCount() <= 1 && bookMetadataCache->getSpineCount() > 1) {
    LOG_DBG("EBP", "Weak TOC (%d entry), trying file-based automatic TOC from spine", bookMetadataCache->getTocCount());
    if (bookMetadataCache->replaceTocWithSpineFiles()) {
      tocParsed = true;
    }
  }
'''
new = '''  if (bookMetadataCache->getTocCount() <= 1 && bookMetadataCache->getSpineCount() > 1) {
    LOG_DBG("EBP", "Weak TOC (%d entry), trying file-based automatic TOC from spine", bookMetadataCache->getTocCount());
    if (bookMetadataCache->replaceTocWithSpineFiles()) {
      tocParsed = true;
    }
  } else if (bookMetadataCache->getTocCount() > 1) {
    // CPHUN-135r4k: a multi-row TOC may still cover only part of the reading
    // spine. Preserve the authored rows and insert meaningful missing XHTML files.
    if (bookMetadataCache->supplementTocWithMissingSpineFiles()) {
      tocParsed = true;
    }
  }
'''
if old not in e:
    raise SystemExit("R4K: weak TOC dispatch block not found")
e = e.replace(old, new, 1)
epub.write_text(e, encoding="utf-8")

# ---------------------------------------------------------------------------
# 2) Record explicit source page breaks as synthetic anchors.
#    These are source-authored breaks, not artificial virtual-chapter breaks.
# ---------------------------------------------------------------------------
ph = Path("lib/Epub/Epub/parsers/ChapterHtmlSlimParser.h")
s = ph.read_text(encoding="utf-8")
needle = "  std::string pendingAnchorId;          // deferred until after previous text block is flushed\n"
if needle not in s:
    raise SystemExit("R4K: pendingAnchorId member not found")
s = s.replace(
    needle,
    needle +
    '  std::string pendingExplicitBreakAlias;  // __cphun_pb_N recorded beside a real id when present\n'
    '  uint16_t explicitPageBreakCounter = 0;\n',
    1,
)
ph.write_text(s, encoding="utf-8")

pcpp = Path("lib/Epub/Epub/parsers/ChapterHtmlSlimParser.cpp")
p = pcpp.read_text(encoding="utf-8")

old_flush = '''  // Record deferred anchor after previous block is flushed (and any TOC page break)
  anchorData.push_back({std::move(pendingAnchorId), static_cast<uint16_t>(completedPageCount)});
  pendingAnchorId.clear();
}
'''
new_flush = '''  // Record deferred anchor after previous block is flushed (and any TOC page break).
  anchorData.push_back({std::move(pendingAnchorId), static_cast<uint16_t>(completedPageCount)});
  pendingAnchorId.clear();
  if (!pendingExplicitBreakAlias.empty()) {
    anchorData.push_back({std::move(pendingExplicitBreakAlias), static_cast<uint16_t>(completedPageCount)});
    pendingExplicitBreakAlias.clear();
  }
}
'''
if old_flush not in p:
    raise SystemExit("R4K: flushPendingAnchor tail not found")
p = p.replace(old_flush, new_flush, 1)

marker = '''  auto centeredBlockStyle = BlockStyle();
'''
if marker not in p:
    raise SystemExit("R4K: centeredBlockStyle marker not found")
break_logic = r'''  // CPHUN-135r4k: honour explicit source page-break markers and expose their
  // resulting page as a synthetic anchor. This is intentionally limited to
  // author-supplied inline/class markers; fallback virtual chapter boundaries
  // never force a page break.
  if (self->insideBody) {
    std::string lowerStyle = styleAttr;
    std::string lowerClass = classAttr;
    std::transform(lowerStyle.begin(), lowerStyle.end(), lowerStyle.begin(),
                   [](unsigned char ch) { return static_cast<char>(std::tolower(ch)); });
    std::transform(lowerClass.begin(), lowerClass.end(), lowerClass.begin(),
                   [](unsigned char ch) { return static_cast<char>(std::tolower(ch)); });

    const bool explicitBefore =
        ((lowerStyle.find("page-break-before") != std::string::npos ||
          lowerStyle.find("break-before") != std::string::npos) &&
         (lowerStyle.find("always") != std::string::npos ||
          lowerStyle.find("page") != std::string::npos ||
          lowerStyle.find("left") != std::string::npos ||
          lowerStyle.find("right") != std::string::npos)) ||
        lowerClass.find("pagebreak") != std::string::npos ||
        lowerClass.find("page-break") != std::string::npos ||
        lowerClass.find("page_break") != std::string::npos ||
        lowerClass.find("newpage") != std::string::npos;

    if (explicitBefore) {
      const std::string alias = "__cphun_pb_" + std::to_string(++self->explicitPageBreakCounter);
      if (self->pendingAnchorId.empty()) {
        self->pendingAnchorId = alias;
      } else {
        self->pendingExplicitBreakAlias = alias;
      }
      if (std::find(self->tocAnchors.begin(), self->tocAnchors.end(), self->pendingAnchorId) ==
          self->tocAnchors.end()) {
        self->tocAnchors.push_back(self->pendingAnchorId);
      }
    }
  }

'''
p = p.replace(marker, break_logic + marker, 1)
pcpp.write_text(p, encoding="utf-8")

# ---------------------------------------------------------------------------
# 3) Large-spine virtual chapters: explicit page breaks first, then fill only
#    oversized gaps with paragraph-safe boundaries. Never split small spines.
# ---------------------------------------------------------------------------
reader = Path("src/activities/reader/EpubReaderActivity.cpp")
r = reader.read_text(encoding="utf-8")
start = r.find("      // CPHUN-135r4j: subdivide only a genuinely long rendered section.")
if start < 0:
    raise SystemExit("R4K: R4J virtual split block start not found")
end_marker = "\n\n      // Release the section while the chapter list is up"
end = r.find(end_marker, start)
if end < 0:
    raise SystemExit("R4K: R4J virtual split block end not found")

new_split = r'''      // CPHUN-135r4k: only genuinely oversized physical XHTML spines are
      // candidates for subdivision. First use source-authored page-break anchors;
      // only gaps still larger than 24 rendered pages get paragraph-safe virtual
      // boundaries. Fallback boundaries are navigation-only and do not create
      // artificial page breaks.
      size_t spineBytes = 0;
      const auto spineItemForSplit = epub->getSpineItem(spineIdx);
      const bool oversizedSpine =
          epub->getItemSize(spineItemForSplit.href, &spineBytes) && spineBytes >= (128u * 1024u);

      if (section && oversizedSpine && section->pageCount >= 24) {
        int tocIndex = epub->getTocIndexForSpineIndex(spineIdx);
        std::string parentTitle = "Fejezet";
        if (tocIndex >= 0 && tocIndex < epub->getTocItemsCount()) {
          parentTitle = epub->getTocItem(tocIndex).title;
          if (parentTitle.empty()) parentTitle = "Fejezet";
        }

        constexpr uint16_t TARGET_PAGES = 12;
        constexpr uint16_t MAX_GAP_PAGES = 24;
        constexpr uint16_t MIN_PART_PAGES = 4;

        std::vector<uint16_t> boundaries;
        // Explicit source page breaks are preferred. Query synthetic anchors in
        // order until the first missing one; only retain useful interior breaks.
        for (uint16_t n = 1; n < 128; ++n) {
          const auto page = section->findAnchor("__cphun_pb_" + std::to_string(n));
          if (!page) break;
          if (*page >= MIN_PART_PAGES && *page + MIN_PART_PAGES < section->pageCount) {
            if (boundaries.empty() || *page >= boundaries.back() + MIN_PART_PAGES) {
              boundaries.push_back(*page);
            }
          }
        }

        auto paragraphBoundaryNear = [&](uint16_t target, uint16_t hardEnd) -> std::optional<uint16_t> {
          if (target < 1 || hardEnd <= target) return std::nullopt;
          const uint16_t searchEnd =
              std::min<uint16_t>(static_cast<uint16_t>(section->pageCount - 1),
                                 std::min<uint16_t>(hardEnd, static_cast<uint16_t>(target + TARGET_PAGES)));
          for (uint16_t page = target; page <= searchEnd; ++page) {
            const auto here = section->getParagraphIndexForPage(page);
            const auto prev = section->getParagraphIndexForPage(page - 1);
            if (here && prev && *here != *prev) return page;
          }
          return std::nullopt;
        };

        // Fill only oversized gaps between explicit breaks (and the head/tail).
        std::vector<uint16_t> completeBoundaries;
        uint16_t gapStart = 0;
        size_t explicitIndex = 0;
        while (true) {
          const uint16_t gapEnd = explicitIndex < boundaries.size()
                                      ? boundaries[explicitIndex]
                                      : section->pageCount;
          uint16_t cursor = gapStart;
          while (gapEnd > cursor + MAX_GAP_PAGES) {
            const uint16_t target = static_cast<uint16_t>(cursor + TARGET_PAGES);
            const uint16_t hardEnd =
                gapEnd > MIN_PART_PAGES ? static_cast<uint16_t>(gapEnd - MIN_PART_PAGES) : gapEnd;
            const auto chosen = paragraphBoundaryNear(target, hardEnd);
            if (!chosen || *chosen <= cursor + MIN_PART_PAGES) break;
            completeBoundaries.push_back(*chosen);
            cursor = *chosen;
          }
          if (explicitIndex < boundaries.size()) {
            if (completeBoundaries.empty() ||
                boundaries[explicitIndex] >= completeBoundaries.back() + MIN_PART_PAGES) {
              completeBoundaries.push_back(boundaries[explicitIndex]);
            }
            gapStart = boundaries[explicitIndex];
            ++explicitIndex;
          } else {
            break;
          }
        }

        int part = 2;
        for (const uint16_t page : completeBoundaries) {
          EpubReaderChapterSelectionActivity::VirtualChapter v;
          v.title = parentTitle + " – " + std::to_string(part++);
          v.spineIndex = spineIdx;
          v.page = page;
          virtualChapters.push_back(std::move(v));
        }
      }'''
r = r[:start] + new_split + r[end:]
reader.write_text(r, encoding="utf-8")

print("CPHUN-135r4k applied: partial TOC supplement + explicit page-break priority + oversized-gap fallback")
