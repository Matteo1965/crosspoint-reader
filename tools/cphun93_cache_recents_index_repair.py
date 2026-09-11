from pathlib import Path


def replace_once(path: str, old: str, new: str):
    p = Path(path)
    s = p.read_text()
    if old not in s:
        raise SystemExit(f"pattern not found in {path}: {old[:120]!r}")
    p.write_text(s.replace(old, new, 1))


def insert_after(path: str, marker: str, addition: str):
    p = Path(path)
    s = p.read_text()
    if marker not in s:
        raise SystemExit(f"marker not found in {path}: {marker[:120]!r}")
    p.write_text(s.replace(marker, marker + addition, 1))


# Build ID
replace_once(
    "src/CPHUNBuildId.h",
    '#define CPHUN_BUILD_ID "CPHUN-260910-92"',
    '#define CPHUN_BUILD_ID "CPHUN-260911-93"',
)

# ---------------------------------------------------------------------------
# 1) Recent-books deduplication by exact path.
# ---------------------------------------------------------------------------
replace_once(
    "src/RecentBooksStore.cpp",
    '''  for (JsonObjectConst obj : arr) {
    if (getCount() >= MAX_RECENT_BOOKS) break;
    RecentBook book;
    book.path = obj["path"] | "";
    book.title = obj["title"] | "";
    book.author = obj["author"] | "";
    book.coverBmpPath = obj["coverBmpPath"] | "";
    recentBooks.push_back(book);
  }
''',
    '''  for (JsonObjectConst obj : arr) {
    if (getCount() >= MAX_RECENT_BOOKS) break;
    RecentBook book;
    book.path = obj["path"] | "";
    book.title = obj["title"] | "";
    book.author = obj["author"] | "";
    book.coverBmpPath = obj["coverBmpPath"] | "";
    if (book.path.empty()) continue;
    const bool duplicate = std::any_of(recentBooks.begin(), recentBooks.end(),
                                       [&](const RecentBook& existing) { return existing.path == book.path; });
    if (duplicate) {
      LOG_DBG("RBS", "Dropping duplicate recent-book entry: %s", book.path.c_str());
      continue;
    }
    recentBooks.push_back(book);
  }
''',
)

replace_once(
    "src/RecentBooksStore.cpp",
    '''  // Remove existing entry if present
  auto it =
      std::find_if(recentBooks.begin(), recentBooks.end(), [&](const RecentBook& book) { return book.path == path; });
  if (it != recentBooks.end()) {
    recentBooks.erase(it);
  }

  // Add to front
''',
    '''  // Remove every existing entry for this exact path. Older firmware could
  // leave duplicate rows behind; removing only the first match made them persistent.
  recentBooks.erase(std::remove_if(recentBooks.begin(), recentBooks.end(),
                                   [&](const RecentBook& book) { return book.path == path; }),
                    recentBooks.end());

  // Add to front
''',
)

replace_once(
    "src/RecentBooksStore.cpp",
    '''bool RecentBooksStore::removeByPath(const std::string& path) {
  auto it =
      std::find_if(recentBooks.begin(), recentBooks.end(), [&](const RecentBook& book) { return book.path == path; });
  if (it == recentBooks.end()) {
    return false;
  }
  recentBooks.erase(it);
  if (!saveToFile()) {
''',
    '''bool RecentBooksStore::removeByPath(const std::string& path) {
  const size_t before = recentBooks.size();
  recentBooks.erase(std::remove_if(recentBooks.begin(), recentBooks.end(),
                                   [&](const RecentBook& book) { return book.path == path; }),
                    recentBooks.end());
  if (recentBooks.size() == before) {
    return false;
  }
  if (!saveToFile()) {
''',
)

replace_once(
    "src/RecentBooksStore.cpp",
    '''  it->path = newPath;
  if (!oldCachePath.empty() && !it->coverBmpPath.empty() && it->coverBmpPath.rfind(oldCachePath, 0) == 0) {
    it->coverBmpPath = newCachePath + it->coverBmpPath.substr(oldCachePath.size());
  }
  saveToFile();
''',
    '''  it->path = newPath;
  if (!oldCachePath.empty() && !it->coverBmpPath.empty() && it->coverBmpPath.rfind(oldCachePath, 0) == 0) {
    it->coverBmpPath = newCachePath + it->coverBmpPath.substr(oldCachePath.size());
  }
  // If a stale duplicate already points at the destination, keep only the moved row.
  bool keptMoved = false;
  recentBooks.erase(std::remove_if(recentBooks.begin(), recentBooks.end(), [&](const RecentBook& book) {
                      if (book.path != newPath) return false;
                      if (!keptMoved && &book == &(*it)) {
                        keptMoved = true;
                        return false;
                      }
                      return &book != &(*it);
                    }),
                    recentBooks.end());
  saveToFile();
''',
)

# The address-based updatePath dedupe above is fragile under vector compaction; replace it
# with a stable path-based pass that keeps the first destination row (the moved row stays in place).
replace_once(
    "src/RecentBooksStore.cpp",
    '''  // If a stale duplicate already points at the destination, keep only the moved row.
  bool keptMoved = false;
  recentBooks.erase(std::remove_if(recentBooks.begin(), recentBooks.end(), [&](const RecentBook& book) {
                      if (book.path != newPath) return false;
                      if (!keptMoved && &book == &(*it)) {
                        keptMoved = true;
                        return false;
                      }
                      return &book != &(*it);
                    }),
                    recentBooks.end());
  saveToFile();
''',
    '''  // If a stale duplicate already points at the destination, keep only the first
  // destination row. updatePath preserves the moved entry's position, so it is the first
  // matching row unless an even older stale duplicate precedes it; either way one row remains.
  bool seenDestination = false;
  recentBooks.erase(std::remove_if(recentBooks.begin(), recentBooks.end(), [&](const RecentBook& book) {
                      if (book.path != newPath) return false;
                      if (!seenDestination) {
                        seenDestination = true;
                        return false;
                      }
                      return true;
                    }),
                    recentBooks.end());
  saveToFile();
''',
)

# ---------------------------------------------------------------------------
# 2) Cache-clear verification: after a per-book clear there must be no stale index,
#    fingerprint, HTML or section layout left behind. progress.bin may remain.
# ---------------------------------------------------------------------------
replace_once(
    "lib/Epub/Epub.h",
    '''  bool clearCachePreservingProgress();
  void setupCacheDir() const;
''',
    '''  bool clearCachePreservingProgress();
  bool cacheReadyForCleanRebuild() const;
  void setupCacheDir() const;
''',
)

insert_after(
    "lib/Epub/Epub.cpp",
    '''bool Epub::clearCachePreservingProgress() {
''',
    '''''',
)

# Append the verifier after clearCachePreservingProgress(). The function is at EOF in #92.
p = Path("lib/Epub/Epub.cpp")
s = p.read_text()
needle = '''  return true;\n}\n'''
idx = s.rfind(needle)
if idx < 0:
    raise SystemExit("clearCachePreservingProgress tail not found")
idx += len(needle)
verifier = '''\n\nbool Epub::cacheReadyForCleanRebuild() const {\n  if (!Storage.exists(cachePath.c_str())) {\n    LOG_ERR("EBP", "Cache directory missing after clear: %s", cachePath.c_str());\n    return false;\n  }\n\n  const char* stalePaths[] = {"/book.bin", "/source.fp", "/html", "/sections"};\n  for (const char* suffix : stalePaths) {\n    const std::string path = cachePath + suffix;\n    if (Storage.exists(path.c_str())) {\n      LOG_ERR("EBP", "Stale cache artifact remains after clear: %s", path.c_str());\n      return false;\n    }\n  }\n  return true;\n}\n'''
s = s[:idx] + verifier + s[idx:]
p.write_text(s)

replace_once(
    "src/activities/reader/EpubReaderActivity.cpp",
    '''          if (!epub->clearCachePreservingProgress()) {
            LOG_ERR("ERS", "Failed to clear current book cache");
          }
''',
    '''          if (!epub->clearCachePreservingProgress()) {
            LOG_ERR("ERS", "Failed to clear current book cache");
          } else if (!epub->cacheReadyForCleanRebuild()) {
            LOG_ERR("ERS", "Current-book cache clear left stale rebuild artifacts");
          } else {
            LOG_DBG("ERS", "Current-book cache verified clean for rebuild");
          }
''',
)

# ---------------------------------------------------------------------------
# 3) Recoverable malformed-spine handling.
#    The original EPUB is never modified. Confirmed skipped spine indexes are cached
#    in skipped_spines.bin and disappear automatically whenever the per-book cache is
#    invalidated because the EPUB source fingerprint changes.
# ---------------------------------------------------------------------------
replace_once(
    "src/activities/reader/EpubReaderActivity.h",
    '''  bool pendingReadFolderMove = false;

  // Footnote support
''',
    '''  bool pendingReadFolderMove = false;

  enum class IndexErrorDialog : uint8_t { None, Main, RepairConfirm };
  IndexErrorDialog indexErrorDialog = IndexErrorDialog::None;
  int indexErrorSelected = 0;
  int failedSpineIndex = -1;
  std::vector<uint16_t> skippedSpines;
  void loadSkippedSpines();
  bool isSpineSkipped(int spineIndex) const;
  bool persistSkippedSpine(int spineIndex);
  void showIndexBuildError();
  void renderIndexErrorDialog();
  bool handleIndexErrorDialogInput();
  void advancePastSkippedSpines(bool forward);

  // Footnote support
''',
)

# Load persisted skip decisions as soon as the EPUB cache is available.
replace_once(
    "src/activities/reader/EpubReaderActivity.cpp",
    '''  epub = std::move(loadedEpub);

  ImageBlock::clearSessionRenderFailures();
''',
    '''  epub = std::move(loadedEpub);
  loadSkippedSpines();

  ImageBlock::clearSessionRenderFailures();
''',
)

# Insert helper implementations before loop().
marker = '''void EpubReaderActivity::loop() {
'''
helpers = r'''namespace {
constexpr char SKIPPED_SPINES_FILE[] = "/skipped_spines.bin";
}

void EpubReaderActivity::loadSkippedSpines() {
  skippedSpines.clear();
  if (!epub) return;
  HalFile file;
  if (!Storage.openFileForRead("ERS", epub->getCachePath() + SKIPPED_SPINES_FILE, file)) return;
  const size_t size = file.size();
  if (size == 0 || size > 1024 || (size % 2) != 0) {
    file.close();
    return;
  }
  for (size_t i = 0; i < size / 2; ++i) {
    uint8_t bytes[2] = {};
    if (file.read(bytes, sizeof(bytes)) != static_cast<int>(sizeof(bytes))) break;
    const uint16_t spine = static_cast<uint16_t>(bytes[0]) | (static_cast<uint16_t>(bytes[1]) << 8);
    if (std::find(skippedSpines.begin(), skippedSpines.end(), spine) == skippedSpines.end()) {
      skippedSpines.push_back(spine);
    }
  }
  file.close();
}

bool EpubReaderActivity::isSpineSkipped(const int spineIndex) const {
  return spineIndex >= 0 &&
         std::find(skippedSpines.begin(), skippedSpines.end(), static_cast<uint16_t>(spineIndex)) !=
             skippedSpines.end();
}

bool EpubReaderActivity::persistSkippedSpine(const int spineIndex) {
  if (!epub || spineIndex < 0 || spineIndex >= epub->getSpineItemsCount()) return false;
  const uint16_t spine = static_cast<uint16_t>(spineIndex);
  if (std::find(skippedSpines.begin(), skippedSpines.end(), spine) == skippedSpines.end()) {
    skippedSpines.push_back(spine);
    std::sort(skippedSpines.begin(), skippedSpines.end());
  }
  HalFile out;
  if (!Storage.openFileForWrite("ERS", epub->getCachePath() + SKIPPED_SPINES_FILE, out)) return false;
  bool ok = true;
  for (const uint16_t item : skippedSpines) {
    const uint8_t bytes[2] = {static_cast<uint8_t>(item & 0xFF), static_cast<uint8_t>(item >> 8)};
    if (out.write(bytes, sizeof(bytes)) != sizeof(bytes)) {
      ok = false;
      break;
    }
  }
  out.close();
  return ok;
}

void EpubReaderActivity::advancePastSkippedSpines(const bool forward) {
  if (!epub) return;
  if (forward) {
    while (currentSpineIndex < epub->getSpineItemsCount() && isSpineSkipped(currentSpineIndex)) {
      LOG_DBG("ERS", "Skipping user-approved malformed spine %d", currentSpineIndex);
      ++currentSpineIndex;
      nextPageNumber = 0;
      pendingPageJump.reset();
      pendingAnchor.clear();
    }
  } else {
    while (currentSpineIndex >= 0 && isSpineSkipped(currentSpineIndex)) {
      LOG_DBG("ERS", "Skipping user-approved malformed spine %d (backward)", currentSpineIndex);
      --currentSpineIndex;
      nextPageNumber = 0;
      pendingPageJump = std::numeric_limits<uint16_t>::max();
      pendingAnchor.clear();
    }
    if (currentSpineIndex < 0) currentSpineIndex = 0;
  }
}

void EpubReaderActivity::showIndexBuildError() {
  failedSpineIndex = currentSpineIndex;
  indexErrorDialog = IndexErrorDialog::Main;
  indexErrorSelected = 0;
  automaticPageTurnActive = false;
  renderIndexErrorDialog();
}

void EpubReaderActivity::renderIndexErrorDialog() {
  renderer.clearScreen();
  if (indexErrorDialog == IndexErrorDialog::Main) {
    renderer.drawCenteredText(UI_12_FONT_ID, 150, "Indexelési hiba - hibás könyv", true, EpdFontFamily::BOLD);
    renderer.drawCenteredText(UI_12_FONT_ID, 245, "A könyv egyik része nem dolgozható fel.", true,
                              EpdFontFamily::REGULAR);
    const std::string actions = indexErrorSelected == 0 ? "> OK <        Javítás" : "OK        > Javítás <";
    renderer.drawCenteredText(UI_12_FONT_ID, 390, actions.c_str(), true, EpdFontFamily::BOLD);
  } else if (indexErrorDialog == IndexErrorDialog::RepairConfirm) {
    renderer.drawCenteredText(UI_12_FONT_ID, 120, "Hibás részek kihagyása", true, EpdFontFamily::BOLD);
    renderer.drawCenteredText(UI_12_FONT_ID, 205, "A CrossPoint megpróbálja megnyitni a könyvet,", true,
                              EpdFontFamily::REGULAR);
    renderer.drawCenteredText(UI_12_FONT_ID, 245, "és kihagyja a nem feldolgozható részeket.", true,
                              EpdFontFamily::REGULAR);
    renderer.drawCenteredText(UI_12_FONT_ID, 285, "Az eredeti EPUB nem módosul.", true, EpdFontFamily::REGULAR);
    const std::string actions = indexErrorSelected == 0 ? "> Mégse <        Javítás" : "Mégse        > Javítás <";
    renderer.drawCenteredText(UI_12_FONT_ID, 410, actions.c_str(), true, EpdFontFamily::BOLD);
  }
  renderer.displayBuffer();
}

bool EpubReaderActivity::handleIndexErrorDialogInput() {
  if (indexErrorDialog == IndexErrorDialog::None) return false;
  if (mappedInput.wasReleased(MappedInputManager::Button::Left) ||
      mappedInput.wasReleased(MappedInputManager::Button::Right)) {
    indexErrorSelected = 1 - indexErrorSelected;
    renderIndexErrorDialog();
    return true;
  }
  if (mappedInput.wasReleased(MappedInputManager::Button::Back)) {
    if (indexErrorDialog == IndexErrorDialog::RepairConfirm) {
      indexErrorDialog = IndexErrorDialog::Main;
      indexErrorSelected = 0;
      renderIndexErrorDialog();
    } else {
      indexErrorDialog = IndexErrorDialog::None;
      onGoHome();
    }
    return true;
  }
  if (!mappedInput.wasReleased(MappedInputManager::Button::Confirm)) return true;

  if (indexErrorDialog == IndexErrorDialog::Main) {
    if (indexErrorSelected == 0) {
      indexErrorDialog = IndexErrorDialog::None;
      onGoHome();
    } else {
      indexErrorDialog = IndexErrorDialog::RepairConfirm;
      indexErrorSelected = 0;
      renderIndexErrorDialog();
    }
    return true;
  }

  if (indexErrorSelected == 0) {
    indexErrorDialog = IndexErrorDialog::Main;
    indexErrorSelected = 0;
    renderIndexErrorDialog();
    return true;
  }

  const int badSpine = failedSpineIndex;
  if (!persistSkippedSpine(badSpine)) {
    LOG_ERR("ERS", "Failed to persist skipped malformed spine %d", badSpine);
    indexErrorDialog = IndexErrorDialog::Main;
    indexErrorSelected = 0;
    renderIndexErrorDialog();
    return true;
  }
  LOG_DBG("ERS", "User approved skipping malformed spine %d", badSpine);
  indexErrorDialog = IndexErrorDialog::None;
  indexErrorSelected = 0;
  failedSpineIndex = -1;
  section.reset();
  currentSpineIndex = badSpine + 1;
  nextPageNumber = 0;
  clearDeferredReposition();
  advancePastSkippedSpines(true);
  requestUpdate();
  return true;
}

'''
p = Path("src/activities/reader/EpubReaderActivity.cpp")
s = p.read_text()
if marker not in s:
    raise SystemExit("loop marker not found")
s = s.replace(marker, helpers + marker, 1)
p.write_text(s)

# Give the dialog priority over normal reader input.
replace_once(
    "src/activities/reader/EpubReaderActivity.cpp",
    '''void EpubReaderActivity::loop() {
  if (!epub) {
''',
    '''void EpubReaderActivity::loop() {
  if (handleIndexErrorDialogInput()) return;
  if (!epub) {
''',
)

# Replace the old one-line build-error popup with the interactive state.
replace_once(
    "src/activities/reader/EpubReaderActivity.cpp",
    '''  const auto showBuildError = [this]() {
    renderer.clearScreen();
    GUI.drawPopup(renderer, tr(STR_INDEX_FAILED));
    automaticPageTurnActive = false;
  };
''',
    '''  const auto showBuildError = [this]() { showIndexBuildError(); };
''',
)

# Respect persisted skips when reopening / jumping forward into a malformed spine.
replace_once(
    "src/activities/reader/EpubReaderActivity.cpp",
    '''  if (currentSpineIndex < 0) currentSpineIndex = 0;
  if (currentSpineIndex > epub->getSpineItemsCount()) currentSpineIndex = epub->getSpineItemsCount();

  if (currentSpineIndex == epub->getSpineItemsCount()) {
''',
    '''  if (currentSpineIndex < 0) currentSpineIndex = 0;
  if (currentSpineIndex > epub->getSpineItemsCount()) currentSpineIndex = epub->getSpineItemsCount();
  advancePastSkippedSpines(true);

  if (currentSpineIndex == epub->getSpineItemsCount()) {
''',
)

# Skip approved malformed spines during page turns in either direction.
replace_once(
    "src/activities/reader/EpubReaderActivity.cpp",
    '''      nextPageNumber = 0;
      currentSpineIndex++;
      section.reset();
''',
    '''      nextPageNumber = 0;
      currentSpineIndex++;
      advancePastSkippedSpines(true);
      section.reset();
''',
)
replace_once(
    "src/activities/reader/EpubReaderActivity.cpp",
    '''      pendingPageJump = std::numeric_limits<uint16_t>::max();
      currentSpineIndex--;
      section.reset();
''',
    '''      pendingPageJump = std::numeric_limits<uint16_t>::max();
      currentSpineIndex--;
      advancePastSkippedSpines(false);
      section.reset();
''',
)

# Keep skipPages consistent as well (first forward and backward occurrences after pageTurn).
p = Path("src/activities/reader/EpubReaderActivity.cpp")
s = p.read_text()
start = s.find("bool EpubReaderActivity::skipPages")
if start < 0:
    raise SystemExit("skipPages not found")
head, tail = s[:start], s[start:]
tail = tail.replace("    currentSpineIndex++;\n    section.reset();", "    currentSpineIndex++;\n    advancePastSkippedSpines(true);\n    section.reset();", 1)
tail = tail.replace("      currentSpineIndex--;\n      section.reset();", "      currentSpineIndex--;\n      advancePastSkippedSpines(false);\n      section.reset();", 1)
p.write_text(head + tail)

print("CPHUN-93 patch applied")
