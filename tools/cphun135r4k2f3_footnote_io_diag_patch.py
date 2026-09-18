from pathlib import Path

# CPHUN-135r4k2f3 diagnostic isolation
# Based on R4K2F (NOT R4K2F2): keep shared resolver temp path, but report
# exactly which I/O stage fails when resolving a footnote target.

cpp = Path("src/activities/reader/EpubReaderActivity.cpp")
s = cpp.read_text(encoding="utf-8")

# Add target size diagnostics next to existing diagnostic context.
old = '''  const std::string targetHref = normalizePath(sourceHref, hrefPath);
  std::string errorCode;
  std::string diagContext;
'''
new = '''  const std::string targetHref = normalizePath(sourceHref, hrefPath);
  std::string errorCode;
  std::string diagContext;
  size_t diagnosticTargetSize = 0;
  bool diagnosticTargetSizeOk = false;
'''
if old not in s:
    raise SystemExit("R4K2F3: diagnostic state block not found")
s = s.replace(old, new, 1)

# Enrich the log with size lookup result.
old = '''    log += "Resolved target: " + targetHref + "\\n";
    log += "Fragment: " + fragment + "\\n\\n";
    log += "Error: ";
'''
new = '''    log += "Resolved target: " + targetHref + "\\n";
    log += "Fragment: " + fragment + "\\n";
    log += "Target size lookup: ";
    log += diagnosticTargetSizeOk ? "OK" : "FAILED";
    log += "\\n";
    log += "Target inflated size: " + std::to_string(diagnosticTargetSize) + "\\n\\n";
    log += "Error: ";
'''
if old not in s:
    raise SystemExit("R4K2F3: diagnostic log block not found")
s = s.replace(old, new, 1)

# Replace the ambiguous resolver preflight/open/stream block with explicit stages.
old = '''  if (targetHref.empty() || targetHref.find("://") != std::string::npos) {
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
'''
new = '''  if (targetHref.empty() || targetHref.find("://") != std::string::npos) {
    writeDiagnostic("FOOTNOTE_TARGET_INVALID");
    return {};
  }

  diagnosticTargetSizeOk = epub->getItemSize(targetHref, &diagnosticTargetSize);
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
if old not in s:
    raise SystemExit("R4K2F3: ambiguous resolver I/O block not found")
s = s.replace(old, new, 1)

# Track temp-file read failures inside readNeedle instead of silently returning {}.
old = '''  auto readNeedle = [&](const std::vector<std::string>& needles, bool fragmentSearch) -> std::string {
    HalFile in;
    if (!Storage.openFileForRead("ERS", tmpPath, in)) return {};
'''
new = '''  bool tempReadFailed = false;
  auto readNeedle = [&](const std::vector<std::string>& needles, bool fragmentSearch) -> std::string {
    HalFile in;
    if (!Storage.openFileForRead("ERS", tmpPath, in)) {
      tempReadFailed = true;
      return {};
    }
'''
if old not in s:
    raise SystemExit("R4K2F3: readNeedle open block not found")
s = s.replace(old, new, 1)

# Prefer explicit temp read failure at the final diagnostic.
old = '''  Storage.remove(tmpPath.c_str());
  writeDiagnostic(errorCode.empty() ? "FOOTNOTE_UNSUPPORTED_STRUCTURE" : errorCode.c_str());
  return {};
'''
new = '''  Storage.remove(tmpPath.c_str());
  if (tempReadFailed) {
    writeDiagnostic("TEMP_FILE_READ_FAILED");
  } else {
    writeDiagnostic(errorCode.empty() ? "FOOTNOTE_UNSUPPORTED_STRUCTURE" : errorCode.c_str());
  }
  return {};
'''
if old not in s:
    raise SystemExit("R4K2F3: final diagnostic block not found")
s = s.replace(old, new, 1)

cpp.write_text(s, encoding="utf-8")
print("CPHUN-135r4k2f3 applied: explicit footnote resolver I/O diagnostics")
