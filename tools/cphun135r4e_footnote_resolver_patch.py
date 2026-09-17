from pathlib import Path
import re

reader_h = Path("src/activities/reader/EpubReaderActivity.h")
h = reader_h.read_text(encoding="utf-8")
old_decl = "  std::string extractFootnoteText(const std::string& href, int sourceSpineIndex) const;"
new_decl = "  std::string extractFootnoteText(const FootnoteEntry& footnote, int sourceSpineIndex) const;"
if old_decl in h:
    h = h.replace(old_decl, new_decl, 1)
elif new_decl not in h:
    raise SystemExit("CPHUN-135r4e: extractFootnoteText declaration not found")
reader_h.write_text(h, encoding="utf-8")

reader = Path("src/activities/reader/EpubReaderActivity.cpp")
s = reader.read_text(encoding="utf-8")

# Callers need the marker as well as href for fallback resolution and diagnostics.
s = s.replace("extractFootnoteText(footnote.href, sourceSpineIndex)",
              "extractFootnoteText(footnote, sourceSpineIndex)")
s = s.replace("extractFootnoteText(note.href, sourceSpine)",
              "extractFootnoteText(note, sourceSpine)")

resolver = r'''std::string EpubReaderActivity::extractFootnoteText(const FootnoteEntry& footnote, const int sourceSpineIndex) const {
  if (!epub || footnote.href[0] == '\0') return {};

  const std::string href(footnote.href);
  const std::string marker(footnote.number);
  const size_t hash = href.find('#');
  const std::string hrefPath = hash == std::string::npos ? href : href.substr(0, hash);
  const std::string fragment = hash == std::string::npos ? std::string() : href.substr(hash + 1);

  std::string sourceHref;
  if (sourceSpineIndex >= 0 && sourceSpineIndex < epub->getSpineItemsCount()) {
    sourceHref = epub->getSpineItem(sourceSpineIndex).href;
  }

  auto normalizePath = [](const std::string& baseFile, const std::string& relative) {
    if (relative.empty()) return baseFile;
    if (relative.find("://") != std::string::npos) return relative;
    std::string joined;
    if (!relative.empty() && relative[0] == '/') {
      joined = relative.substr(1);
    } else {
      const size_t slash = baseFile.rfind('/');
      joined = slash == std::string::npos ? relative : baseFile.substr(0, slash + 1) + relative;
    }
    std::vector<std::string> parts;
    size_t p = 0;
    while (p <= joined.size()) {
      const size_t q = joined.find('/', p);
      const std::string part = joined.substr(p, q == std::string::npos ? std::string::npos : q - p);
      if (part == "..") {
        if (!parts.empty()) parts.pop_back();
      } else if (!part.empty() && part != ".") {
        parts.push_back(part);
      }
      if (q == std::string::npos) break;
      p = q + 1;
    }
    std::string out;
    for (size_t i = 0; i < parts.size(); ++i) {
      if (i) out += '/';
      out += parts[i];
    }
    return out;
  };

  const std::string targetHref = normalizePath(sourceHref, hrefPath);
  std::string errorCode;
  std::string diagContext;

  auto writeDiagnostic = [&](const char* code) {
    const size_t slash = bookPath.find_last_of("/\\");
    const std::string dir = slash == std::string::npos ? std::string() : bookPath.substr(0, slash + 1);
    std::string tag = fragment.empty() ? "unknown" : fragment;
    for (char& c : tag) {
      if (!(std::isalnum(static_cast<unsigned char>(c)) || c == '-' || c == '_')) c = '_';
    }
    if (tag.size() > 40) tag.resize(40);
    const std::string logPath = dir + "footnote_error_" + std::to_string(millis()) + "_" + tag + ".txt";
    std::string log;
    log.reserve(2048);
    log += "CrossPoint Footnote Diagnostic\nFormat version: 1\n\n";
    log += "Firmware: CPHUN-260917-135R4E-EXP\n";
    log += "Book: " + epub->getTitle() + "\n";
    log += "EPUB: " + bookPath + "\n";
    log += "Source spine: " + std::to_string(sourceSpineIndex) + "\n";
    log += "Source XHTML: " + sourceHref + "\n";
    log += "Marker: " + marker + "\n";
    log += "Original href: " + href + "\n";
    log += "Resolved target: " + targetHref + "\n";
    log += "Fragment: " + fragment + "\n\n";
    log += "Error: ";
    log += code;
    log += "\n\nContext (max 1024 bytes):\n";
    if (diagContext.size() > 1024) diagContext.resize(1024);
    log += diagContext;
    log += "\n";
    if (log.size() > 8192) log.resize(8192);
    HalFile out;
    if (Storage.openFileForWrite("ERS", logPath, out)) {
      out.write(reinterpret_cast<const uint8_t*>(log.data()), log.size());
      out.close();
      LOG_DBG("ERS", "Footnote diagnostic written: %s", logPath.c_str());
    }
  };

  if (targetHref.empty() || targetHref.find("://") != std::string::npos) {
    writeDiagnostic("FOOTNOTE_TARGET_NOT_FOUND");
    return {};
  }

  const std::string tmpPath = epub->getCachePath() + "/.footnote_resolver.tmp";
  HalFile out;
  if (!Storage.openFileForWrite("ERS", tmpPath, out)) {
    writeDiagnostic("FOOTNOTE_TARGET_NOT_FOUND");
    return {};
  }
  const bool streamed = epub->readItemContentsToStream(targetHref, out, 1024);
  out.close();
  if (!streamed) {
    Storage.remove(tmpPath.c_str());
    writeDiagnostic("FOOTNOTE_TARGET_NOT_FOUND");
    return {};
  }

  auto readNeedle = [&](const std::vector<std::string>& needles, bool fragmentSearch) -> std::string {
    HalFile in;
    if (!Storage.openFileForRead("ERS", tmpPath, in)) return {};
    std::string scan;
    std::string capture;
    scan.reserve(12288);
    capture.reserve(12288);
    constexpr size_t SCAN_LIMIT = 12288;
    constexpr size_t CAPTURE_LIMIT = 16384;
    uint8_t chunk[768];
    bool found = false;
    std::string blockTag;
    std::string activeNeedle;

    while (true) {
      const int got = in.read(chunk, sizeof(chunk));
      if (got <= 0) break;
      if (diagContext.size() < 1024) {
        const size_t take = std::min<size_t>(static_cast<size_t>(got), 1024 - diagContext.size());
        diagContext.append(reinterpret_cast<const char*>(chunk), take);
      }
      if (!found) {
        scan.append(reinterpret_cast<const char*>(chunk), static_cast<size_t>(got));
        size_t pos = std::string::npos;
        for (const auto& needle : needles) {
          if (needle.empty()) continue;
          const size_t candidate = scan.find(needle);
          if (candidate != std::string::npos && (pos == std::string::npos || candidate < pos)) {
            pos = candidate;
            activeNeedle = needle;
          }
        }
        if (pos == std::string::npos) {
          if (scan.size() > SCAN_LIMIT) scan.erase(0, scan.size() - 2048);
          continue;
        }

        size_t begin = pos;
        struct Block { const char* open; const char* close; };
        constexpr Block blocks[] = {{"<dl", "dl"}, {"<aside", "aside"}, {"<section", "section"},
                                    {"<li", "li"}, {"<div", "div"}, {"<p", "p"}};
        size_t best = std::string::npos;
        for (const auto& b : blocks) {
          const size_t bp = scan.rfind(b.open, pos);
          if (bp != std::string::npos && (best == std::string::npos || bp > best)) {
            best = bp;
            blockTag = b.close;
          }
        }
        if (best != std::string::npos) begin = best;
        else {
          const size_t lt = scan.rfind('<', pos);
          if (lt != std::string::npos) begin = lt;
        }
        capture.assign(scan.data() + begin, scan.size() - begin);
        found = true;
        scan.clear();
      } else {
        capture.append(reinterpret_cast<const char*>(chunk), static_cast<size_t>(got));
      }

      if (!found) continue;
      if (capture.size() > CAPTURE_LIMIT) capture.resize(CAPTURE_LIMIT);

      size_t stop = std::string::npos;
      size_t suffix = 0;
      if (!blockTag.empty() && blockTag != "p") {
        const std::string close = "</" + blockTag + ">";
        stop = capture.find(close);
        suffix = close.size();
      } else if (blockTag == "p") {
        // Some Calibre footnotes (e.g. id_Footnote_N) continue through several
        // paragraphs. For those, stop at the next note anchor instead of the
        // first </p>. Other p-based notes remain one bounded paragraph.
        bool multiParagraph = false;
        std::string family;
        if (fragment.rfind("id_Footnote_", 0) == 0) family = "id_Footnote_";
        else if (fragment.rfind("Footnote_", 0) == 0) family = "Footnote_";
        if (!family.empty()) {
          multiParagraph = true;
          const size_t first = capture.find(activeNeedle);
          size_t next = capture.find("id=\"" + family, first == std::string::npos ? 1 : first + activeNeedle.size());
          const size_t next2 = capture.find("id='" + family, first == std::string::npos ? 1 : first + activeNeedle.size());
          if (next == std::string::npos || (next2 != std::string::npos && next2 < next)) next = next2;
          if (next != std::string::npos) {
            const size_t pbegin = capture.rfind("<p", next);
            stop = pbegin == std::string::npos ? next : pbegin;
            suffix = 0;
          }
        }
        if (!multiParagraph) {
          stop = capture.find("</p>");
          suffix = 4;
        }
      }

      if (stop != std::string::npos) {
        capture.resize(stop + suffix);
        in.close();
        return trimPlain(htmlToPlain(capture));
      }
      if (capture.size() >= CAPTURE_LIMIT) {
        in.close();
        return trimPlain(htmlToPlain(capture));
      }
    }
    in.close();
    if (found && !capture.empty()) return trimPlain(htmlToPlain(capture));
    return {};
  };

  std::vector<std::string> anchorNeedles;
  if (!fragment.empty()) {
    anchorNeedles.push_back("id=\"" + fragment + "\"");
    anchorNeedles.push_back("id='" + fragment + "'");
    anchorNeedles.push_back("name=\"" + fragment + "\"");
    anchorNeedles.push_back("name='" + fragment + "'");
    std::string text = readNeedle(anchorNeedles, true);
    if (!text.empty()) {
      Storage.remove(tmpPath.c_str());
      return text;
    }
    errorCode = "FOOTNOTE_ANCHOR_NOT_FOUND";
  }

  // Marker fallback for EPUBs without a usable fragment. Exact visible marker
  // is tried first, then common numeric note-id families.
  std::vector<std::string> markerNeedles;
  if (!marker.empty()) markerNeedles.push_back(marker);
  std::string digits;
  for (const char c : marker) if (c >= '0' && c <= '9') digits += c;
  if (!digits.empty()) {
    markerNeedles.push_back(">" + digits + "<");
    markerNeedles.push_back("{" + digits + "}");
    markerNeedles.push_back("[" + digits + "]");
    markerNeedles.push_back("id=\"note_" + digits + "\"");
    markerNeedles.push_back("id=\"Footnote_" + digits + "\"");
    markerNeedles.push_back("id=\"footnote-" + digits + "\"");
    markerNeedles.push_back("id=\"n" + digits + "\"");
  }
  if (!markerNeedles.empty()) {
    std::string text = readNeedle(markerNeedles, false);
    if (!text.empty()) {
      Storage.remove(tmpPath.c_str());
      return text;
    }
  }

  Storage.remove(tmpPath.c_str());
  writeDiagnostic(errorCode.empty() ? "FOOTNOTE_UNSUPPORTED_STRUCTURE" : errorCode.c_str());
  return {};
}'''

pat = re.compile(
    r'std::string EpubReaderActivity::extractFootnoteText\(const std::string& href, const int sourceSpineIndex\) const \{.*?\n\}\n\n(?=void EpubReaderActivity::openFootnotePopup)',
    re.S,
)
s, n = pat.subn(lambda m: resolver + "\n\n", s, count=1)
if n != 1:
    raise SystemExit(f"CPHUN-135r4e: old extractFootnoteText body not found: {n}")

# Restore the Reader-menu item without reintroducing the synchronous whole-book
# scan. The action itself remains current-page/bounded in the R4D guard.
old_visible = "SETTINGS.orientation, !currentPageFootnotes.empty(), !cachedBookmarks.empty(), startOnBookTab),"
new_visible = "SETTINGS.orientation, true, !cachedBookmarks.empty(), startOnBookTab),"
if old_visible in s:
    s = s.replace(old_visible, new_visible, 1)
elif new_visible not in s:
    raise SystemExit("CPHUN-135r4e: Footnotes menu visibility expression not found")

# Unsupported structures must never masquerade as dictionary failures or crash.
s = s.replace('if (text.empty()) text = "A lábjegyzet szövege nem olvasható.";',
              'if (text.empty()) text = "A lábjegyzet tartalma nem olvasható ebben az EPUB-ban.";')

# Semantic safety checks.
if "ensureBookFootnotes();\n      openFootnotesList(true, true);" in s:
    raise SystemExit("CPHUN-135r4e: synchronous whole-book footnote scan is reachable from Reader menu")
if "readItemContentsToStream(targetHref" not in s:
    raise SystemExit("CPHUN-135r4e: direct target-XHTML streaming resolver missing")
if "FOOTNOTE_ANCHOR_NOT_FOUND" not in s or "CrossPoint Footnote Diagnostic" not in s:
    raise SystemExit("CPHUN-135r4e: diagnostic logging missing")

reader.write_text(s, encoding="utf-8")
print("CPHUN-135r4e Footnote Resolver v1 applied: href target + anchor/marker fallback + diagnostic log + visible menu")
