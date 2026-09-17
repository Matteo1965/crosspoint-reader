from pathlib import Path

# CPHUN-135r4k2f2
# Give every footnote resolver invocation its own temp file. This isolates
# repeated list -> popup -> list selections from stale SD/file-handle state.

cpp = Path("src/activities/reader/EpubReaderActivity.cpp")
s = cpp.read_text(encoding="utf-8")

old = '''  const std::string tmpPath = epub->getCachePath() + "/.footnote_resolver.tmp";
  HalFile out;
'''
new = '''  // CPHUN-135r4k2f2: never reuse the same resolver temp pathname across
  // consecutive popup selections. On the X4 the first resolve can succeed
  // while an immediately reused temp file fails on later selections.
  static uint16_t footnoteResolverSequence = 0;
  const std::string tmpPath =
      epub->getCachePath() + "/.footnote_resolver_" + std::to_string(++footnoteResolverSequence) + ".tmp";
  HalFile out;
'''
if old not in s:
    raise SystemExit("R4K2F2: resolver temp path block not found")
s = s.replace(old, new, 1)

# Make sure a failed open cannot leave a stale file from a wrapped sequence.
old = '''  if (!Storage.openFileForWrite("ERS", tmpPath, out)) {
    writeDiagnostic("FOOTNOTE_TARGET_NOT_FOUND");
    return {};
  }
'''
new = '''  Storage.remove(tmpPath.c_str());
  if (!Storage.openFileForWrite("ERS", tmpPath, out)) {
    writeDiagnostic("FOOTNOTE_TARGET_NOT_FOUND");
    return {};
  }
'''
if old not in s:
    raise SystemExit("R4K2F2: resolver open block not found")
s = s.replace(old, new, 1)

cpp.write_text(s, encoding="utf-8")
print("CPHUN-135r4k2f2 applied: unique resolver temp file per footnote selection")
