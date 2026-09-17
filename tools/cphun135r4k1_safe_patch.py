from pathlib import Path
import re

# CPHUN-135r4k1 SAFE
# Regression-isolation build:
#   - keep R4J footnote/page ownership fixes
#   - preserve authored TOC and supplement missing meaningful spine XHTML files
#   - keep large-spine virtual chapter fallback
#   - DO NOT modify ChapterHtmlSlimParser for explicit page-break detection

hdr = Path("lib/Epub/Epub/BookMetadataCache.h")
h = hdr.read_text(encoding="utf-8")
needle = "  bool replaceTocWithSpineFiles();\n"
if needle not in h:
    raise SystemExit("R4K1: replaceTocWithSpineFiles declaration not found")
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
    raise SystemExit("R4K1: BOOK_CACHE_VERSION not found")

insert_before = "bool BookMetadataCache::replaceTocWithSpineFiles() {"
if insert_before not in c:
    raise SystemExit("R4K1: replaceTocWithSpineFiles definition not found")

supplement = r'''
bool BookMetadataCache::supplementTocWithMissingSpineFiles() {
  if (!buildMode || !tocFile || !spineFile || tocCount == 0) return false;

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
  for (int i = 0; i < tocCount; ++i) original.push_back(readTocEntry(tocIn));
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
    for (char& ch : title) if (ch == '_' || ch == '-') ch = ' ';
    while (!title.empty() && title.front() == ' ') title.erase(title.begin());
    while (!title.empty() && title.back() == ' ') title.pop_back();
    if (title.empty()) title = "Fejezet " + std::to_string(spine + 1);

    MissingToc item;
    item.entry = TocEntry(utf8ComposeNfc(title), spineEntry.href, "", 0, static_cast<int16_t>(spine));
    item.spineIndex = spine;
    missing.push_back(std::move(item));
  }

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
  return !missing.empty();
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
    if (bookMetadataCache->supplementTocWithMissingSpineFiles()) {
      tocParsed = true;
    }
  }
'''
if old not in e:
    raise SystemExit("R4K1: weak TOC dispatch block not found")
e = e.replace(old, new, 1)
epub.write_text(e, encoding="utf-8")

# Restrict R4J virtual splitting to physically oversized XHTML only.
# No parser changes and no explicit source page-break detection in this SAFE build.
reader = Path("src/activities/reader/EpubReaderActivity.cpp")
r = reader.read_text(encoding="utf-8")
start = r.find("      // CPHUN-135r4j: subdivide only a genuinely long rendered section.")
if start < 0:
    raise SystemExit("R4K1: R4J virtual split block start not found")
end_marker = "\n\n      // Release the section while the chapter list is up"
end = r.find(end_marker, start)
if end < 0:
    raise SystemExit("R4K1: R4J virtual split block end not found")

new_split = r'''      // CPHUN-135r4k1 SAFE: only physically oversized XHTML spines are
      // subdivided. Boundaries remain paragraph-safe and navigation-only.
      // No parser-side explicit page-break detection is enabled in this build.
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
        uint16_t lastBoundary = 0;
        int part = 2;
        for (uint16_t target = TARGET_PAGES; target + 1 < section->pageCount; target += TARGET_PAGES) {
          std::optional<uint16_t> chosen;
          const uint16_t searchEnd =
              std::min<uint16_t>(section->pageCount - 1, target + TARGET_PAGES);
          for (uint16_t page = target; page <= searchEnd; ++page) {
            const auto here = section->getParagraphIndexForPage(page);
            const auto prev = section->getParagraphIndexForPage(page - 1);
            if (here && prev && *here != *prev) {
              chosen = page;
              break;
            }
          }
          if (!chosen || *chosen <= lastBoundary + 4) continue;
          EpubReaderChapterSelectionActivity::VirtualChapter v;
          v.title = parentTitle + " – " + std::to_string(part++);
          v.spineIndex = spineIdx;
          v.page = *chosen;
          virtualChapters.push_back(std::move(v));
          lastBoundary = *chosen;
        }
      }'''
r = r[:start] + new_split + r[end:]
reader.write_text(r, encoding="utf-8")

print("CPHUN-135r4k1 SAFE applied: TOC supplement + oversized paragraph-safe virtual chapters; no parser page-break changes")
