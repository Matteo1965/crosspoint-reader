from pathlib import Path

# CPHUN-135r4k2f4
# Resolve bounded footnote target XHTML with one-shot ZIP inflate instead of
# streaming inflate. Streaming needs a separate 32 KB history window; the
# one-shot path uses the output buffer itself as history. This is deliberately
# limited to small/medium note targets to avoid reintroducing whole-book RAM use.

cpp = Path("src/activities/reader/EpubReaderActivity.cpp")
s = cpp.read_text(encoding="utf-8")

old = '''  diagnosticTargetSizeOk = epub->getItemSize(targetHref, &diagnosticTargetSize);
  if (!diagnosticTargetSizeOk) {
    writeDiagnostic("EPUB_ITEM_SIZE_FAILED");
    return {};
  }

  const std::string tmpPath = epub->getCachePath() + "/.footnote_resolver.tmp";
  HalFile out;
  if (!Storage.openFileForWrite("ERS", tmpPath, out)) {
    writeDiagnostic("TEMP_FILE_OPEN_FAILED");
    return {};
  }

  const bool streamed = epub->readItemContentsToStream(targetHref, out, 1024);
  out.flush();
  out.close();
  if (!streamed) {
    Storage.remove(tmpPath.c_str());
    writeDiagnostic("EPUB_ZIP_STREAM_FAILED");
    return {};
  }
'''
new = '''  diagnosticTargetSizeOk = epub->getItemSize(targetHref, &diagnosticTargetSize);
  if (!diagnosticTargetSizeOk) {
    writeDiagnostic("EPUB_ITEM_SIZE_FAILED");
    return {};
  }

  // CPHUN-135r4k2f4: bounded one-shot inflate for note targets.
  // readFileToStream() uses InflateStream::init(true), which allocates a
  // separate ~32 KB history window. readItemContentsToBytes() uses one-shot
  // inflate and the output buffer itself as the history area.
  constexpr size_t MAX_FOOTNOTE_TARGET_BYTES = 96u * 1024u;
  if (diagnosticTargetSize == 0 || diagnosticTargetSize > MAX_FOOTNOTE_TARGET_BYTES) {
    writeDiagnostic("FOOTNOTE_TARGET_TOO_LARGE");
    return {};
  }

  size_t targetSize = 0;
  uint8_t* targetBytes = epub->readItemContentsToBytes(targetHref, &targetSize, true);
  if (!targetBytes) {
    writeDiagnostic("EPUB_ZIP_ONESHOT_FAILED");
    return {};
  }
  std::string targetHtml(reinterpret_cast<char*>(targetBytes), targetSize);
  free(targetBytes);
'''

if old not in s:
    raise SystemExit("R4K2F4: R4K2F3 resolver I/O block not found")
s = s.replace(old, new, 1)

# Replace temp-file-based readNeedle with direct bounded-memory search.
start = s.find('  bool tempReadFailed = false;\\n  auto readNeedle =')
if start < 0:
    raise SystemExit("R4K2F4: temp-file readNeedle start not found")
end_marker = '\\n  std::vector<std::string> anchorNeedles;'
end = s.find(end_marker, start)
if end < 0:
    raise SystemExit("R4K2F4: anchorNeedles marker not found")

new_read = r'''  auto readNeedle = [&](const std::vector<std::string>& needles, bool fragmentSearch) -> std::string {
    (void)fragmentSearch;
    size_t pos = std::string::npos;
    std::string activeNeedle;
    for (const auto& needle : needles) {
      if (needle.empty()) continue;
      const size_t candidate = targetHtml.find(needle);
      if (candidate != std::string::npos && (pos == std::string::npos || candidate < pos)) {
        pos = candidate;
        activeNeedle = needle;
      }
    }
    if (pos == std::string::npos) return {};

    if (diagContext.empty()) {
      const size_t contextStart = pos > 256 ? pos - 256 : 0;
      const size_t contextLen = std::min<size_t>(1024, targetHtml.size() - contextStart);
      diagContext = targetHtml.substr(contextStart, contextLen);
    }

    size_t begin = pos;
    std::string blockTag;
    struct Block { const char* open; const char* close; };
    constexpr Block blocks[] = {{"<dl", "dl"}, {"<aside", "aside"}, {"<section", "section"},
                                {"<li", "li"}, {"<div", "div"}, {"<p", "p"}};
    size_t best = std::string::npos;
    for (const auto& b : blocks) {
      const size_t bp = targetHtml.rfind(b.open, pos);
      if (bp != std::string::npos && (best == std::string::npos || bp > best)) {
        best = bp;
        blockTag = b.close;
      }
    }
    if (best != std::string::npos) begin = best;
    else {
      const size_t lt = targetHtml.rfind('<', pos);
      if (lt != std::string::npos) begin = lt;
    }

    size_t stop = std::string::npos;
    size_t suffix = 0;
    if (!blockTag.empty() && blockTag != "p") {
      const std::string close = "</" + blockTag + ">";
      stop = targetHtml.find(close, pos);
      suffix = close.size();
    } else if (blockTag == "p") {
      bool multiParagraph = false;
      std::string family;
      if (fragment.rfind("id_Footnote_", 0) == 0) family = "id_Footnote_";
      else if (fragment.rfind("Footnote_", 0) == 0) family = "Footnote_";
      if (!family.empty()) {
        multiParagraph = true;
        const size_t next1 = targetHtml.find("id=\"" + family, pos + activeNeedle.size());
        const size_t next2 = targetHtml.find("id='" + family, pos + activeNeedle.size());
        size_t next = next1;
        if (next == std::string::npos || (next2 != std::string::npos && next2 < next)) next = next2;
        if (next != std::string::npos) {
          const size_t pbegin = targetHtml.rfind("<p", next);
          stop = pbegin == std::string::npos ? next : pbegin;
        }
      }
      if (!multiParagraph) {
        stop = targetHtml.find("</p>", pos);
        suffix = 4;
      }
    }

    constexpr size_t CAPTURE_LIMIT = 16384;
    size_t captureEnd = stop == std::string::npos ? std::min(targetHtml.size(), begin + CAPTURE_LIMIT)
                                                  : std::min(targetHtml.size(), stop + suffix);
    if (captureEnd <= begin) return {};
    return trimPlain(htmlToPlain(targetHtml.substr(begin, captureEnd - begin)));
  };
'''

s = s[:start] + new_read + s[end:]

# Final cleanup no longer removes/reads temp files.
s = s.replace('''      Storage.remove(tmpPath.c_str());
      return text;
''', '''      return text;
''')
s = s.replace('''  Storage.remove(tmpPath.c_str());
  if (tempReadFailed) {
    writeDiagnostic("TEMP_FILE_READ_FAILED");
  } else {
    writeDiagnostic(errorCode.empty() ? "FOOTNOTE_UNSUPPORTED_STRUCTURE" : errorCode.c_str());
  }
  return {};
''', '''  writeDiagnostic(errorCode.empty() ? "FOOTNOTE_UNSUPPORTED_STRUCTURE" : errorCode.c_str());
  return {};
''')

cpp.write_text(s, encoding="utf-8")
print("CPHUN-135r4k2f4 applied: bounded one-shot ZIP inflate for footnote target")
