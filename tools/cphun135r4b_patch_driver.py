from pathlib import Path
import re

patch = Path(__file__).with_name("cphun135r4b_edit_footnotes_keyboard_patch.py")
text = patch.read_text(encoding="utf-8")

# Make the generated patch idempotent where earlier stages already produced the
# desired text.
old = '''    count = text.count(old)\n    if count != 1:\n        raise SystemExit(f"CPHUN-135r4b: {path}: expected one match, found {count}: {old[:180]!r}")\n    p.write_text(text.replace(old, new, 1), encoding="utf-8")'''
new = '''    count = text.count(old)\n    if count == 0 and new in text:\n        return\n    if count != 1:\n        raise SystemExit(f"CPHUN-135r4b: {path}: expected one match, found {count}: {old[:180]!r}")\n    p.write_text(text.replace(old, new, 1), encoding="utf-8")'''
if old not in text:
    raise SystemExit("CPHUN-135r4b driver: replace_once helper not found")
text = text.replace(old, new, 1)

# The exact <a href> parser context can differ slightly after earlier CPHUN
# patches. Use a targeted regex substitution against the post-patch source.
frag_old = '''replace_once(\n    "lib/Epub/Epub/parsers/ChapterHtmlSlimParser.cpp",\n    \'\'\'      self->flushPartWordBuffer();\\n      self->nextWordContinues = true;\\n    }\\n    self->insideFootnoteLink = true;\'\'\',\n    \'\'\'      self->flushPartWordBuffer();\\n      // CPHUN-135r4b: a following noteref must not suppress hyphenation of\\n      // the lexical word immediately before the separate <a> node. The\\n      // noteref punctuation still receives zero-space attachment in ParsedText.\\n      self->nextWordContinues = false;\\n    }\\n    self->insideFootnoteLink = true;\'\'\',\n)'''
frag_new = '''p = Path("lib/Epub/Epub/parsers/ChapterHtmlSlimParser.cpp")\ns = p.read_text(encoding="utf-8")\nimport re\npat = re.compile(r'(if \\(self->partWordBufferIndex > 0\\) \\{\\n\\s*self->flushPartWordBuffer\\(\\);\\n)(?:\\s*self->nextWordContinues = true;\\n)(\\s*\\}\\n\\s*self->insideFootnoteLink = true;)')\ns2, n = pat.subn(r'\\1      // CPHUN-135r4b: a following noteref must not suppress hyphenation of\\n      // the lexical word immediately before the separate <a> node.\\n      self->nextWordContinues = false;\\n\\2', s, count=1)\nif n == 0 and "CPHUN-135r4b: a following noteref" not in s:\n    raise SystemExit("CPHUN-135r4b: footnote-link continuation block not found")\np.write_text(s2 if n else s, encoding="utf-8")'''
if frag_old not in text:
    raise SystemExit("CPHUN-135r4b driver: footnote parser patch block not found")
text = text.replace(frag_old, frag_new, 1)

# Do not change the reader-menu availability boolean here. More importantly,
# never build the whole-book footnote index merely to open the Reader menu.
# The index is built lazily only after the user selects Lábjegyzetek.
menu_block = re.compile(
    r'replace_once\(\n\s*"src/activities/reader/EpubReaderActivity\.cpp",\n'
    r'.*?!currentPageFootnotes\.empty\(\).*?!bookFootnotes\.empty\(\).*?\n\)\n', re.S)
text, n_menu = menu_block.subn('', text, count=1)
if n_menu != 1:
    raise SystemExit("CPHUN-135r4b driver: reader-menu availability patch block not found")

# Apply the feature patch first; then replace its RAM-heavy footnote routines
# with bounded-memory, SD-backed streaming implementations.
exec(compile(text, str(patch), "exec"), {"__name__": "__main__", "__file__": str(patch)})

src_path = Path("src/activities/reader/EpubReaderActivity.cpp")
s = src_path.read_text(encoding="utf-8")

# Remove eager all-book indexing from openReaderMenu().
s, n = re.subn(
    r'(void EpubReaderActivity::openReaderMenu\(const bool startOnBookTab\) \{\n\s*pendingManualTurn = 0;)\n\s*ensureBookFootnotes\(\);',
    r'\1', s, count=1)
if n != 1:
    raise SystemExit("CPHUN-135r4b: eager footnote indexing call not found")

safe_ensure = r'''void EpubReaderActivity::ensureBookFootnotes() {
  if (bookFootnotesIndexed || !epub) return;
  bookFootnotesIndexed = true;
  bookFootnotes.clear();

  // CPHUN-135r4b memory fix: never inflate an XHTML spine into RAM. Stream
  // each ZIP item to a temporary SD file, then parse it with a small rolling
  // buffer. A bounded in-memory index protects the X4 heap as well.
  constexpr size_t MAX_BOOK_FOOTNOTES = 192;
  constexpr size_t ROLLING_LIMIT = 6144;
  const std::string tmpPath = epub->getCachePath() + "/.footnotes_scan.tmp";

  for (int spine = 0; spine < epub->getSpineItemsCount() && bookFootnotes.size() < MAX_BOOK_FOOTNOTES; ++spine) {
    const auto item = epub->getSpineItem(spine);
    HalFile out;
    if (!Storage.openFileForWrite("ERS", tmpPath, out)) continue;
    const bool streamed = epub->readItemContentsToStream(item.href, out, 1024);
    out.close();
    if (!streamed) {
      Storage.remove(tmpPath.c_str());
      continue;
    }

    HalFile in;
    if (!Storage.openFileForRead("ERS", tmpPath, in)) {
      Storage.remove(tmpPath.c_str());
      continue;
    }
    std::string pending;
    pending.reserve(2048);
    uint8_t chunk[768];
    while (bookFootnotes.size() < MAX_BOOK_FOOTNOTES) {
      const int got = in.read(chunk, sizeof(chunk));
      if (got <= 0) break;
      pending.append(reinterpret_cast<const char*>(chunk), static_cast<size_t>(got));

      while (true) {
        const size_t a = pending.find("<a");
        if (a == std::string::npos) {
          if (pending.size() > 256) pending.erase(0, pending.size() - 256);
          break;
        }
        const size_t tagEnd = pending.find('>', a + 2);
        const size_t close = pending.find("</a>", a + 2);
        if (tagEnd == std::string::npos || close == std::string::npos || close < tagEnd) {
          if (a > 0) pending.erase(0, a);
          if (pending.size() > ROLLING_LIMIT) pending.erase(0, pending.size() - 512);
          break;
        }

        const std::string tag = pending.substr(a, tagEnd - a + 1);
        std::string href = htmlAttribute(tag, "href");
        const std::string label = htmlToPlain(pending.substr(tagEnd + 1, close - tagEnd - 1));
        pending.erase(0, close + 4);
        if (href.empty() || href.find('#') == std::string::npos || !looksLikeFootnoteLabel(label)) continue;

        if (href[0] == '#') {
          href = item.href + href;
        } else if (href.find("://") == std::string::npos && href.find('/') == std::string::npos) {
          const size_t slash = item.href.rfind('/');
          if (slash != std::string::npos) href = item.href.substr(0, slash + 1) + href;
        }
        const bool duplicate = std::any_of(bookFootnotes.begin(), bookFootnotes.end(), [&](const FootnoteEntry& e) {
          return href == e.href;
        });
        if (duplicate) continue;

        FootnoteEntry entry;
        std::strncpy(entry.number, label.c_str(), sizeof(entry.number) - 1);
        entry.number[sizeof(entry.number) - 1] = '\0';
        std::strncpy(entry.href, href.c_str(), sizeof(entry.href) - 1);
        entry.href[sizeof(entry.href) - 1] = '\0';
        bookFootnotes.push_back(entry);
      }
    }
    in.close();
    Storage.remove(tmpPath.c_str());
  }
}'''

safe_extract = r'''std::string EpubReaderActivity::extractFootnoteText(const std::string& href, const int sourceSpineIndex) const {
  if (!epub || href.empty()) return {};
  const size_t hash = href.find('#');
  if (hash == std::string::npos || hash + 1 >= href.size()) return {};
  const std::string anchor = href.substr(hash + 1);
  int spine = href[0] == '#' ? sourceSpineIndex : epub->resolveHrefToSpineIndex(href);
  if (spine < 0 && sourceSpineIndex >= 0) spine = sourceSpineIndex;
  if (spine < 0 || spine >= epub->getSpineItemsCount()) return {};
  const auto item = epub->getSpineItem(spine);

  // Stream the target XHTML to SD instead of asking ZipFile for one large
  // output allocation (the crash reports showed ~250 KB items on an X4 with
  // <100 KB max contiguous heap).
  const std::string tmpPath = epub->getCachePath() + "/.footnote_read.tmp";
  HalFile out;
  if (!Storage.openFileForWrite("ERS", tmpPath, out)) return {};
  const bool streamed = epub->readItemContentsToStream(item.href, out, 1024);
  out.close();
  if (!streamed) {
    Storage.remove(tmpPath.c_str());
    return {};
  }

  HalFile in;
  if (!Storage.openFileForRead("ERS", tmpPath, in)) {
    Storage.remove(tmpPath.c_str());
    return {};
  }

  const std::string needle1 = "id=\"" + anchor + "\"";
  const std::string needle2 = "id='" + anchor + "'";
  const std::string needle3 = "name=\"" + anchor + "\"";
  std::string scan;
  std::string capture;
  scan.reserve(3072);
  capture.reserve(4096);
  constexpr size_t SCAN_LIMIT = 4096;
  constexpr size_t CAPTURE_LIMIT = 12288;
  bool found = false;
  bool done = false;
  uint8_t chunk[768];

  while (!done) {
    const int got = in.read(chunk, sizeof(chunk));
    if (got <= 0) break;
    const std::string_view part(reinterpret_cast<const char*>(chunk), static_cast<size_t>(got));

    if (!found) {
      scan.append(part.data(), part.size());
      size_t pos = scan.find(needle1);
      if (pos == std::string::npos) pos = scan.find(needle2);
      if (pos == std::string::npos) pos = scan.find(needle3);
      if (pos != std::string::npos) {
        size_t begin = scan.rfind('<', pos);
        if (begin == std::string::npos) begin = pos;
        capture.assign(scan.data() + begin, scan.size() - begin);
        found = true;
        scan.clear();
      } else if (scan.size() > SCAN_LIMIT) {
        scan.erase(0, scan.size() - 512);
      }
    } else {
      capture.append(part.data(), part.size());
    }

    if (found) {
      size_t stop = std::string::npos;
      size_t suffix = 0;
      const auto consider = [&](const char* tag) {
        const size_t p = capture.find(tag);
        if (p != std::string::npos && (stop == std::string::npos || p < stop)) {
          stop = p;
          suffix = std::strlen(tag);
        }
      };
      consider("</p>");
      consider("</li>");
      consider("</div>");
      if (stop != std::string::npos) {
        capture.resize(stop + suffix);
        done = true;
      } else if (capture.size() >= CAPTURE_LIMIT) {
        capture.resize(CAPTURE_LIMIT);
        done = true;
      }
    }
  }
  in.close();
  Storage.remove(tmpPath.c_str());
  return found ? trimPlain(htmlToPlain(capture)) : std::string();
}'''

pat_ensure = re.compile(r'void EpubReaderActivity::ensureBookFootnotes\(\) \{.*?\n\}\n\n(?=std::string EpubReaderActivity::extractFootnoteText)', re.S)
s, n = pat_ensure.subn(safe_ensure + "\n\n", s, count=1)
if n != 1:
    raise SystemExit("CPHUN-135r4b: ensureBookFootnotes body not found")

pat_extract = re.compile(r'std::string EpubReaderActivity::extractFootnoteText\(const std::string& href, const int sourceSpineIndex\) const \{.*?\n\}\n\n(?=void EpubReaderActivity::openFootnotePopup)', re.S)
s, n = pat_extract.subn(safe_extract + "\n\n", s, count=1)
if n != 1:
    raise SystemExit("CPHUN-135r4b: extractFootnoteText body not found")

src_path.write_text(s, encoding="utf-8")
print("CPHUN-135r4b memory fix applied: lazy index + SD-streamed footnote parsing")
