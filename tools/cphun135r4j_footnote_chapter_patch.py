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
reader.write_text(s, encoding='utf-8')

# 2) Page-boundary footnote fix. A hyphenated source word can be represented by
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
      const std::string word(line->wordText(i));
      if (word == marker || word == ("{" + marker + "}") || word == ("[" + marker + "]") ||
          word == ("(" + marker + ")")) {
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

# 3) Preserve the existing automatic-TOC behavior and explicitly document the
#    partial-TOC guard for the next virtual-chapter layer. R4J must never replace
#    a real multi-entry TOC just to split a large spine.
epub = Path('lib/Epub/Epub.cpp')
e = epub.read_text(encoding='utf-8')
needle = '''  if (bookMetadataCache->getTocCount() <= 1 && bookMetadataCache->getSpineCount() > 1) {
    LOG_DBG("EBP", "Weak TOC (%d entry), trying file-based automatic TOC from spine", bookMetadataCache->getTocCount());
'''
replacement = '''  // CPHUN-135r4j: keep real multi-entry TOCs intact. Oversized chapters in a
  // partially structured book are handled as virtual chapter boundaries after
  // pagination; never destroy ELŐSZÓ/BEVEZETŐ-style real entries here.
  if (bookMetadataCache->getTocCount() <= 1 && bookMetadataCache->getSpineCount() > 1) {
    LOG_DBG("EBP", "Weak TOC (%d entry), trying file-based automatic TOC from spine", bookMetadataCache->getTocCount());
'''
if needle not in e:
    raise SystemExit('CPHUN-135r4j: weak Auto TOC block not found')
e = e.replace(needle, replacement, 1)
epub.write_text(e, encoding='utf-8')

print(f'CPHUN-135r4j applied: raw footnote href + visible-marker page ownership + section cache v{new_version}')
