from pathlib import Path

# Centralize CPHUN diagnostic logs under /logfiles on the SD card.
# Keep a fallback to the EPUB directory if the log directory cannot be created.

cpp = Path("src/activities/reader/EpubReaderActivity.cpp")
s = cpp.read_text(encoding="utf-8")

old = '''    const size_t slash = bookPath.find_last_of("/\\\\");
    const std::string dir = slash == std::string::npos ? std::string() : bookPath.substr(0, slash + 1);
    std::string tag = fragment.empty() ? "unknown" : fragment;
'''
new = '''    constexpr const char* LOG_DIR = "/logfiles";
    const bool logDirReady = Storage.ensureDirectoryExists(LOG_DIR);
    const size_t slash = bookPath.find_last_of("/\\\\");
    const std::string fallbackDir = slash == std::string::npos ? std::string() : bookPath.substr(0, slash + 1);
    const std::string dir = logDirReady ? std::string(LOG_DIR) + "/" : fallbackDir;
    std::string tag = fragment.empty() ? "unknown" : fragment;
'''
if old not in s:
    raise SystemExit("CPHUN logdir: diagnostic directory block not found")
s = s.replace(old, new, 1)

cpp.write_text(s, encoding="utf-8")
print("CPHUN log directory patch applied: /logfiles with EPUB-dir fallback")
