from pathlib import Path

# CPHUN-135r4k2f7
# Reuse the already extracted footnote target XHTML across repeated selections
# in the same reader session. The previous resolver re-streamed the same ZIP
# member for every selection; on X4, the second stream can fail even though the
# first succeeds. Keep the fixed short temp filename and cache only one target.

h = Path("src/activities/reader/EpubReaderActivity.h")
s = h.read_text(encoding="utf-8")
needle = '''  std::vector<FootnoteEntry> bookFootnotes;
  bool bookFootnotesIndexed = false;'''
replacement = '''  std::vector<FootnoteEntry> bookFootnotes;
  bool bookFootnotesIndexed = false;
  mutable std::string footnoteResolverCachedTarget;'''
if needle not in s:
    raise SystemExit("R4K2F7: footnote member block not found")
s = s.replace(needle, replacement, 1)
h.write_text(s, encoding="utf-8")

p = Path("src/activities/reader/EpubReaderActivity.cpp")
s = p.read_text(encoding="utf-8")

old = '''  const std::string tmpPath = epub->getCachePath() + "/.footnote_resolver.tmp";
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
new = '''  const std::string tmpPath = epub->getCachePath() + "/.footnote_resolver.tmp";

  // CPHUN-135r4k2f7: if the same XHTML target was already extracted during
  // this reader session, reuse it instead of streaming the ZIP member again.
  bool haveCachedTarget = false;
  if (footnoteResolverCachedTarget == targetHref) {
    HalFile probe;
    if (Storage.openFileForRead("ERS", tmpPath, probe)) {
      probe.close();
      haveCachedTarget = true;
    } else {
      footnoteResolverCachedTarget.clear();
    }
  }

  if (!haveCachedTarget) {
    Storage.remove(tmpPath.c_str());
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
      footnoteResolverCachedTarget.clear();
      writeDiagnostic("EPUB_ZIP_STREAM_FAILED");
      return {};
    }
    footnoteResolverCachedTarget = targetHref;
  }
'''
if old not in s:
    raise SystemExit("R4K2F7: resolver extraction block not found")
s = s.replace(old, new, 1)

# On successful text extraction, keep the temp file for subsequent selections.
s = s.replace(
'''      Storage.remove(tmpPath.c_str());
      return text;''',
'''      return text;'''
)

# On a final resolver miss, keep a valid cached XHTML; only report the miss.
s = s.replace(
'''  Storage.remove(tmpPath.c_str());
  if (tempReadFailed) {''',
'''  if (tempReadFailed) {''',
1
)

p.write_text(s, encoding="utf-8")
print("CPHUN-135r4k2f7 applied: reuse extracted target XHTML across repeated footnotes")
