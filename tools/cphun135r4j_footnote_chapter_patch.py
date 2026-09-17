from pathlib import Path
import re

# CPHUN-135r4j
# 1) Keep scanned footnote hrefs source-relative. The R4E resolver is the ONE place
#    that resolves them against the source spine; pre-resolving in R4I caused paths
#    such as Ops/notes.html to become Ops/Ops/notes.html.
reader = Path('src/activities/reader/EpubReaderActivity.cpp')
s = reader.read_text(encoding='utf-8')
old = '''      if (href[0] == '#') {
        href = item.href + href;
      } else if (href.find("://") == std::string::npos && href.find('/') == std::string::npos) {
        const size_t slash = item.href.rfind('/');
        if (slash != std::string::npos) href = item.href.substr(0, slash + 1) + href;
      }

'''
if old not in s:
    raise SystemExit('CPHUN-135r4j: R4I href pre-normalization block not found')
s = s.replace(old, '''      // CPHUN-135r4j: preserve the href exactly as it appears in the source XHTML.
      // extractFootnoteText() resolves it once, relative to currentSpineIndex.

''', 1)

# 2) Non-destructive virtual chapter subdivisions for an oversized current spine.
# Keep the EPUB's real TOC entries and insert virtual rows directly after the
# current real chapter. Boundaries are selected from the Section paragraph LUT,
# so a virtual chapter never starts in the middle of a sentence/paragraph.
old_chapter = '''    case EpubReaderMenuActivity::MenuAction::SELECT_CHAPTER: {
      const int spineIdx = currentSpineIndex;
      // Release the section while the chapter list is up (mirrors the
      // TEXT_SETTINGS path): picking a chapter resets it anyway, and its
      // tens-of-KB footprint is the difference between the chapter list
      // holding its CJK glyph arena (RAM-only repaints) and re-reading
      // glyphs from SD on every row step. Cancel restores via the same
      // cached-position rebuild TEXT_SETTINGS uses.
      {
        RenderLock lock;
        if (section) {
          rememberCurrentContentOffset();
          cachedSpineIndex = currentSpineIndex;
          cachedChapterTotalPageCount = section->pageCount;
          nextPageNumber = section->currentPage;
        }
        section.reset();
      }
      startActivityForResult(
          std::make_unique<EpubReaderChapterSelectionActivity>(renderer, mappedInput, epub, spineIdx),
          [this](const ActivityResult& result) {
            if (result.isCancelled) {
              openReaderMenu();
              return;
            }
            const auto& chapterResult = std::get<ChapterResult>(result.data);
            RenderLock lock;
            clearDeferredReposition();
            currentSpineIndex = chapterResult.spineIndex;
            pendingAnchor = chapterResult.anchor;
            nextPageNumber = 0;
            section.reset();
            requestUpdate();
          });
      break;
    }'''
new_chapter = '''    case EpubReaderMenuActivity::MenuAction::SELECT_CHAPTER: {
      const int spineIdx = currentSpineIndex;
      std::vector<EpubReaderChapterSelectionActivity::VirtualChapter> virtualChapters;

      // CPHUN-135r4j: subdivide only a genuinely long rendered section. Roughly
      // 12 pages is the target size, but we advance to the first page whose
      // paragraph index differs from the preceding page. If there is no safe
      // paragraph boundary in the next 12 pages, do not cut there at all.
      // This preserves complete sentences and the EPUB's original TOC.
      if (section && section->pageCount >= 24) {
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
          const uint16_t searchEnd = std::min<uint16_t>(section->pageCount - 1, target + TARGET_PAGES);
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
      }

      // Release the section while the chapter list is up (mirrors the
      // TEXT_SETTINGS path): picking a chapter resets it anyway, and its
      // tens-of-KB footprint is the difference between the chapter list
      // holding its CJK glyph arena (RAM-only repaints) and re-reading
      // glyphs from SD on every row step. Cancel restores via the same
      // cached-position rebuild TEXT_SETTINGS uses.
      {
        RenderLock lock;
        if (section) {
          rememberCurrentContentOffset();
          cachedSpineIndex = currentSpineIndex;
          cachedChapterTotalPageCount = section->pageCount;
          nextPageNumber = section->currentPage;
        }
        section.reset();
      }
      startActivityForResult(
          std::make_unique<EpubReaderChapterSelectionActivity>(renderer, mappedInput, epub, spineIdx,
                                                                std::move(virtualChapters)),
          [this](const ActivityResult& result) {
            if (result.isCancelled) {
              openReaderMenu();
              return;
            }
            const auto& chapterResult = std::get<ChapterResult>(result.data);
            RenderLock lock;
            clearDeferredReposition();
            currentSpineIndex = chapterResult.spineIndex;
            constexpr const char* VIRTUAL_PAGE_PREFIX = "__cphun_page_";
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
            section.reset();
            requestUpdate();
          });
      break;
    }'''
if old_chapter not in s:
    raise SystemExit('CPHUN-135r4j: SELECT_CHAPTER block not found')
s = s.replace(old_chapter, new_chapter, 1)
reader.write_text(s, encoding='utf-8')

# 3) Page-boundary footnote fix. A hyphenated source word can be represented by
#    fragments on two rendered lines. Counting rendered line words can therefore
#    reach the source-word index one page too early. Prefer the line that actually
#    contains the visible noteref marker; retain the word-index fallback only for
#    unusual links whose label was transformed by layout.
parser = Path('lib/Epub/Epub/parsers/ChapterHtmlSlimParser.cpp')
p = parser.read_text(encoding='utf-8')
old = '''  // Track cumulative words to assign footnotes to the page containing their anchor
  wordsExtractedInBlock += line->wordCount();
  auto footnoteIt = pendingFootnotes.begin();
  while (footnoteIt != pendingFootnotes.end() && footnoteIt->first <= wordsExtractedInBlock) {
    currentPage->addFootnote(footnoteIt->second.number, footnoteIt->second.href);
    ++footnoteIt;
  }
  pendingFootnotes.erase(pendingFootnotes.begin(), footnoteIt);
'''
new = '''  // CPHUN-135r4j: assign a noteref to the page where its marker is actually
  // rendered. A hyphenated source word can split into fragments across pages,
  // making rendered-word counting advance before the following {N}/[N] marker.
  // Exact visible-marker matching wins; word-index remains a fallback for EPUBs
  // whose noteref label is not preserved as a standalone rendered token.
  auto markerOnLine = [&](const FootnoteEntry& fn) {
    if (fn.number[0] == '\\0') return false;
    const std::string marker(fn.number);
    for (uint16_t i = 0; i < line->wordCount(); ++i) {
      const std::string renderedToken(line->wordText(i));
      if (renderedToken == marker || renderedToken == ("{" + marker + "}") || renderedToken == ("[" + marker + "]") ||
          renderedToken == ("(" + marker + ")")) {
        return true;
      }
    }
    return false;
  };

  for (auto it = pendingFootnotes.begin(); it != pendingFootnotes.end();) {
    if (markerOnLine(it->second)) {
      currentPage->addFootnote(it->second.number, it->second.href);
      it = pendingFootnotes.erase(it);
    } else {
      ++it;
    }
  }

  wordsExtractedInBlock += line->wordCount();
  auto footnoteIt = pendingFootnotes.begin();
  while (footnoteIt != pendingFootnotes.end()) {
    // Do not let the fallback steal an ordinary numeric/bracketed marker from
    // the following page merely because a hyphenated word produced two visual
    // fragments. Numeric marker links wait for markerOnLine().
    std::string label(footnoteIt->second.number);
    bool markerLike = !label.empty();
    for (char c : label) {
      if (!(c >= '0' && c <= '9') && c != '{' && c != '}' && c != '[' && c != ']' && c != '(' && c != ')') {
        markerLike = false;
        break;
      }
    }
    if (markerLike || footnoteIt->first > wordsExtractedInBlock) {
      ++footnoteIt;
      continue;
    }
    currentPage->addFootnote(footnoteIt->second.number, footnoteIt->second.href);
    footnoteIt = pendingFootnotes.erase(footnoteIt);
  }
'''
if old not in p:
    raise SystemExit('CPHUN-135r4j: footnote page-assignment block not found')
p = p.replace(old, new, 1)
parser.write_text(p, encoding='utf-8')

# Cached Page::footnotes data changes semantics, so invalidate old section caches.
section = Path('lib/Epub/Epub/Section.cpp')
sec = section.read_text(encoding='utf-8')
m = re.search(r'constexpr uint8_t SECTION_FILE_VERSION = (\d+);', sec)
if not m:
    raise SystemExit('CPHUN-135r4j: SECTION_FILE_VERSION not found')
old_version = int(m.group(1))
new_version = old_version + 1
sec = sec[:m.start()] + f'constexpr uint8_t SECTION_FILE_VERSION = {new_version};' + sec[m.end():]
section.write_text(sec, encoding='utf-8')

# 4) Chapter-selection UI: insert the virtual subdivisions immediately after
#    the current real TOC row. They navigate by a private page pseudo-anchor,
#    which EpubReaderActivity converts to pendingPageJump above.
hdr = Path('src/activities/reader/EpubReaderChapterSelectionActivity.h')
h = hdr.read_text(encoding='utf-8')
h = h.replace('#include <string>\n', '#include <string>\n#include <vector>\n', 1)
h = h.replace('''class EpubReaderChapterSelectionActivity final : public UiListActivity {
  std::shared_ptr<Epub> epub;
  int currentSpineIndex = 0;
''', '''class EpubReaderChapterSelectionActivity final : public UiListActivity {
 public:
  struct VirtualChapter {
    std::string title;
    int spineIndex = 0;
    uint16_t page = 0;
  };

 private:
  std::shared_ptr<Epub> epub;
  int currentSpineIndex = 0;
  std::vector<VirtualChapter> virtualChapters;
  int virtualInsertAfter = -1;
''', 1)
h = h.replace('''  // Total TOC items count
  int listCount() const override { return epub ? epub->getTocItemsCount() : 0; }
''', '''  // Total TOC items count, plus non-destructive virtual subdivisions for the
  // current oversized spine.
  int listCount() const override {
    return epub ? epub->getTocItemsCount() + static_cast<int>(virtualChapters.size()) : 0;
  }
  int realTocIndexForRow(int row) const;
  int virtualIndexForRow(int row) const;
''', 1)
h = h.replace('''  explicit EpubReaderChapterSelectionActivity(GfxRenderer& renderer, MappedInputManager& mappedInput,
                                              const std::shared_ptr<Epub>& epub, int currentSpineIndex);
''', '''  explicit EpubReaderChapterSelectionActivity(GfxRenderer& renderer, MappedInputManager& mappedInput,
                                              const std::shared_ptr<Epub>& epub, int currentSpineIndex,
                                              std::vector<VirtualChapter> virtualChapters = {});
''', 1)
hdr.write_text(h, encoding='utf-8')

cpp = Path('src/activities/reader/EpubReaderChapterSelectionActivity.cpp')
c = cpp.read_text(encoding='utf-8')
c = c.replace('''EpubReaderChapterSelectionActivity::EpubReaderChapterSelectionActivity(GfxRenderer& renderer,
                                                                       MappedInputManager& mappedInput,
                                                                       const std::shared_ptr<Epub>& epub,
                                                                       const int currentSpineIndex)
    : UiListActivity("EpubReaderChapterSelection", renderer, mappedInput),
      epub(epub),
      currentSpineIndex(currentSpineIndex) {}
''', '''EpubReaderChapterSelectionActivity::EpubReaderChapterSelectionActivity(
    GfxRenderer& renderer, MappedInputManager& mappedInput, const std::shared_ptr<Epub>& epub,
    const int currentSpineIndex, std::vector<VirtualChapter> virtualChapters)
    : UiListActivity("EpubReaderChapterSelection", renderer, mappedInput),
      epub(epub),
      currentSpineIndex(currentSpineIndex),
      virtualChapters(std::move(virtualChapters)) {
  virtualInsertAfter = epub ? epub->getTocIndexForSpineIndex(currentSpineIndex) : -1;
}

int EpubReaderChapterSelectionActivity::virtualIndexForRow(const int row) const {
  if (virtualInsertAfter < 0 || virtualChapters.empty()) return -1;
  const int first = virtualInsertAfter + 1;
  const int index = row - first;
  return index >= 0 && index < static_cast<int>(virtualChapters.size()) ? index : -1;
}

int EpubReaderChapterSelectionActivity::realTocIndexForRow(const int row) const {
  if (virtualInsertAfter < 0 || virtualChapters.empty()) return row;
  const int firstAfterVirtual = virtualInsertAfter + 1 + static_cast<int>(virtualChapters.size());
  return row >= firstAfterVirtual ? row - static_cast<int>(virtualChapters.size()) : row;
}
''', 1)

old_window = '''  for (int i = 0; i < windowCount; i++) {
    const auto tocItem = epub->getTocItem(clamped + i);
    std::string indent(tocItem.level > 0 ? (tocItem.level - 1) * 2 : 0, ' ');
    windowLabels[i] = indent + tocItem.title;
    fui::ListItem item;
    item.label = windowLabels[i].c_str();
    item.actionValue = static_cast<int16_t>(clamped + i);
    windowItems[i] = item;
  }
'''
new_window = '''  for (int i = 0; i < windowCount; i++) {
    const int row = clamped + i;
    const int virtualIndex = virtualIndexForRow(row);
    if (virtualIndex >= 0) {
      windowLabels[i] = "  " + virtualChapters[virtualIndex].title;
    } else {
      const auto tocItem = epub->getTocItem(realTocIndexForRow(row));
      std::string indent(tocItem.level > 0 ? (tocItem.level - 1) * 2 : 0, ' ');
      windowLabels[i] = indent + tocItem.title;
    }
    fui::ListItem item;
    item.label = windowLabels[i].c_str();
    item.actionValue = static_cast<int16_t>(row);
    windowItems[i] = item;
  }
'''
if old_window not in c:
    raise SystemExit('CPHUN-135r4j: chapter window block not found')
c = c.replace(old_window, new_window, 1)

old_activate = '''  nav.selected = index;
  const auto tocItem = epub->getTocItem(index);
  if (tocItem.spineIndex == -1) {
    ActivityResult result;
    result.isCancelled = true;
    setResult(std::move(result));
    finish();
  } else {
    setResult(ChapterResult{tocItem.spineIndex, tocItem.anchor});
    finish();
  }
'''
new_activate = '''  nav.selected = index;
  const int virtualIndex = virtualIndexForRow(index);
  if (virtualIndex >= 0) {
    const auto& v = virtualChapters[virtualIndex];
    setResult(ChapterResult{v.spineIndex, "__cphun_page_" + std::to_string(v.page)});
    finish();
    return;
  }
  const auto tocItem = epub->getTocItem(realTocIndexForRow(index));
  if (tocItem.spineIndex == -1) {
    ActivityResult result;
    result.isCancelled = true;
    setResult(std::move(result));
    finish();
  } else {
    setResult(ChapterResult{tocItem.spineIndex, tocItem.anchor});
    finish();
  }
'''
if old_activate not in c:
    raise SystemExit('CPHUN-135r4j: chapter activate block not found')
c = c.replace(old_activate, new_activate, 1)
cpp.write_text(c, encoding='utf-8')

# Preserve the existing weak-TOC generator: do NOT replace real multi-entry TOCs.
epub = Path('lib/Epub/Epub.cpp')
e = epub.read_text(encoding='utf-8')
needle = '''  if (bookMetadataCache->getTocCount() <= 1 && bookMetadataCache->getSpineCount() > 1) {
    LOG_DBG("EBP", "Weak TOC (%d entry), trying file-based automatic TOC from spine", bookMetadataCache->getTocCount());
'''
replacement = '''  // CPHUN-135r4j: keep real multi-entry TOCs intact. Oversized chapters in a
  // partially structured book are exposed as virtual paragraph-safe chapter
  // boundaries by EpubReaderChapterSelectionActivity.
  if (bookMetadataCache->getTocCount() <= 1 && bookMetadataCache->getSpineCount() > 1) {
    LOG_DBG("EBP", "Weak TOC (%d entry), trying file-based automatic TOC from spine", bookMetadataCache->getTocCount());
'''
if needle not in e:
    raise SystemExit('CPHUN-135r4j: weak Auto TOC block not found')
e = e.replace(needle, replacement, 1)
epub.write_text(e, encoding='utf-8')

print(f'CPHUN-135r4j applied: raw href + visible marker ownership + paragraph-safe virtual chapters + section cache v{new_version}')
