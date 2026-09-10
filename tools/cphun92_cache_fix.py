from pathlib import Path


def replace_once(path: str, old: str, new: str) -> None:
    p = Path(path)
    text = p.read_text(encoding="utf-8")
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"Expected one match in {path}, found {count}")
    p.write_text(text.replace(old, new, 1), encoding="utf-8")


# Build id and Hungarian menu wording.
replace_once("src/CPHUNBuildId.h", 'CPHUN-260910-90', 'CPHUN-260910-92')
replace_once("lib/I18n/translations/hungarian.yaml",
             'STR_CLEAR_READING_CACHE: "Olvasási cache törlése"',
             'STR_CLEAR_READING_CACHE: "Összes olvasási cache törlése"')
replace_once("lib/I18n/translations/hungarian.yaml",
             'STR_DELETE_CACHE: "Könyv-cache törlése"',
             'STR_DELETE_CACHE: "Aktuális könyv cache törlése"')

# Epub API: reliable per-book clear which closes live cache handles and keeps position.
replace_once(
    "lib/Epub/Epub.h",
    '''  bool load(bool buildIfMissing = true, bool skipLoadingCss = false);\n  bool clearCache() const;\n  void setupCacheDir() const;''',
    '''  bool load(bool buildIfMissing = true, bool skipLoadingCss = false);\n  bool clearCache() const;\n  // Close all live cache handles, remove the entire per-book cache, and restore\n  // progress.bin so a manual clear does not lose the current reading position.\n  bool clearCachePreservingProgress();\n  void setupCacheDir() const;''')

# Source fingerprint helpers and automatic stale-cache invalidation.
replace_once(
    "lib/Epub/Epub.cpp",
    '#include "Epub/parsers/TocNcxParser.h"\n',
    '''#include "Epub/parsers/TocNcxParser.h"\n\nnamespace {\nconstexpr uint32_t SOURCE_FINGERPRINT_MAGIC = 0x43504650;  // "CPFP"\nconstexpr char SOURCE_FINGERPRINT_FILE[] = "/source.fp";\nconstexpr char PROGRESS_FILE[] = "/progress.bin";\n\nstruct SourceFingerprint {\n  uint32_t magic = SOURCE_FINGERPRINT_MAGIC;\n  uint32_t entryCount = 0;\n  uint64_t hash = 1469598103934665603ULL;\n};\nstatic_assert(sizeof(SourceFingerprint) == 16);\n\nvoid fnv1aAppend(uint64_t& hash, const void* data, const size_t size) {\n  const auto* bytes = static_cast<const uint8_t*>(data);\n  for (size_t i = 0; i < size; ++i) {\n    hash ^= bytes[i];\n    hash *= 1099511628211ULL;\n  }\n}\n\nvoid fnv1aAppendString(uint64_t& hash, const std::string_view value) {\n  fnv1aAppend(hash, value.data(), value.size());\n  const uint8_t separator = 0;\n  fnv1aAppend(hash, &separator, sizeof(separator));\n}\n}  // namespace\n''')

# Add private helper declarations.
replace_once(
    "lib/Epub/Epub.h",
    '''  void discoverCssFilesFromZip();\n  CssParser::ParseResult parseCssFiles(CssParser::CacheStatus existingCacheStatus) const;\n''',
    '''  void discoverCssFilesFromZip();\n  CssParser::ParseResult parseCssFiles(CssParser::CacheStatus existingCacheStatus) const;\n  bool computeSourceFingerprint(uint64_t& hash, uint32_t& entryCount) const;\n  bool sourceFingerprintMatches() const;\n  bool writeSourceFingerprint() const;\n''')

# Inject fingerprint implementation before load().
marker = '// load in the meta data for the epub file\nbool Epub::load(const bool buildIfMissing, const bool skipLoadingCss) {'
impl = r'''bool Epub::computeSourceFingerprint(uint64_t& hash, uint32_t& entryCount) const {
  SourceFingerprint fp;
  ZipFile zip(filepath);
  const bool ok = zip.enumerateFileEntries([&](std::string_view entryPath, uint32_t crc32, uint32_t compressedSize) {
    fnv1aAppendString(fp.hash, entryPath);
    fnv1aAppend(fp.hash, &crc32, sizeof(crc32));
    fnv1aAppend(fp.hash, &compressedSize, sizeof(compressedSize));
    ++fp.entryCount;
  });
  if (!ok) {
    LOG_ERR("EBP", "Could not fingerprint EPUB source: %s", filepath.c_str());
    return false;
  }
  // Mix the number of ZIP members in as a final guard against truncation/addition.
  fnv1aAppend(fp.hash, &fp.entryCount, sizeof(fp.entryCount));
  hash = fp.hash;
  entryCount = fp.entryCount;
  return true;
}

bool Epub::sourceFingerprintMatches() const {
  uint64_t currentHash = 0;
  uint32_t currentCount = 0;
  if (!computeSourceFingerprint(currentHash, currentCount)) return true;  // Fail safe: never delete on probe failure.

  HalFile file;
  if (!Storage.openFileForRead("EBP", cachePath + SOURCE_FINGERPRINT_FILE, file)) return false;
  SourceFingerprint stored;
  const int bytesRead = file.read(reinterpret_cast<uint8_t*>(&stored), sizeof(stored));
  file.close();
  return bytesRead == static_cast<int>(sizeof(stored)) && stored.magic == SOURCE_FINGERPRINT_MAGIC &&
         stored.entryCount == currentCount && stored.hash == currentHash;
}

bool Epub::writeSourceFingerprint() const {
  SourceFingerprint fp;
  if (!computeSourceFingerprint(fp.hash, fp.entryCount)) return false;
  HalFile file;
  if (!Storage.openFileForWrite("EBP", cachePath + SOURCE_FINGERPRINT_FILE, file)) return false;
  const size_t written = file.write(reinterpret_cast<const uint8_t*>(&fp), sizeof(fp));
  file.close();
  return written == sizeof(fp);
}

'''
replace_once("lib/Epub/Epub.cpp", marker, impl + marker)

# On warm load, invalidate a cache whose EPUB ZIP contents changed. Missing fingerprint
# means a pre-#92 cache: rebuild it once, preserving progress.
replace_once(
    "lib/Epub/Epub.cpp",
    '''  // Try to load existing cache first\n  if (bookMetadataCache->load()) {''',
    '''  // A cache is keyed by path for stable reading-position identity, so verify the\n  // actual EPUB contents separately. A Calibre overwrite at the same path must not\n  // reuse stale HTML/CSS/section data. Pre-#92 caches have no fingerprint and are\n  // deliberately rebuilt once.\n  if (Storage.exists((cachePath + "/book.bin").c_str()) && !sourceFingerprintMatches()) {\n    LOG_DBG("EBP", "EPUB source changed or has legacy cache; rebuilding: %s", filepath.c_str());\n    if (!clearCachePreservingProgress()) {\n      LOG_ERR("EBP", "Failed to invalidate stale EPUB cache");\n      return false;\n    }\n    bookMetadataCache.reset(new BookMetadataCache(cachePath));\n    cssParser.reset(new CssParser(cachePath));\n  }\n\n  // Try to load existing cache first\n  if (bookMetadataCache->load()) {''')

# Stamp fingerprint after a successful warm load.
replace_once(
    "lib/Epub/Epub.cpp",
    '''    cssParser->clear();\n    LOG_DBG("EBP", "Loaded ePub: %s", filepath.c_str());\n    return true;\n  }''',
    '''    cssParser->clear();\n    if (!writeSourceFingerprint()) LOG_ERR("EBP", "Failed to persist EPUB source fingerprint");\n    LOG_DBG("EBP", "Loaded ePub: %s", filepath.c_str());\n    return true;\n  }''')

# Stamp fingerprint after a successful cold rebuild.
replace_once(
    "lib/Epub/Epub.cpp",
    '''  LOG_DBG("EBP", "Loaded ePub: %s", filepath.c_str());\n  return true;\n}\n\nbool Epub::clearCache() const {''',
    '''  if (!writeSourceFingerprint()) LOG_ERR("EBP", "Failed to persist EPUB source fingerprint");\n  LOG_DBG("EBP", "Loaded ePub: %s", filepath.c_str());\n  return true;\n}\n\nbool Epub::clearCache() const {''')

# Strengthen clearCache() and add a handle-closing, progress-preserving variant.
replace_once(
    "lib/Epub/Epub.cpp",
    '''bool Epub::clearCache() const {\n  if (!Storage.exists(cachePath.c_str())) {\n    LOG_DBG("EPB", "Cache does not exist, no action needed");\n    return true;\n  }\n\n  if (!Storage.removeDir(cachePath.c_str())) {\n    LOG_ERR("EPB", "Failed to clear cache");\n    return false;\n  }\n\n  LOG_DBG("EPB", "Cache cleared successfully");\n  return true;\n}\n''',
    '''bool Epub::clearCache() const {\n  if (!Storage.exists(cachePath.c_str())) {\n    LOG_DBG("EPB", "Cache does not exist, no action needed");\n    return true;\n  }\n\n  if (!Storage.removeDir(cachePath.c_str()) || Storage.exists(cachePath.c_str())) {\n    LOG_ERR("EPB", "Failed to clear cache completely: %s", cachePath.c_str());\n    return false;\n  }\n\n  LOG_DBG("EPB", "Cache cleared successfully");\n  return true;\n}\n\nbool Epub::clearCachePreservingProgress() {\n  uint8_t progress[16] = {};\n  size_t progressSize = 0;\n  HalFile progressFile;\n  if (Storage.openFileForRead("EBP", cachePath + PROGRESS_FILE, progressFile)) {\n    const size_t fileSize = progressFile.size();\n    if (fileSize <= sizeof(progress)) {\n      const int read = progressFile.read(progress, fileSize);\n      if (read == static_cast<int>(fileSize)) progressSize = fileSize;\n    }\n    progressFile.close();\n  }\n\n  // BookMetadataCache keeps book.bin open while loaded. Close every cache-owned\n  // handle before removing the directory; otherwise a per-book clear can leave\n  // stale files behind on SD filesystems that reject deleting open files.\n  bookMetadataCache.reset();\n  cssParser.reset();\n\n  if (!clearCache()) return false;\n  setupCacheDir();\n\n  if (progressSize > 0) {\n    HalFile out;\n    if (!Storage.openFileForWrite("EBP", cachePath + PROGRESS_FILE, out)) return false;\n    const size_t written = out.write(progress, progressSize);\n    out.close();\n    if (written != progressSize) return false;\n  }\n  return true;\n}\n''')

# Current-book reader command: write latest position first, close Section, then use
# the handle-closing per-book cache clear. Keep the current position across rebuild.
replace_once(
    "src/activities/reader/EpubReaderActivity.cpp",
    '''        if (epub && section) {\n          uint16_t backupSpine = currentSpineIndex;\n          uint16_t backupPage = section->currentPage;\n          uint16_t backupPageCount = section->pageCount;\n          section.reset();\n          epub->clearCache();\n          epub->setupCacheDir();\n          if (!saveProgress(backupSpine, backupPage, backupPageCount)) {\n            LOG_ERR("ERS", "Failed to save progress before cache clear");\n          }\n        }''',
    '''        if (epub && section) {\n          const uint16_t backupSpine = currentSpineIndex;\n          const uint16_t backupPage = section->currentPage;\n          const uint16_t backupPageCount = section->pageCount;\n          // Persist the newest position while the cache is still intact; the cache\n          // clear below snapshots and restores progress.bin.\n          if (!saveProgress(backupSpine, backupPage, backupPageCount)) {\n            LOG_ERR("ERS", "Failed to save progress before cache clear");\n          }\n          section.reset();\n          if (!epub->clearCachePreservingProgress()) {\n            LOG_ERR("ERS", "Failed to clear current book cache");\n          }\n        }''')

# Global clear: enumerate first, close the directory, then mutate it. Deleting while
# openNextFile() was walking the same directory could skip entries. Also fail loudly
# if any target remains after removeDir().
replace_once(
    "src/activities/settings/ClearCacheActivity.cpp",
    '#include <Logging.h>\n',
    '#include <Logging.h>\n\n#include <string>\n#include <vector>\n')

old_global = r'''  clearedCount = 0;
  failedCount = 0;
  char name[128];

  // Iterate through all entries in the directory
  for (auto file = root.openNextFile(); file; file = root.openNextFile()) {
    file.getName(name, sizeof(name));
    String itemName(name);

    // Only delete directories matching known book cache names.
    if (file.isDirectory() && isBookCacheDirectoryName(itemName.c_str())) {
      String fullPath = "/.crosspoint/" + itemName;
      LOG_DBG("CLEAR_CACHE", "Removing cache: %s", fullPath.c_str());

      file.close();  // Close before attempting to delete

      if (Storage.removeDir(fullPath.c_str())) {
        clearedCount++;
      } else {
        LOG_ERR("CLEAR_CACHE", "Failed to remove: %s", fullPath.c_str());
        failedCount++;
      }
    } else {
      file.close();
    }
  }
  root.close();

  LOG_DBG("CLEAR_CACHE", "Cache cleared: %d removed, %d failed", clearedCount, failedCount);

  state = SUCCESS;
  requestUpdate();'''
new_global = r'''  clearedCount = 0;
  failedCount = 0;
  char name[128];
  std::vector<std::string> targets;

  // Snapshot target names first. Never mutate /.crosspoint while openNextFile()
  // is traversing it: FAT directory iteration can otherwise skip entries.
  for (auto file = root.openNextFile(); file; file = root.openNextFile()) {
    file.getName(name, sizeof(name));
    if (file.isDirectory() && isBookCacheDirectoryName(name)) {
      targets.emplace_back(std::string("/.crosspoint/") + name);
    }
    file.close();
  }
  root.close();

  for (const auto& fullPath : targets) {
    LOG_DBG("CLEAR_CACHE", "Removing cache: %s", fullPath.c_str());
    const bool removed = Storage.removeDir(fullPath.c_str());
    if (removed && !Storage.exists(fullPath.c_str())) {
      clearedCount++;
    } else {
      LOG_ERR("CLEAR_CACHE", "Failed to remove completely: %s", fullPath.c_str());
      failedCount++;
    }
  }

  LOG_DBG("CLEAR_CACHE", "Cache cleared: %d removed, %d failed", clearedCount, failedCount);

  state = failedCount == 0 ? SUCCESS : FAILED;
  requestUpdate();'''
replace_once("src/activities/settings/ClearCacheActivity.cpp", old_global, new_global)
