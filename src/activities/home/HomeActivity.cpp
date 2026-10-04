#include "HomeActivity.h"

#include <Bitmap.h>
#include <Epub.h>
#include <FsHelpers.h>
#include <GfxRenderer.h>
#include <HalStorage.h>
#include <I18n.h>
#include <HalGPIO.h>
#include <Utf8.h>
#include <Xtc.h>
#include <Epub/Section.h>

#include <algorithm>
#include <cmath>
#include <cstring>
#include <memory>
#include <vector>

#include "CrossPointSettings.h"
#include "CrossPointState.h"
#include "MappedInputManager.h"
#include "OpdsServerStore.h"
#include "RecentBooksStore.h"
#include "components/UITheme.h"
#include "activities/reader/BookInfoActivity.h"
#include "activities/util/BmpViewerActivity.h"
#include "CoverGridBrowserActivity.h"
#include "components/icons/folder.h"
#include "components/icons/recent.h"
#include "components/icons/library.h"
#include "components/icons/transfer.h"
#include "components/icons/settings2.h"
#include "fontIds.h"

namespace {
struct CoverGridLayout {
  int left;
  int coverW;
  int coverH;
  int featuredY;
  int gridY;
  int gapX;
  int columns;
  int menuTop;
};

CoverGridLayout coverGridLayout(const GfxRenderer& renderer) {
  (void)renderer;
  constexpr int left = 28;
  constexpr int gapX = 14;
  constexpr int columns = 3;
  constexpr int coverW = 132;
  constexpr int coverH = 220;
  return {left, coverW, coverH, 38, 276, gapX, columns, 502};
}

std::string trimCopy(std::string value) {
  const auto first = value.find_first_not_of(" \t\r\n-_");
  if (first == std::string::npos) return {};
  const auto last = value.find_last_not_of(" \t\r\n-_");
  return value.substr(first, last - first + 1);
}

std::string asciiLowerCopy(std::string value) {
  for (char& c : value) {
    if (c >= 'A' && c <= 'Z') c = static_cast<char>(c - 'A' + 'a');
  }
  return value;
}

std::string cleanDisplayedBookTitle(std::string title) {
  title = trimCopy(title);
  const std::string lower = asciiLowerCopy(title);
  static constexpr const char* suffixes[] = {"ok", "x4", "korr", "jav"};
  for (const char* suffix : suffixes) {
    const size_t n = std::char_traits<char>::length(suffix);
    if (lower.size() < n || lower.compare(lower.size() - n, n, suffix) != 0) continue;
    const size_t start = lower.size() - n;
    if (start > 0 && lower[start - 1] != ' ' && lower[start - 1] != '\t') continue;
    title = trimCopy(title.substr(0, start));
    break;
  }
  return title;
}

int scaledCalibrePageCount(const int referencePages, const GfxRenderer& renderer) {
  if (referencePages <= 0) return 0;

  // Count Pages reference calibration: Bitter 16 pt, NORMAL line spacing,
  // 10 px screen margin, 500 characters/page.
  constexpr float REFERENCE_FONT_PT = 16.0f;
  constexpr int REFERENCE_MARGIN_PX = 10;
  const float fontScale = static_cast<float>(SETTINGS.fontPointSize) / REFERENCE_FONT_PT;
  const float lineScale = SETTINGS.getReaderLineCompression();  // NORMAL == 1.0

  const int screenW = renderer.getScreenWidth();
  const int screenH = renderer.getScreenHeight();
  const int statusBar = UITheme::getStatusBarHeight();
  const int margin = SETTINGS.screenMargin;
  const float refW = static_cast<float>(std::max(1, screenW - 2 * REFERENCE_MARGIN_PX));
  const float curW = static_cast<float>(std::max(1, screenW - 2 * margin));
  const float refH = static_cast<float>(std::max(1, screenH - statusBar - 2 * REFERENCE_MARGIN_PX));
  const float curH = static_cast<float>(std::max(1, screenH - statusBar - 2 * margin));
  const float areaScale = (refW * refH) / (curW * curH);

  const float scale = fontScale * fontScale * lineScale * areaScale;
  return std::max(1, static_cast<int>(std::lround(static_cast<float>(referencePages) * scale)));
}

bool isTechnicalPartTitle(const std::string& lower) {
  if (lower.rfind("part", 0) != 0 || lower.size() <= 4) return false;
  for (size_t i = 4; i < lower.size(); ++i) {
    if (lower[i] < '0' || lower[i] > '9') return false;
  }
  return true;
}

bool isHiddenChapterTitle(const std::string& lower) {
  static constexpr const char* hidden[] = {
      "tartalom", "tartalomjegyzék", "borító", "impresszum",
      "címlap", "címoldal", "copyright", "index"};
  for (const char* item : hidden) {
    if (lower == item) return true;
  }
  return false;
}

bool chapterTitleNeedsSuffix(const std::string& lower) {
  if (lower.find("fejezet") != std::string::npos || lower.find("chapter") != std::string::npos) return false;
  static constexpr const char* noSuffix[] = {
      "előszó", "prológus", "epilógus", "szószedet", "bevezető"};
  for (const char* item : noSuffix) {
    if (lower.rfind(item, 0) == 0) return false;
  }
  return true;
}

bool validBmpFile(const std::string& path) {
  if (path.empty()) return false;
  HalFile file;
  if (!Storage.openFileForRead("HOME", path, file)) return false;
  Bitmap bmp(file);
  const bool ok = bmp.parseHeaders() == BmpReaderError::Ok && bmp.getWidth() > 0 && bmp.getHeight() > 0;
  file.close();
  return ok;
}
}  // namespace

bool HomeActivity::coverGridActive() const {
  return SETTINGS.homeLayout == CrossPointSettings::HOME_COVER_GRID &&
         renderer.getScreenWidth() < renderer.getScreenHeight();
}

bool HomeActivity::useLibraryHomeMenu() const {
  return SETTINGS.homeLayout == CrossPointSettings::HOME_COVER_GRID ||
         SETTINGS.uiTheme == CrossPointSettings::ROUNDEDRAFF;
}

int HomeActivity::gridBookLimit() const { return 4; }

int HomeActivity::gridThumbHeight(int index) const {
  (void)index;
  const auto layout = coverGridLayout(renderer);
  // The legacy thumbnail generator uses width = height * 0.6. Generate the
  // Cover Grid thumbnail tall enough that its width reaches the grid cell,
  // then center-crop the excess height at render time. This keeps the normal
  // RoundedRaff thumbnail cache untouched while guaranteeing full cell fill.
  return (layout.coverW * 10 + 5) / 6;
}

int HomeActivity::menuItemToIndex(const HomeMenuItem item) const {
  if (useLibraryHomeMenu()) {
    if (coverGridActive()) {
      if (item == HomeMenuItem::LIBRARY) return 0;
      if (item == HomeMenuItem::COVER_GRID_BROWSER) return 1;
      if (item == HomeMenuItem::FILE_BROWSER) return 2;
      if (item == HomeMenuItem::FILE_TRANSFER) return 3;
      if (item == HomeMenuItem::SETTINGS_MENU) return 4;
      return 0;
    }
    if (item == HomeMenuItem::LIBRARY) return 0;
    if (item == HomeMenuItem::COVER_GRID_BROWSER) return 1;
    if (item == HomeMenuItem::FILE_BROWSER) return 2;
    if (item == HomeMenuItem::FILE_TRANSFER) return 3;
    if (item == HomeMenuItem::SETTINGS_MENU) return 4;
    return 0;
  }
  int i = 0;
  if (item == HomeMenuItem::FILE_BROWSER) return i;
  ++i;
  if (item == HomeMenuItem::RECENTS) return i;
  ++i;
  if (item == HomeMenuItem::OPDS_BROWSER) return hasOpdsServers ? i : 0;
  if (hasOpdsServers) ++i;
  if (item == HomeMenuItem::FILE_TRANSFER) return i;
  ++i;
  if (item == HomeMenuItem::SETTINGS_MENU) return i;
  return 0;
}

HomeMenuItem HomeActivity::indexToMenuItem(const int idx) const {
  if (useLibraryHomeMenu()) {
    if (coverGridActive()) {
      if (idx == 0) return HomeMenuItem::LIBRARY;
      if (idx == 1) return HomeMenuItem::COVER_GRID_BROWSER;
      if (idx == 2) return HomeMenuItem::FILE_BROWSER;
      if (idx == 3) return HomeMenuItem::FILE_TRANSFER;
      if (idx == 4) return HomeMenuItem::SETTINGS_MENU;
      return HomeMenuItem::NONE;
    }
    if (idx == 0) return HomeMenuItem::LIBRARY;
    if (idx == 1) return HomeMenuItem::COVER_GRID_BROWSER;
    if (idx == 2) return HomeMenuItem::FILE_BROWSER;
    if (idx == 3) return HomeMenuItem::FILE_TRANSFER;
    if (idx == 4) return HomeMenuItem::SETTINGS_MENU;
    return HomeMenuItem::NONE;
  }
  int i = 0;
  if (idx == i++) return HomeMenuItem::FILE_BROWSER;
  if (idx == i++) return HomeMenuItem::RECENTS;
  if (hasOpdsServers && idx == i++) return HomeMenuItem::OPDS_BROWSER;
  if (idx == i++) return HomeMenuItem::FILE_TRANSFER;
  if (idx == i) return HomeMenuItem::SETTINGS_MENU;
  return HomeMenuItem::NONE;
}

int HomeActivity::getMenuItemCount() const {
  int count = useLibraryHomeMenu() ? 5 : 4 + (hasOpdsServers ? 1 : 0);
  count += static_cast<int>(recentBooks.size());
  return count;
}

void HomeActivity::loadRecentBooks(int maxBooks) {
  recentBooks.clear();
  const auto& books = RECENT_BOOKS.getBooks();
  recentBooks.reserve(std::min(static_cast<int>(books.size()), maxBooks));

  for (const RecentBook& book : books) {
    // Limit to maximum number of recent books
    if (recentBooks.size() >= maxBooks) {
      break;
    }

    // Skip if file no longer exists
    if (RecentBooksStore::isMissing(book)) {
      continue;
    }

    recentBooks.push_back(book);
  }
}

void HomeActivity::loadFeaturedProgress() {
  featuredProgressPercent = -1;
  featuredProgressTenths = -1;
  featuredCurrentPage = 0;
  featuredTotalPages = 0;
  featuredSeries.clear();
  featuredChapterTitle.clear();
  if (recentBooks.empty() || !FsHelpers::hasEpubExtension(recentBooks[0].path)) return;

  auto epub = std::make_shared<Epub>(recentBooks[0].path, "/.crosspoint");
  if (!epub->load(false, true) || epub->getBookSize() == 0) return;

  Epub::BookInfo info;
  int calibrePageCount = 0;
  if (epub->readBookInfo(info)) {
    calibrePageCount = info.calibrePageCount;
    if (!info.series.empty()) {
      featuredSeries = info.series;
      if (!info.seriesIndex.empty()) {
      std::string seriesIndex = info.seriesIndex;
      const size_t decimalPos = seriesIndex.find_first_of(".,");
      if (decimalPos != std::string::npos && decimalPos + 1 < seriesIndex.size()) {
        bool fractionalPartIsZero = true;
        for (size_t i = decimalPos + 1; i < seriesIndex.size(); ++i) {
          if (seriesIndex[i] != '0') {
            fractionalPartIsZero = false;
            break;
          }
        }
        if (fractionalPartIsZero) seriesIndex.erase(decimalPos);
      }
        featuredSeries += " #" + seriesIndex;
      }
    }
  }

  HalFile f;
  if (!Storage.openFileForRead("HOME", epub->getCachePath() + "/progress.bin", f)) return;
  uint8_t data[10] = {};
  const int dataSize = f.read(data, sizeof(data));
  f.close();
  if (dataSize != 4 && dataSize != 6 && dataSize != 10) return;

  const int spineIndex = data[0] + (data[1] << 8);
  int pageIndex = data[2] + (data[3] << 8);
  const int chapterPages = dataSize >= 6 ? data[4] + (data[5] << 8) : 0;
  if (pageIndex == UINT16_MAX) pageIndex = 0;
  if (spineIndex < 0 || spineIndex >= epub->getSpineItemsCount()) return;

  float intra = 0.0f;
  if (chapterPages > 1) {
    intra = std::clamp(static_cast<float>(pageIndex) / static_cast<float>(chapterPages - 1), 0.0f, 1.0f);
  }
  const float progress = std::clamp(epub->calculateProgress(spineIndex, intra), 0.0f, 1.0f);
  featuredProgressTenths = static_cast<int>(progress * 1000.0f + 0.5f);
  featuredProgressPercent = static_cast<int>(progress * 100.0f + 0.5f);

  const int tocIndex = epub->getTocIndexForSpineIndex(spineIndex);
  if (tocIndex >= 0 && tocIndex < epub->getTocItemsCount()) {
    featuredChapterTitle = trimCopy(epub->getTocItem(tocIndex).title);
    std::string foldedChapter = asciiLowerCopy(featuredChapterTitle);

    // Remove technical suffixes that begin with "split". Keep the meaningful
    // user-facing prefix, then trim separators left behind by the removal.
    const size_t splitPos = foldedChapter.find("split");
    if (splitPos != std::string::npos) {
      featuredChapterTitle = trimCopy(featuredChapterTitle.substr(0, splitPos));
      foldedChapter = asciiLowerCopy(featuredChapterTitle);
    }

    // Hide generated and structural navigation labels from Home.
    if (featuredChapterTitle.empty() ||
        foldedChapter.rfind("index split", 0) == 0 ||
        foldedChapter.rfind("index_split", 0) == 0 ||
        isTechnicalPartTitle(foldedChapter) ||
        isHiddenChapterTitle(foldedChapter)) {
      featuredChapterTitle.clear();
    }
  }

  // Prefer Calibre Count Pages metadata when present. The stored #pages
  // value is calibrated at 500 chars/page = Bitter 16 pt / NORMAL / 10 px.
  // Scale it locally to the active CrossPoint reading geometry.
  if (calibrePageCount > 0) {
    featuredTotalPages = scaledCalibrePageCount(calibrePageCount, renderer);
    if (featuredTotalPages > 0) {
      featuredCurrentPage = std::clamp(
          1 + static_cast<int>(std::lround(progress * static_cast<float>(featuredTotalPages - 1))),
          1, featuredTotalPages);
    }
    return;
  }

  // Fallback: book-wide page fraction is shown only when every spine already has a
  // finalized page count for the current layout. Never force pagination from Home.
  int pagesBefore = 0;
  int total = 0;
  bool complete = true;
  for (int i = 0; i < epub->getSpineItemsCount(); ++i) {
    Section section(epub, i, renderer);
    const auto count = section.getCachedPageCount();
    if (!count.has_value() || *count <= 0) {
      complete = false;
      break;
    }
    if (i < spineIndex) pagesBefore += *count;
    total += *count;
  }
  if (complete && total > 0) {
    featuredCurrentPage = std::min(total, pagesBefore + std::max(0, pageIndex) + 1);
    featuredTotalPages = total;
  }
}

void HomeActivity::loadRecentCovers(int coverHeight) {
  recentsLoading = true;
  bool showingLoading = false;
  Rect popupRect;

  int progress = 0;
  for (RecentBook& book : recentBooks) {
    const int thumbHeight = coverGridActive() ? gridThumbHeight(progress) : coverHeight;
    bool success = true;

    if (FsHelpers::hasEpubExtension(book.path)) {
      Epub epub(book.path, "/.crosspoint");
      const std::string thumbTemplate = epub.getThumbBmpPath();
      if (book.coverBmpPath != thumbTemplate) {
        book.coverBmpPath = thumbTemplate;
        RECENT_BOOKS.updateBook(book.path, book.title, book.author, thumbTemplate);
      }
      const std::string coverPath =
          coverGridActive() ? epub.getGridThumbBmpPath(thumbHeight) : epub.getThumbBmpPath(thumbHeight);
      if (Storage.exists(coverPath.c_str()) && !validBmpFile(coverPath)) {
        LOG_DBG("HOME", "Removing invalid EPUB thumbnail: %s", coverPath.c_str());
        Storage.remove(coverPath.c_str());
      }
      if (!validBmpFile(coverPath)) {
        if (!showingLoading) {
          showingLoading = true;
          popupRect = GUI.drawPopup(renderer, tr(STR_LOADING_POPUP));
        }
        GUI.fillPopupProgress(renderer, popupRect, 10 + progress * (90 / std::max<size_t>(1, recentBooks.size())));
        // Recent books normally already have a cache. If not, build the cache
        // without CSS so the cover metadata is still available to the thumbnail generator.
        bool loaded = epub.load(false, true);
        if (!loaded) loaded = epub.load(true, true);
        success = loaded &&
                  (coverGridActive() ? epub.generateGridThumbBmp(thumbHeight) : epub.generateThumbBmp(thumbHeight)) &&
                  validBmpFile(coverPath);
      }
    } else if (FsHelpers::hasXtcExtension(book.path)) {
      Xtc xtc(book.path, "/.crosspoint");
      const std::string thumbTemplate = xtc.getThumbBmpPath();
      if (book.coverBmpPath != thumbTemplate) {
        book.coverBmpPath = thumbTemplate;
        RECENT_BOOKS.updateBook(book.path, book.title, book.author, thumbTemplate);
      }
      const std::string coverPath = xtc.getThumbBmpPath(thumbHeight);
      if (Storage.exists(coverPath.c_str()) && !validBmpFile(coverPath)) {
        LOG_DBG("HOME", "Removing invalid XTC thumbnail: %s", coverPath.c_str());
        Storage.remove(coverPath.c_str());
      }
      if (!validBmpFile(coverPath)) {
        if (!showingLoading) {
          showingLoading = true;
          popupRect = GUI.drawPopup(renderer, tr(STR_LOADING_POPUP));
        }
        GUI.fillPopupProgress(renderer, popupRect, 10 + progress * (90 / std::max<size_t>(1, recentBooks.size())));
        success = xtc.load() && xtc.generateThumbBmp(thumbHeight) && validBmpFile(coverPath);
      }
    }

    if (!success) {
      LOG_ERR("HOME", "Could not generate home thumbnail for %s", book.path.c_str());
    }
    coverRendered = false;
    progress++;
  }

  if (coverGridActive()) loadFeaturedProgress();
  recentsLoaded = true;
  recentsLoading = false;
  if (coverGridActive()) {
    gridFrameValid = false;
  }
  requestUpdate();
}

void HomeActivity::onEnter() {
  Activity::onEnter();

  hasOpdsServers = OPDS_STORE.hasServers();

  const auto& metrics = UITheme::getInstance().getMetrics();
  loadRecentBooks(coverGridActive() ? gridBookLimit() : metrics.homeRecentBooksCount);
  originalResumePath = recentBooks.empty() ? std::string{} : recentBooks[0].path;
  backPressSeen = false;
  gridFrameValid = false;
  previousGridSelection = -1;
  firstRenderDone = false;
  recentsLoaded = false;
  recentsLoading = false;
  coverRendered = false;
  coverBufferStored = false;

  const auto base = static_cast<int>(recentBooks.size());
  selectorIndex = initialMenuItem == HomeMenuItem::NONE ? 0 : base + menuItemToIndex(initialMenuItem);

  // Trigger first update
  requestUpdate();
}

void HomeActivity::onExit() {
  optionPopup_.dismiss();
  Activity::onExit();

  // Free the stored cover buffer if any
  freeCoverBuffer();
}

bool HomeActivity::storeCoverBuffer() {
  if (static_cast<CrossPointSettings::UI_THEME>(SETTINGS.uiTheme) ==
          CrossPointSettings::UI_THEME::ROUNDEDRAFF &&
      !recentsLoaded) {
    return false;
  }

  // render() must have already set the cover rect; without it we'd be back to
  // cloning the whole framebuffer.
  if (coverRectW <= 0 || coverRectH <= 0) return false;
  freeCoverBuffer();
  const size_t needed = renderer.getRegionByteSize(coverRectX, coverRectY, coverRectW, coverRectH);
  if (needed == 0) return false;
  coverBuffer = static_cast<uint8_t*>(malloc(needed));
  if (!coverBuffer) {
    LOG_ERR("HOME", "OOM: cover buffer (%u bytes)", (unsigned)needed);
    return false;
  }
  coverBufferSize = needed;
  if (!renderer.copyRegionToBuffer(coverRectX, coverRectY, coverRectW, coverRectH, coverBuffer, coverBufferSize)) {
    free(coverBuffer);
    coverBuffer = nullptr;
    coverBufferSize = 0;
    return false;
  }
  return true;
}

bool HomeActivity::restoreCoverBuffer() {
  if (!coverBuffer || coverRectW <= 0 || coverRectH <= 0) return false;
  return renderer.copyBufferToRegion(coverRectX, coverRectY, coverRectW, coverRectH, coverBuffer, coverBufferSize);
}

void HomeActivity::freeCoverBuffer() {
  if (coverBuffer) {
    free(coverBuffer);
    coverBuffer = nullptr;
  }
  coverBufferSize = 0;
  coverBufferStored = false;
}

void HomeActivity::loop() {
  if (optionPopup_.isActive()) {
    optionPopup_.handleInput(mappedInput, [this] { requestUpdate(); });
    return;
  }
  if (coverGridActive()) {
    loopCoverGrid();
    return;
  }
  const int menuCount = getMenuItemCount();
  const auto& metrics = UITheme::getInstance().getMetrics();

  auto activateSelection = [this] {
    if (selectorIndex < recentBooks.size()) {
      onSelectBook(recentBooks[selectorIndex].path);
      return;
    }
    const int menuIndex = selectorIndex - static_cast<int>(recentBooks.size());
    switch (indexToMenuItem(menuIndex)) {
      case HomeMenuItem::LIBRARY:
        onLibraryOpen();
        break;
      case HomeMenuItem::COVER_GRID_BROWSER:
        onCoverGridOpen();
        break;
      case HomeMenuItem::FILE_BROWSER:
        onFileBrowserOpen();
        break;
      case HomeMenuItem::RECENTS:
        onRecentsOpen();
        break;
      case HomeMenuItem::OPDS_BROWSER:
        onOpdsBrowserOpen();
        break;
      case HomeMenuItem::FILE_TRANSFER:
        onFileTransferOpen();
        break;
      case HomeMenuItem::SETTINGS_MENU:
        onSettingsOpen();
        break;
      default:
        break;
    }
  };

  int selectedBook = -1;
  if (mappedInput.wasLongPressed(MappedInputManager::Button::Confirm, 700) && selectedHomeBookIndex(selectedBook)) {
    showHomeBookOptions(selectedBook);
    return;
  }

  int longX = -1;
  int longY = -1;
  if (mappedInput.wasScreenLongPress(longX, longY) && !recentBooks.empty()) {
    const int coverColumnCount = std::max(1, metrics.homeRecentBooksCount);
    const int recentCount = std::min(static_cast<int>(recentBooks.size()), coverColumnCount);
    const int coverColumnWidth = (renderer.getScreenWidth() - 2 * metrics.contentSidePadding) / std::max(1, recentCount);
    for (int i = 0; i < recentCount; ++i) {
      const int x = metrics.contentSidePadding + i * coverColumnWidth;
      if (longX >= x && longX < x + coverColumnWidth &&
          longY >= metrics.homeTopPadding && longY < metrics.homeTopPadding + metrics.homeCoverTileHeight) {
        selectorIndex = i;
        showHomeBookOptions(i);
        return;
      }
    }
  }

  // Home navigation uses the logical mapped hardware buttons directly.
  // Keep the same mapping/orientation semantics as ButtonNavigator without
  // depending on its shared static input pointer/state.
  if (mappedInput.wasReleased(MappedInputManager::Button::NavNext)) {
    selectorIndex = ButtonNavigator::nextIndex(selectorIndex, menuCount);
    requestUpdate();
    return;
  }
  if (mappedInput.wasReleased(MappedInputManager::Button::NavPrevious)) {
    selectorIndex = ButtonNavigator::previousIndex(selectorIndex, menuCount);
    requestUpdate();
    return;
  }

  const auto swipe = mappedInput.wasSwipe();
  if (swipe == MappedInputManager::SwipeDir::Up) {
    selectorIndex = ButtonNavigator::nextIndex(selectorIndex, menuCount);
    requestUpdate();
    return;
  }
  if (swipe == MappedInputManager::SwipeDir::Down) {
    selectorIndex = ButtonNavigator::previousIndex(selectorIndex, menuCount);
    requestUpdate();
    return;
  }

  // Back is otherwise unused on the home menu: open the most recently read
  // book directly (recentBooks is most-recent-first and already pruned of
  // files missing from the SD card).
  if (mappedInput.wasReleased(MappedInputManager::Button::Back) && !recentBooks.empty()) {
    onSelectBook(recentBooks[0].path);
    return;
  }

  const int coverColumnCount = std::max(1, metrics.homeRecentBooksCount);
  const int recentCount = std::min(static_cast<int>(recentBooks.size()), coverColumnCount);
  const int coverColumnWidth = (renderer.getScreenWidth() - 2 * metrics.contentSidePadding) / coverColumnCount;
  int touchedBook = -1;
  const auto coverTouch = mappedInput.colTouch(touchedBook, metrics.contentSidePadding, coverColumnWidth, recentCount,
                                               metrics.homeTopPadding,
                                               metrics.homeTopPadding + metrics.homeCoverTileHeight, coverColumnWidth);
  if (coverTouch != MappedInputManager::RowTouch::None) {
    if (coverTouch == MappedInputManager::RowTouch::Down) {
      if (selectorIndex != touchedBook) {
        selectorIndex = touchedBook;
        requestUpdate();
      }
    } else {
      selectorIndex = touchedBook;
      activateSelection();
    }
    return;
  }

  const bool includeContinueReading = metrics.homeContinueReadingInMenu && !useLibraryHomeMenu();
  const int menuTop = metrics.homeTopPadding + 20 + metrics.homeCoverTileHeight + metrics.homeMenuTopOffset;
  const int renderedMenuSelection =
      includeContinueReading ? selectorIndex : selectorIndex - static_cast<int>(recentBooks.size());
  const int renderedMenuCount =
      menuCount - (includeContinueReading ? 0 : static_cast<int>(recentBooks.size()));
  int menuRow = -1;
  // Row height from the theme, not the metrics table: RoundedRaff draws
  // font-derived rows and the touch grid must match the visuals exactly.
  const int menuRowHeight = GUI.getMenuRowHeight(renderer);
  const auto menuTouch = mappedInput.rowTouch(menuRow, menuTop, menuRowHeight + metrics.menuSpacing, renderedMenuCount,
                                              0, INT32_MAX, menuRowHeight);
  if (menuTouch != MappedInputManager::RowTouch::None) {
    const int touchedIndex =
        includeContinueReading ? menuRow : menuRow + static_cast<int>(recentBooks.size());
    if (menuTouch == MappedInputManager::RowTouch::Down) {
      if (selectorIndex != touchedIndex) {
        selectorIndex = touchedIndex;
        requestUpdate();
      }
    } else {
      selectorIndex = touchedIndex;
      activateSelection();
    }
    return;
  }

  if (mappedInput.wasReleased(MappedInputManager::Button::Confirm)) {
    activateSelection();
  }
}

void HomeActivity::render(RenderLock&&) {
  if (coverGridActive()) {
    renderCoverGrid();
    return;
  }
  const auto& metrics = UITheme::getInstance().getMetrics();
  const auto pageWidth = renderer.getScreenWidth();
  const auto pageHeight = renderer.getScreenHeight();

  renderer.clearScreen();
  bool bufferRestored = coverBufferStored && restoreCoverBuffer();

  // Band spans topPadding..homeTopPadding: the cover tile starts at the fixed
  // homeTopPadding, so the height must shrink by topPadding or the band (and a
  // centered title, e.g. RoundedRaff's book title) sinks into the tile.
  GUI.drawHeader(renderer, Rect{0, metrics.topPadding, pageWidth, metrics.homeTopPadding - metrics.topPadding},
                 metrics.homeContinueReadingInMenu && !recentBooks.empty() ? recentBooks[0].title.c_str() : nullptr,
                 metrics.homeContinueReadingInMenu && !recentBooks.empty() ? recentBooks[0].author.c_str() : nullptr);

  // Record the tile rect so storeCoverBuffer (called from the theme) knows
  // which sub-region of the framebuffer to snapshot. ~16 KB in Portrait
  // instead of the 48 KB full framebuffer the previous bind captured.
  coverRectX = 0;
  const bool roundedRaffHome =
      static_cast<CrossPointSettings::UI_THEME>(SETTINGS.uiTheme) == CrossPointSettings::UI_THEME::ROUNDEDRAFF;
  coverRectY = metrics.homeTopPadding + 22 + (roundedRaffHome ? 14 : 0);
  coverRectW = pageWidth;
  coverRectH = roundedRaffHome ? metrics.homeCoverHeight : metrics.homeCoverTileHeight;

  GUI.drawRecentBookCover(renderer, Rect{0, metrics.homeTopPadding + 22, pageWidth, metrics.homeCoverTileHeight},
                          recentBooks, selectorIndex, coverRendered, coverBufferStored, bufferRestored,
                          std::bind(&HomeActivity::storeCoverBuffer, this));

  // RoundedRaff and Cover Grid share the reconstructed four-item home menu.
  // Other themes retain their legacy menu until explicitly migrated.
  std::vector<const char*> menuItems;
  std::vector<UIIcon> menuIcons;
  const bool includeContinueReading = metrics.homeContinueReadingInMenu && !useLibraryHomeMenu();
  if (useLibraryHomeMenu()) {
    if (coverGridActive()) {
      menuItems = {tr(STR_LIBRARY), tr(STR_BROWSE_FILES), tr(STR_FILE_TRANSFER), tr(STR_SETTINGS_TITLE)};
      menuIcons = {Library, Folder, Transfer, Settings};
    } else {
      const char* gridLabel = I18N.getLanguage() == Language::HU ? "Borítórács" : "Cover Grid";
      menuItems = {tr(STR_LIBRARY), gridLabel, tr(STR_BROWSE_FILES), tr(STR_FILE_TRANSFER), tr(STR_SETTINGS_TITLE)};
      menuIcons = {Library, Recent, Folder, Transfer, Settings};
    }
  } else {
    menuItems = {tr(STR_BROWSE_FILES), tr(STR_MENU_RECENT_BOOKS), tr(STR_FILE_TRANSFER), tr(STR_SETTINGS_TITLE)};
    menuIcons = {Folder, Recent, Transfer, Settings};
    if (hasOpdsServers) {
      menuItems.insert(menuItems.begin() + 2, tr(STR_OPDS_BROWSER));
      menuIcons.insert(menuIcons.begin() + 2, Library);
    }
    if (includeContinueReading && !recentBooks.empty()) {
      menuItems.insert(menuItems.begin(), tr(STR_CONTINUE_READING));
      menuIcons.insert(menuIcons.begin(), Book);
    }
  }

  GUI.drawButtonMenu(
      renderer,
      Rect{0, metrics.homeTopPadding + 20 + metrics.homeCoverTileHeight + metrics.homeMenuTopOffset, pageWidth,
           pageHeight - (metrics.headerHeight + metrics.homeTopPadding + metrics.verticalSpacing + 20 +
                         metrics.homeMenuTopOffset + metrics.buttonHintsHeight)},
      static_cast<int>(menuItems.size()),
      includeContinueReading ? selectorIndex : selectorIndex - static_cast<int>(recentBooks.size()),
      [&menuItems](int index) { return std::string(menuItems[index]); },
      [&menuIcons](int index) { return menuIcons[index]; });

  const auto labels = mappedInput.mapLabels(recentBooks.empty() ? "" : tr(STR_RESUME), tr(STR_SELECT), tr(STR_DIR_UP),
                                            tr(STR_DIR_DOWN));
  GUI.drawButtonHints(renderer, labels.btn1, labels.btn2, labels.btn3, labels.btn4);

  if (optionPopup_.isActive()) {
    optionPopup_.processRender(renderer, mappedInput);
    return;
  }

  renderer.displayBuffer();

  if (!firstRenderDone) {
    firstRenderDone = true;
    requestUpdate();
  } else if (!recentsLoaded && !recentsLoading) {
    recentsLoading = true;
    loadRecentCovers(metrics.homeCoverHeight);
  }
}

bool HomeActivity::selectedHomeBookIndex(int& index) const {
  const int bookCount = static_cast<int>(recentBooks.size());
  if (selectorIndex < 0 || selectorIndex >= bookCount) return false;
  index = selectorIndex;
  return true;
}

std::shared_ptr<Epub> HomeActivity::loadHomeBookEpub(const int index) {
  if (index < 0 || index >= static_cast<int>(recentBooks.size())) return {};
  if (!FsHelpers::hasEpubExtension(recentBooks[index].path)) return {};
  auto epub = std::make_shared<Epub>(recentBooks[index].path, "/.crosspoint");
  bool loaded = epub->load(false, true);
  if (!loaded) loaded = epub->load(true, true);
  return loaded ? epub : std::shared_ptr<Epub>{};
}

void HomeActivity::reopenHomeAfterChild() {
  gridFrameValid = false;
  coverRendered = false;
  coverBufferStored = false;
  requestUpdate();
}

void HomeActivity::openHomeBookInfo(const int index, const bool metadata) {
  auto epub = loadHomeBookEpub(index);
  if (!epub) {
    requestUpdate();
    return;
  }
  startActivityForResult(
      std::make_unique<BookInfoActivity>(renderer, mappedInput, epub,
                                         metadata ? BookInfoActivity::Page::Metadata
                                                  : BookInfoActivity::Page::Description),
      [this](const ActivityResult&) { reopenHomeAfterChild(); });
}

void HomeActivity::openHomeBookCover(const int index) {
  auto epub = loadHomeBookEpub(index);
  if (!epub) {
    requestUpdate();
    return;
  }
  std::string coverPath = epub->getBookCoverViewBmpPath();
  if (!Storage.exists(coverPath.c_str())) epub->generateBookCoverViewBmp();
  if (!Storage.exists(coverPath.c_str())) {
    requestUpdate();
    return;
  }
  startActivityForResult(std::make_unique<BmpViewerActivity>(renderer, mappedInput, coverPath, true),
                         [this](const ActivityResult&) { reopenHomeAfterChild(); });
}

void HomeActivity::showHomeBookOptions(const int index) {
  if (index < 0 || index >= static_cast<int>(recentBooks.size())) return;
  static constexpr const char* OPTIONS_HU[] = {"Fülszöveg", "Metaadatok", "Borító megjelenítése", "Megnyitás"};
  static constexpr const char* OPTIONS_EN[] = {"Description", "Metadata", "Show cover", "Open"};
  const char* const* options = I18N.getLanguage() == Language::HU ? OPTIONS_HU : OPTIONS_EN;
  optionPopup_.showMultilineTitle(recentBooks[index].title.c_str(), options, 4, 0, [this, index](const int choice) {
    if (choice == 0) openHomeBookInfo(index, false);
    else if (choice == 1) openHomeBookInfo(index, true);
    else if (choice == 2) openHomeBookCover(index);
    else if (choice == 3) onSelectBook(recentBooks[index].path);
  });
  requestUpdate();
}

void HomeActivity::onSelectBook(const std::string& path) { activityManager.goToReader(path); }

void HomeActivity::onLibraryOpen() { activityManager.goToLibrary(); }

void HomeActivity::onCoverGridOpen() {
  startActivityForResult(std::make_unique<CoverGridBrowserActivity>(renderer, mappedInput),
                         [this](const ActivityResult&) { requestUpdate(); });
}

void HomeActivity::onFileBrowserOpen() { activityManager.goToFileBrowser(); }

void HomeActivity::onRecentsOpen() { activityManager.goToRecentBooks(); }

void HomeActivity::onSettingsOpen() { activityManager.goToSettings(); }

void HomeActivity::onFileTransferOpen() { activityManager.goToFileTransfer(); }

void HomeActivity::onOpdsBrowserOpen() { activityManager.goToBrowser(); }


// CPHUN-181: The two layouts share the same direct-to-framebuffer BMP renderer.
// No second screen-sized image or PSRAM cover snapshots are allocated.
void HomeActivity::paintGridCover(const size_t index, Rect rect) {
  if (index >= recentBooks.size()) return;
  const RecentBook& book = recentBooks[index];
  const int thumbHeight = gridThumbHeight(static_cast<int>(index));
  std::string path;
  if (FsHelpers::hasEpubExtension(book.path)) {
    Epub epub(book.path, "/.crosspoint");
    path = epub.getGridThumbBmpPath(thumbHeight);
  } else {
    path = UITheme::getCoverThumbPath(book.coverBmpPath, thumbHeight);
  }

  // Prefer the compact home thumbnail. If it is missing or corrupt, fall back
  // to the book's cached full cover so a failed thumbnail cannot blank the grid.
  if (!validBmpFile(path)) {
    if (FsHelpers::hasEpubExtension(book.path)) {
      Epub epub(book.path, "/.crosspoint");
      const std::string fallback = epub.getCoverBmpPath(false);
      if (validBmpFile(fallback)) path = fallback;
    } else if (FsHelpers::hasXtcExtension(book.path)) {
      Xtc xtc(book.path, "/.crosspoint");
      const std::string fallback = xtc.getCoverBmpPath();
      if (validBmpFile(fallback)) path = fallback;
    }
  }

  bool drawn = false;
  if (validBmpFile(path)) {
    HalFile file;
    if (Storage.openFileForRead("HOME", path, file)) {
      Bitmap bmp(file);
      if (bmp.parseHeaders() == BmpReaderError::Ok && bmp.getWidth() > 0 && bmp.getHeight() > 0) {
        const float imageRatio = static_cast<float>(bmp.getWidth()) / bmp.getHeight();
        const float targetRatio = static_cast<float>(rect.width) / rect.height;
        float cropX = 0.0f;
        float cropY = 0.0f;
        if (imageRatio > targetRatio) {
          // Wider than the grid cell: crop equally from left and right.
          cropX = std::max(0.0f, 1.0f - targetRatio / imageRatio);
        } else if (imageRatio < targetRatio) {
          // Taller/narrower than the grid cell: crop equally from top and bottom.
          cropY = std::max(0.0f, 1.0f - imageRatio / targetRatio);
        }
        renderer.drawBitmap(bmp, rect.x, rect.y, rect.width, rect.height, cropX, cropY);
        drawn = true;
      }
      file.close();
    }
  }

  renderer.drawRect(rect.x, rect.y, rect.width, rect.height, true);
  if (!drawn) {
    renderer.drawText(SMALL_FONT_ID, rect.x + 8, rect.y + rect.height / 3,
                      renderer.truncatedText(SMALL_FONT_ID, book.title.c_str(), rect.width - 16).c_str());
  }
  if (selectorIndex == static_cast<int>(index))
    renderer.drawRect(rect.x - 3, rect.y - 3, rect.width + 6, rect.height + 6, 2, true);
}

bool HomeActivity::renderGridGrayscaleCovers() {
  const auto layout = coverGridLayout(renderer);

  // Absolute/B is only safe here when strip uploads are available: each
  // grayscale strip is seeded from the already-rendered BW page, so text,
  // menu rows, frames and button hints survive as true black/white pixels.
  // Only the cover rectangles then replace those pixels with 2-bit levels.
  const bool stripSupported = renderer.supportsStripGrayscale();
  bool absolute = stripSupported &&
                  renderer.grayscaleCapabilities(HalDisplay::GrayscaleMode::Absolute).supported();

  if (absolute) {
    if (!renderer.displayGrayscaleBase(HalDisplay::GrayscaleMode::Absolute)) absolute = false;
  }
  if (!absolute) {
    renderer.displayGrayscaleBase(HalDisplay::HALF_REFRESH);
  }

  auto drawCoverPlane = [this, &layout](const size_t index) {
    if (index >= recentBooks.size()) return;
    const RecentBook& book = recentBooks[index];
    if (!FsHelpers::hasEpubExtension(book.path)) return;

    Epub epub(book.path, "/.crosspoint");
    const std::string path = epub.getGridThumbBmpPath(gridThumbHeight(static_cast<int>(index)));
    if (!validBmpFile(path)) return;

    const int x = index == 0
                      ? layout.left
                      : layout.left + ((static_cast<int>(index) - 1) % layout.columns) * (layout.coverW + layout.gapX);
    const int y = index == 0 ? layout.featuredY : layout.gridY;
    const Rect rect{x, y, layout.coverW, layout.coverH};

    HalFile file;
    if (!Storage.openFileForRead("HOME", path, file)) return;
    Bitmap bmp(file);
    if (bmp.parseHeaders() != BmpReaderError::Ok || bmp.getWidth() <= 0 || bmp.getHeight() <= 0) {
      file.close();
      return;
    }

    const float imageRatio = static_cast<float>(bmp.getWidth()) / bmp.getHeight();
    const float targetRatio = static_cast<float>(rect.width) / rect.height;
    float cropX = 0.0f;
    float cropY = 0.0f;
    if (imageRatio > targetRatio)
      cropX = std::max(0.0f, 1.0f - targetRatio / imageRatio);
    else if (imageRatio < targetRatio)
      cropY = std::max(0.0f, 1.0f - imageRatio / targetRatio);

    renderer.drawBitmap(bmp, rect.x, rect.y, rect.width, rect.height, cropX, cropY);
    file.close();
  };

  if (absolute) {
    constexpr int STRIP_ROWS = 32;
    const int panelRows = renderer.getDisplayHeight();
    const size_t rowBytes = renderer.getDisplayWidthBytes();
    const size_t scratchBytes = rowBytes * STRIP_ROWS;
    uint8_t* scratch = static_cast<uint8_t*>(malloc(scratchBytes));
    const uint8_t* bwPage = renderer.getFrameBuffer();
    if (scratch != nullptr && bwPage != nullptr) {
      for (const auto plane : {GfxRenderer::GRAYSCALE_LSB, GfxRenderer::GRAYSCALE_MSB}) {
        renderer.setRenderMode(plane);
        for (int y = 0; y < panelRows; y += STRIP_ROWS) {
          const int rows = std::min(STRIP_ROWS, panelRows - y);
          // Seed both Absolute planes with the BW UI: black=00, white=11.
          memcpy(scratch, bwPage + static_cast<size_t>(y) * rowBytes, static_cast<size_t>(rows) * rowBytes);
          renderer.beginStripTarget(scratch, y, rows);
          for (size_t i = 0; i < recentBooks.size(); ++i) drawCoverPlane(i);
          renderer.endStripTarget();
          renderer.writeGrayscalePlaneStrip(plane == GfxRenderer::GRAYSCALE_LSB, scratch, y, rows);
        }
      }
      free(scratch);
      renderer.displayGrayBuffer();
      renderer.setRenderMode(GfxRenderer::BW);
      return true;  // BW framebuffer was never destroyed.
    }
    if (scratch != nullptr) free(scratch);
    renderer.setRenderMode(GfxRenderer::BW);
    // Do not attempt an Absolute full-buffer fallback: it would erase the UI.
    return false;
  }

  // Overlay fallback for platforms without strip+Absolute support.
  renderer.clearScreen(0x00);
  renderer.setRenderMode(GfxRenderer::GRAYSCALE_LSB);
  for (size_t i = 0; i < recentBooks.size(); ++i) drawCoverPlane(i);
  renderer.copyGrayscaleLsbBuffers();

  renderer.clearScreen(0x00);
  renderer.setRenderMode(GfxRenderer::GRAYSCALE_MSB);
  for (size_t i = 0; i < recentBooks.size(); ++i) drawCoverPlane(i);
  renderer.copyGrayscaleMsbBuffers();

  renderer.displayGrayBuffer();
  renderer.setRenderMode(GfxRenderer::BW);
  return false;
}

void HomeActivity::previewGridBook(const int index) {
  if (index <= 0 || index >= static_cast<int>(recentBooks.size())) return;
  std::swap(recentBooks[0], recentBooks[index]);
  selectorIndex = 0;
  loadFeaturedProgress();
  gridFrameValid = false;
  previousGridSelection = -1;
  requestUpdate();
}

void HomeActivity::restoreOriginalGridBook() {
  if (originalResumePath.empty() || recentBooks.empty()) return;
  for (size_t i = 0; i < recentBooks.size(); ++i) {
    if (recentBooks[i].path == originalResumePath) {
      if (i != 0) std::swap(recentBooks[0], recentBooks[i]);
      selectorIndex = 0;
      loadFeaturedProgress();
      gridFrameValid = false;
      previousGridSelection = -1;
      return;
    }
  }
}

void HomeActivity::loopCoverGrid() {
  const auto layout = coverGridLayout(renderer);
  const auto& metrics = UITheme::getInstance().getMetrics();
  const int bookCount = static_cast<int>(recentBooks.size());
  const int navCount = bookCount + 5;

  auto activate = [this, bookCount]() {
    if (selectorIndex < bookCount) {
      if (selectorIndex == 0) onSelectBook(recentBooks[0].path);
      else previewGridBook(selectorIndex);
      return;
    }
    switch (indexToMenuItem(selectorIndex - bookCount)) {
      case HomeMenuItem::LIBRARY: onLibraryOpen(); break;
      case HomeMenuItem::COVER_GRID_BROWSER: onCoverGridOpen(); break;
      case HomeMenuItem::FILE_BROWSER: onFileBrowserOpen(); break;
      case HomeMenuItem::FILE_TRANSFER: onFileTransferOpen(); break;
      case HomeMenuItem::SETTINGS_MENU: onSettingsOpen(); break;
      default: break;
    }
  };

  int gridSelectedBook = -1;
  if (mappedInput.wasLongPressed(MappedInputManager::Button::Confirm, 700) && selectedHomeBookIndex(gridSelectedBook)) {
    showHomeBookOptions(gridSelectedBook);
    return;
  }

  int longX = -1;
  int longY = -1;
  if (mappedInput.wasScreenLongPress(longX, longY)) {
    for (int i = 0; i < bookCount; ++i) {
      const int x = i == 0 ? layout.left
                           : layout.left + ((i - 1) % layout.columns) * (layout.coverW + layout.gapX);
      const int y = i == 0 ? layout.featuredY : layout.gridY;
      if (longX >= x && longX < x + layout.coverW && longY >= y && longY < y + layout.coverH) {
        selectorIndex = i;
        showHomeBookOptions(i);
        return;
      }
    }
  }

  // Cover Grid handles the four front buttons directly through the logical
  // mappings. This avoids depending on ButtonNavigator's shared/static state
  // while still respecting the user's configured hardware mapping.
  if (mappedInput.wasReleased(MappedInputManager::Button::NavNext)) {
    selectorIndex = ButtonNavigator::nextIndex(selectorIndex, navCount);
    requestUpdate();
    return;
  }
  if (mappedInput.wasReleased(MappedInputManager::Button::NavPrevious)) {
    selectorIndex = ButtonNavigator::previousIndex(selectorIndex, navCount);
    requestUpdate();
    return;
  }

  const auto swipe = mappedInput.wasSwipe();
  if (swipe == MappedInputManager::SwipeDir::Up || swipe == MappedInputManager::SwipeDir::Down) {
    selectorIndex = swipe == MappedInputManager::SwipeDir::Up
                        ? ButtonNavigator::nextIndex(selectorIndex, navCount)
                        : ButtonNavigator::previousIndex(selectorIndex, navCount);
    requestUpdate();
    return;
  }

  if (mappedInput.wasPressed(MappedInputManager::Button::Back)) backPressSeen = true;
  if (mappedInput.wasReleased(MappedInputManager::Button::Back) && backPressSeen && bookCount > 0) {
    restoreOriginalGridBook();
    if (!originalResumePath.empty()) onSelectBook(originalResumePath);
    else onSelectBook(recentBooks[0].path);
    return;
  }

  for (int i = 0; i < bookCount; ++i) {
    const int x = i == 0 ? layout.left
                         : layout.left + ((i - 1) % layout.columns) * (layout.coverW + layout.gapX);
    const int y = i == 0 ? layout.featuredY : layout.gridY;
    if (mappedInput.wasTapInRect(x, y, layout.coverW, layout.coverH)) {
      selectorIndex = i;
      activate();
      return;
    }
  }

  int menuRow = -1;
  const int menuRowHeight = GUI.getMenuRowHeight(renderer);
  const auto menuTouch = mappedInput.rowTouch(menuRow, layout.menuTop, menuRowHeight + metrics.menuSpacing, 5, 0,
                                              INT32_MAX, menuRowHeight);
  if (menuTouch != MappedInputManager::RowTouch::None) {
    selectorIndex = bookCount + menuRow;
    if (menuTouch == MappedInputManager::RowTouch::Tap) activate();
    else requestUpdate();
    return;
  }

  if (mappedInput.wasReleased(MappedInputManager::Button::Confirm)) activate();
}

void HomeActivity::renderCoverGrid() {
  const auto& metrics = UITheme::getInstance().getMetrics();
  const auto layout = coverGridLayout(renderer);

  // CPHUN-195: do not paint an incomplete BW/grid frame and then repaint it
  // several times while thumbnails are being prepared. Finish cover loading
  // first, then allow exactly one complete page render.
  if (!recentsLoaded && !recentsLoading) {
    firstRenderDone = true;
    loadRecentCovers(layout.coverH);
    return;
  }
  const int width = renderer.getScreenWidth();
  const int height = renderer.getScreenHeight();
  const int bookCount = static_cast<int>(recentBooks.size());

  auto drawMenu = [this, &metrics, &layout, width, height, bookCount]() {
    const char* gridLabel = I18N.getLanguage() == Language::HU ? "Borítórács" : "Cover Grid";
    std::vector<const char*> labels = {tr(STR_LIBRARY), gridLabel, tr(STR_BROWSE_FILES), tr(STR_FILE_TRANSFER),
                                       tr(STR_SETTINGS_TITLE)};
    std::vector<UIIcon> icons = {Library, Recent, Folder, Transfer, Settings};
    const int menuHeight = std::max(0, height - layout.menuTop - metrics.buttonHintsHeight - 6);
    renderer.fillRect(0, layout.menuTop, width, menuHeight, false);
    GUI.drawButtonMenu(renderer, Rect{0, layout.menuTop, width, menuHeight}, 5,
                       selectorIndex >= bookCount ? selectorIndex - bookCount : -1,
                       [&labels](int index) { return std::string(labels[index]); },
                       [&icons](int index) { return icons[index]; });
  };

  if (gridFrameValid && recentsLoaded) {
    auto outlineBook = [this, &layout](const int selected, const bool black) {
      if (selected < 0 || selected >= static_cast<int>(recentBooks.size())) return;
      const int x = selected == 0 ? layout.left
                                  : layout.left + ((selected - 1) % layout.columns) * (layout.coverW + layout.gapX);
      const int y = selected == 0 ? layout.featuredY : layout.gridY;
      renderer.drawRect(x - 3, y - 3, layout.coverW + 6, layout.coverH + 6, 2, black);
    };

    if (previousGridSelection != selectorIndex) {
      const bool oldMenu = previousGridSelection >= bookCount;
      const bool newMenu = selectorIndex >= bookCount;
      if (oldMenu || newMenu) {
        drawMenu();
      }
      if (!oldMenu) outlineBook(previousGridSelection, false);
      if (!newMenu) outlineBook(selectorIndex, true);
    }
    previousGridSelection = selectorIndex;
    // Keep the current UI edits, but re-compose the cover rectangles through
    // the Absolute grayscale path instead of sending the whole BW framebuffer.
    // A plain displayBuffer() here is what made every cover fall back to dark BW.
    gridFrameValid = renderGridGrayscaleCovers();
    return;
  }

  renderer.clearScreen();
  // Compact 32 px header zone for the 132x220 Cover Grid geometry.
  GUI.drawHeader(renderer, Rect{0, metrics.topPadding, width, std::max(0, 32 - metrics.topPadding)}, nullptr);

  if (!recentBooks.empty()) {
    paintGridCover(0, Rect{layout.left, layout.featuredY, layout.coverW, layout.coverH});

    const int textX = layout.left + layout.coverW + 22;  // 182 px on 480-wide X4
    const int textW = std::max(40, width - textX - 34);   // 264 px on 480-wide X4
    const std::string displayTitle = cleanDisplayedBookTitle(recentBooks[0].title);
    const auto title = renderer.wrappedText(UI_12_FONT_ID, displayTitle.c_str(), textW, 4);
    int titleY = layout.featuredY + 12;
    for (const auto& line : title) {
      renderer.drawText(UI_12_FONT_ID, textX, titleY, line.c_str(), true, EpdFontFamily::BOLD);
      titleY += renderer.getLineHeight(UI_12_FONT_ID);
    }
    int infoY = titleY + 6;
    if (!recentBooks[0].author.empty()) {
      std::string author = recentBooks[0].author;
      if (I18N.getLanguage() == Language::HU) {
        const size_t comma = author.find(',');
        if (comma != std::string::npos) {
          author.erase(comma, 1);
          while (comma < author.size() && author[comma] == ' ') author.erase(comma, 1);
          author.insert(comma, " ");
        }
      }
      author = renderer.truncatedText(UI_12_FONT_ID, author.c_str(), textW);
      renderer.drawText(UI_12_FONT_ID, textX, infoY, author.c_str(), true, EpdFontFamily::REGULAR);
      infoY += renderer.getLineHeight(UI_12_FONT_ID) + 8;
    }
    if (!featuredSeries.empty()) {
      const auto series = renderer.truncatedText(UI_10_FONT_ID, featuredSeries.c_str(), textW);
      renderer.drawText(UI_10_FONT_ID, textX, infoY, series.c_str());
      infoY += renderer.getLineHeight(UI_10_FONT_ID) + 8;
    }
    if (!featuredChapterTitle.empty()) {
      std::string chapter = featuredChapterTitle;
      std::string folded = chapter;
      for (char& c : folded) {
        if (c >= 'A' && c <= 'Z') c = static_cast<char>(c - 'A' + 'a');
      }
      const bool hu = I18N.getLanguage() == Language::HU;
      const char* suffix = hu ? " fejezet" : " chapter";
      if (chapterTitleNeedsSuffix(folded)) chapter += suffix;
      chapter = renderer.truncatedText(UI_10_FONT_ID, chapter.c_str(), textW);
      renderer.drawText(UI_10_FONT_ID, textX, infoY, chapter.c_str());
      infoY += renderer.getLineHeight(UI_10_FONT_ID) + 8;
    }
    if (featuredProgressTenths >= 0) {
      char progressText[48];
      const int whole = featuredProgressTenths / 10;
      const int decimal = featuredProgressTenths % 10;
      const char decimalSep = I18N.getLanguage() == Language::HU ? ',' : '.';
      if (featuredTotalPages > 0 && featuredCurrentPage > 0) {
        snprintf(progressText, sizeof(progressText), "%d%c%d%% · %d / %d %s", whole, decimalSep, decimal,
                 featuredCurrentPage, featuredTotalPages,
                 I18N.getLanguage() == Language::HU ? "oldal" : "pages");
      } else {
        snprintf(progressText, sizeof(progressText), "%d%c%d%%", whole, decimalSep, decimal);
      }
      renderer.drawText(UI_10_FONT_ID, textX, infoY, progressText);

      constexpr int progressBarHeight = 8;
      const int progressBarY = infoY + renderer.getLineHeight(UI_10_FONT_ID) + 6;
      renderer.fillRect(textX, progressBarY, textW, progressBarHeight, false);
      renderer.drawRect(textX, progressBarY, textW, progressBarHeight, true);
      const int innerWidth = std::max(0, textW - 2);
      const int fillWidth = (innerWidth * std::clamp(featuredProgressTenths, 0, 1000) + 500) / 1000;
      if (fillWidth > 0) {
        renderer.fillRectDither(textX + 1, progressBarY + 1, fillWidth, progressBarHeight - 2, Color::DarkGray);
      }
    }

    for (size_t i = 1; i < recentBooks.size(); ++i) {
      const int x = layout.left + ((static_cast<int>(i) - 1) % layout.columns) * (layout.coverW + layout.gapX);
      paintGridCover(i, Rect{x, layout.gridY, layout.coverW, layout.coverH});
    }
  } else {
    renderer.drawText(UI_12_FONT_ID, layout.left, layout.featuredY + 50, tr(STR_NO_OPEN_BOOK));
  }

  drawMenu();

  const auto buttonLabels = mappedInput.mapLabels(recentBooks.empty() ? "" : tr(STR_RESUME), tr(STR_SELECT),
                                                  tr(STR_DIR_UP), tr(STR_DIR_DOWN));
  GUI.drawButtonHints(renderer, buttonLabels.btn1, buttonLabels.btn2, buttonLabels.btn3, buttonLabels.btn4);

  if (optionPopup_.isActive()) {
    optionPopup_.processRender(renderer, mappedInput);
    return;
  }

  gridFrameValid = renderGridGrayscaleCovers();
  previousGridSelection = selectorIndex;

  if (!firstRenderDone) {
    firstRenderDone = true;
    requestUpdate();
  } else if (!recentsLoaded && !recentsLoading) {
    recentsLoading = true;
    loadRecentCovers(layout.coverH);
  }
}

