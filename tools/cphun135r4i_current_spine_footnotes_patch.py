from pathlib import Path
import re

p = Path('src/activities/reader/EpubReaderActivity.cpp')
s = p.read_text(encoding='utf-8')

safe_ensure = r'''void EpubReaderActivity::ensureBookFootnotes() {
  if (bookFootnotesIndexed || !epub) return;
  bookFootnotesIndexed = true;
  bookFootnotes.clear();

  // CPHUN-135r4i: SAFE CURRENT-SPINE INDEX ONLY.
  // Never walk the whole EPUB from the Reader menu. R4G reproduced an X4
  // abort while the synchronous whole-book scan reached Michelangelo note 132.
  // One spine/XHTML is bounded enough for an interactive menu operation while
  // still allowing notes elsewhere in the current chapter to be listed.
  constexpr size_t MAX_SPINE_FOOTNOTES = 160;
  constexpr size_t ROLLING_LIMIT = 6144;
  if (currentSpineIndex < 0 || currentSpineIndex >= epub->getSpineItemsCount()) return;

  const auto item = epub->getSpineItem(currentSpineIndex);
  const std::string tmpPath = epub->getCachePath() + "/.footnotes_spine_scan.tmp";

  auto lowerAscii = [](std::string v) {
    for (char& c : v) c = static_cast<char>(std::tolower(static_cast<unsigned char>(c)));
    return v;
  };

  auto isForwardNoteref = [&](const std::string& tag, const std::string& href, const std::string& label) {
    if (href.empty() || !looksLikeFootnoteLabel(label)) return false;
    const std::string t = lowerAscii(tag);
    const std::string h = lowerAscii(href);
    if (t.find("noteref") != std::string::npos || t.find("doc-noteref") != std::string::npos) return true;
    if (t.find("footnote") != std::string::npos || t.find("endnote") != std::string::npos) return true;

    const size_t hash = h.find('#');
    const std::string path = hash == std::string::npos ? h : h.substr(0, hash);
    const std::string frag = hash == std::string::npos ? std::string() : h.substr(hash + 1);
    if (path.find("footnote") != std::string::npos || path.find("endnote") != std::string::npos ||
        path.find("notes.") != std::string::npos || path.find("/notes") != std::string::npos ||
        path.find("note.") != std::string::npos) return true;
    if (frag.find("footnote") != std::string::npos || frag.find("endnote") != std::string::npos ||
        frag.rfind("note_", 0) == 0 || frag.rfind("note-", 0) == 0) return true;
    return false;
  };

  HalFile out;
  if (!Storage.openFileForWrite("ERS", tmpPath, out)) return;
  const bool streamed = epub->readItemContentsToStream(item.href, out, 1024);
  out.close();
  if (!streamed) {
    Storage.remove(tmpPath.c_str());
    return;
  }

  HalFile in;
  if (!Storage.openFileForRead("ERS", tmpPath, in)) {
    Storage.remove(tmpPath.c_str());
    return;
  }

  std::string pending;
  pending.reserve(2048);
  uint8_t chunk[768];
  while (bookFootnotes.size() < MAX_SPINE_FOOTNOTES) {
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
      if (!isForwardNoteref(tag, href, label)) continue;

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
  LOG_DBG("ERS", "Current-spine footnote index: spine=%d, entries=%u", currentSpineIndex,
          static_cast<unsigned>(bookFootnotes.size()));
}'''

pat = re.compile(r'void EpubReaderActivity::ensureBookFootnotes\(\) \{.*?\n\}\n\n(?=std::string EpubReaderActivity::extractFootnoteText)', re.S)
s, n = pat.subn(safe_ensure + "\n\n", s, count=1)
if n != 1:
    raise SystemExit(f'CPHUN-135r4i: ensureBookFootnotes body not found: {n}')

old_case = '''    case EpubReaderMenuActivity::MenuAction::FOOTNOTES: {
      // CPHUN-135r4h crash fix: never synchronously scan the whole EPUB from
      // the Reader menu. On X4, ensureBookFootnotes() can exhaust resources
      // while walking many spine items (reproduced with Michelangelo around
      // id_Footnote_132). Use only the already parsed current-page index here.
      openFootnotesList(false, true);
      break;
    }'''
new_case = '''    case EpubReaderMenuActivity::MenuAction::FOOTNOTES: {
      // CPHUN-135r4i: rebuild a bounded index for the CURRENT spine only.
      // Keep the current-page list as fallback for already parsed references.
      bookFootnotesIndexed = false;
      ensureBookFootnotes();
      if (!bookFootnotes.empty()) {
        openFootnotesList(true, true);
      } else {
        openFootnotesList(false, true);
      }
      break;
    }'''
if old_case in s:
    s = s.replace(old_case, new_case, 1)
elif new_case not in s:
    raise SystemExit('CPHUN-135r4i: R4H FOOTNOTES menu case not found')

p.write_text(s, encoding='utf-8')
print('CPHUN-135r4i applied: current-spine-only footnote menu index')
