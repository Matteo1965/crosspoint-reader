from pathlib import Path

# CPHUN-48 on top of CPHUN-47:
# - Home: author on spare second title line; avoid a one-word second title line for 4+ word titles.
# - Home: cover outline +1 px (1 -> 2 px).
# - EPUB: when parsed TOC has <=1 entry but the spine has several HTML/XHTML files,
#   replace that weak TOC with a generated file-based TOC.

# --- Home header passes author as subtitle ---
p = Path('src/activities/home/HomeActivity.cpp')
s = p.read_text(encoding='utf-8')
old = '''  GUI.drawHeader(renderer, Rect{0, metrics.topPadding, pageWidth, metrics.homeTopPadding - metrics.topPadding},
                 metrics.homeContinueReadingInMenu && !recentBooks.empty() ? recentBooks[0].title.c_str() : nullptr);'''
new = '''  GUI.drawHeader(renderer, Rect{0, metrics.topPadding, pageWidth, metrics.homeTopPadding - metrics.topPadding},
                 metrics.homeContinueReadingInMenu && !recentBooks.empty() ? recentBooks[0].title.c_str() : nullptr,
                 metrics.homeContinueReadingInMenu && !recentBooks.empty() ? recentBooks[0].author.c_str() : nullptr);'''
if old not in s:
    raise SystemExit('CPHUN-48 HomeActivity header anchor missing')
s = s.replace(old, new, 1)
p.write_text(s, encoding='utf-8')

# --- RoundedRaff title wrapping / author / cover border ---
p = Path('src/components/themes/roundedraff/RoundedRaffTheme.cpp')
s = p.read_text(encoding='utf-8')
anchor = '''    const int lines = second.empty() ? 1 : 2;
    int textY = rect.y + std::max(0, (rect.height - lines * lineHeight) / 2) + 4;'''
replacement = '''    // Avoid an orphan single word on line 2 for titles with at least four words.
    size_t wordCount = 0;
    bool inWord = false;
    for (const char c : input) {
      if (c == ' ') {
        inWord = false;
      } else if (!inWord) {
        ++wordCount;
        inWord = true;
      }
    }
    if (wordCount >= 4 && !second.empty() && second.find(' ') == std::string::npos) {
      const size_t split = first.rfind(' ');
      if (split != std::string::npos) {
        const std::string candidate = first.substr(split + 1) + " " + second;
        if (renderer.getTextAdvanceX(kTitleFontId, candidate.c_str(), EpdFontFamily::BOLD) <= maxWidth) {
          second = candidate;
          first.erase(split);
        }
      }
    }

    // If the title fits on one line, use the otherwise-empty second line for the author.
    if (second.empty() && subtitle != nullptr && subtitle[0] != '\\0') {
      second = renderer.truncatedText(kTitleFontId, subtitle, maxWidth, EpdFontFamily::BOLD);
    }

    const int lines = second.empty() ? 1 : 2;
    int textY = rect.y + std::max(0, (rect.height - lines * lineHeight) / 2) + 4;'''
if anchor not in s:
    raise SystemExit('CPHUN-48 home title post-wrap anchor missing')
s = s.replace(anchor, replacement, 1)
old_border = '''      renderer.drawRoundedRect(tileX + (tileWidth - coverWidth) / 2, imgY, coverWidth,
                               RoundedRaffMetrics::values.homeCoverHeight, 1, kCoverRadius, true);'''
new_border = '''      renderer.drawRoundedRect(tileX + (tileWidth - coverWidth) / 2, imgY, coverWidth,
                               RoundedRaffMetrics::values.homeCoverHeight, 2, kCoverRadius, true);'''
if old_border not in s:
    raise SystemExit('CPHUN-48 cover border anchor missing')
s = s.replace(old_border, new_border, 1)
p.write_text(s, encoding='utf-8')

# --- BookMetadataCache: generated file-based TOC support ---
p = Path('lib/Epub/Epub/BookMetadataCache.h')
h = p.read_text(encoding='utf-8')
anchor = '  void createTocEntry(const std::string& title, const std::string& href, const std::string& anchor, uint8_t level);\n'
if anchor not in h:
    raise SystemExit('CPHUN-48 BookMetadataCache.h anchor missing')
h = h.replace(anchor, anchor + '  bool replaceTocWithSpineFiles();\n', 1)
p.write_text(h, encoding='utf-8')

p = Path('lib/Epub/Epub/BookMetadataCache.cpp')
s = p.read_text(encoding='utf-8')
s = s.replace('constexpr uint8_t BOOK_CACHE_VERSION = 10;  // v10: ignore ambiguous guide text references',
              'constexpr uint8_t BOOK_CACHE_VERSION = 11;  // v11: generated TOC for weak single-entry EPUB TOCs', 1)
insert_before = '/* ============= READING / LOADING FUNCTIONS ================ */'
if insert_before not in s:
    raise SystemExit('CPHUN-48 BookMetadataCache.cpp insertion anchor missing')
method = r'''
bool BookMetadataCache::replaceTocWithSpineFiles() {
  if (!buildMode || !tocFile || !spineFile) {
    LOG_DBG("BMC", "replaceTocWithSpineFiles called but TOC pass is not active");
    return false;
  }

  // Collect candidates first. createTocEntry seeks spineFile while mapping hrefs,
  // so do not interleave candidate enumeration with TOC writes.
  std::vector<std::string> hrefs;
  hrefs.reserve(spineCount);
  spineFile.seek(0);
  for (int i = 0; i < spineCount; ++i) {
    const auto entry = readSpineEntry(spineFile);
    std::string lower = entry.href;
    std::transform(lower.begin(), lower.end(), lower.begin(), [](unsigned char c) { return static_cast<char>(std::tolower(c)); });

    const auto hash = lower.find('#');
    if (hash != std::string::npos) lower.erase(hash);
    const auto query = lower.find('?');
    if (query != std::string::npos) lower.erase(query);
    const bool html = lower.size() >= 5 &&
                      (lower.rfind(".html") == lower.size() - 5 ||
                       lower.rfind(".xhtml") == lower.size() - 6 ||
                       lower.rfind(".htm") == lower.size() - 4);
    if (!html) continue;

    const auto slash = lower.find_last_of('/');
    const std::string base = slash == std::string::npos ? lower : lower.substr(slash + 1);
    // Skip common package/navigation wrappers rather than presenting them as chapters.
    if (base.find("cover") != std::string::npos || base == "nav.xhtml" || base == "nav.html" ||
        base == "toc.xhtml" || base == "toc.html" || base == "toc.htm" ||
        base.find("titlepage") != std::string::npos || base.find("title_page") != std::string::npos ||
        base.find("copyright") != std::string::npos || base.find("colophon") != std::string::npos) {
      continue;
    }
    hrefs.push_back(entry.href);
  }

  // One meaningful file cannot improve a one-entry TOC; leave the original untouched.
  if (hrefs.size() <= 1) {
    LOG_DBG("BMC", "Auto TOC: only %zu meaningful HTML spine file(s), keeping original TOC", hrefs.size());
    return false;
  }

  // Replace the weak parsed TOC, rather than appending duplicate entries to it.
  const bool flushed = !passOut || passOut->flush();
  passOut.reset();
  tocFile.close();
  if (!flushed || !Storage.openFileForWrite("BMC", cachePath + tmpTocBinFile, tocFile)) {
    LOG_ERR("BMC", "Auto TOC: could not reset TOC temp file");
    return false;
  }
  tocCount = 0;
  passOut = makeUniqueNoThrow<serialization::BufferedFileWriter>(tocFile, BUILD_IO_BUFFER_SIZE);

  int chapter = 1;
  for (const auto& href : hrefs) {
    std::string title = FsHelpers::decodeUriEscapes(href);
    const auto hash = title.find('#');
    if (hash != std::string::npos) title.erase(hash);
    const auto query = title.find('?');
    if (query != std::string::npos) title.erase(query);
    const auto slash = title.find_last_of('/');
    if (slash != std::string::npos) title.erase(0, slash + 1);
    const auto dot = title.find_last_of('.');
    if (dot != std::string::npos) title.erase(dot);
    for (char& c : title) {
      if (c == '_' || c == '-') c = ' ';
    }
    while (!title.empty() && title.front() == ' ') title.erase(title.begin());
    while (!title.empty() && title.back() == ' ') title.pop_back();
    if (title.empty()) title = "Fejezet " + std::to_string(chapter);

    createTocEntry(title, href, "", 0);
    ++chapter;
  }

  LOG_DBG("BMC", "Auto TOC: generated %zu entries from HTML/XHTML spine files", hrefs.size());
  return tocCount > 1;
}

'''
s = s.replace(insert_before, method + insert_before, 1)
# std::tolower
if '#include <cctype>' not in s:
    s = s.replace('#include <deque>\n', '#include <cctype>\n#include <deque>\n', 1)
p.write_text(s, encoding='utf-8')

# --- Epub indexing: prefer real NAV/NCX; replace only weak <=1-entry TOCs ---
p = Path('lib/Epub/Epub.cpp')
s = p.read_text(encoding='utf-8')
anchor = '''  if (!tocParsed) {
    LOG_ERR("EBP", "Warning: Could not parse any TOC format");
    // Continue anyway - book will work without TOC
  }

  if (!bookMetadataCache->endTocPass()) {'''
replacement = '''  if (bookMetadataCache->getTocCount() <= 1 && bookMetadataCache->getSpineCount() > 1) {
    LOG_DBG("EBP", "Weak TOC (%d entry), trying file-based automatic TOC from spine", bookMetadataCache->getTocCount());
    if (bookMetadataCache->replaceTocWithSpineFiles()) {
      tocParsed = true;
    }
  }

  if (!tocParsed) {
    LOG_ERR("EBP", "Warning: Could not parse any TOC format");
    // Continue anyway - book will work without TOC
  }

  if (!bookMetadataCache->endTocPass()) {'''
if anchor not in s:
    raise SystemExit('CPHUN-48 Epub TOC anchor missing')
s = s.replace(anchor, replacement, 1)
p.write_text(s, encoding='utf-8')

# Verification.
home = Path('src/activities/home/HomeActivity.cpp').read_text(encoding='utf-8')
assert 'recentBooks[0].author.c_str()' in home
rr = Path('src/components/themes/roundedraff/RoundedRaffTheme.cpp').read_text(encoding='utf-8')
assert 'wordCount >= 4' in rr
assert 'subtitle != nullptr' in rr
assert 'homeCoverHeight, 2, kCoverRadius' in rr
bmh = Path('lib/Epub/Epub/BookMetadataCache.h').read_text(encoding='utf-8')
bmc = Path('lib/Epub/Epub/BookMetadataCache.cpp').read_text(encoding='utf-8')
epub = Path('lib/Epub/Epub.cpp').read_text(encoding='utf-8')
assert 'replaceTocWithSpineFiles' in bmh and 'replaceTocWithSpineFiles' in bmc
assert 'BOOK_CACHE_VERSION = 11' in bmc
assert 'getTocCount() <= 1' in epub
assert 'replaceTocWithSpineFiles()' in epub
print('Applied CPHUN-48 home title/author/border refinements and file-based automatic TOC')
