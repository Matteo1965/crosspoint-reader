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

#include <algorithm>
#include <cstring>
#include <vector>

#include "CrossPointSettings.h"
#include "CrossPointState.h"
#include "MappedInputManager.h"
#include "OpdsServerStore.h"
#include "RecentBooksStore.h"
#include "components/UITheme.h"
#include "components/icons/folder.h"
#include "components/icons/recent.h"
#include "components/icons/library.h"
#include "components/icons/transfer.h"
#include "components/icons/settings2.h"
#include "fontIds.h"

bool HomeActivity::coverGridActive() const {
  return SETTINGS.uiTheme == CrossPointSettings::COVER_GRID &&
         renderer.getScreenWidth() < renderer.getScreenHeight();
}

int HomeActivity::gridBookLimit() const {
#if defined(BOARD_HAS_PSRAM)
  return 7;  // Featured book and two rows of three on X4 Classic / PSRAM devices.
#else
  return 3;  // Featured book and two large covers on the original X4.
#endif
}

int HomeActivity::gridCoverHeight(int index) const {
#if defined(BOARD_HAS_PSRAM)
  return index == 0 ? 220 : 165;
#else
  return index == 0 ? 265 : 292;
#endif
}

int HomeActivity::getMenuItemCount() const {
  int count = 4;  // File Browser, Recents, File transfer, Settings
  if (!recentBooks.empty()) {
    count += recentBooks.size();
  }
  if (hasOpdsServers) {
    count++;
  }
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

void HomeActivity::loadRecentCovers(int coverHeight) {
  recentsLoading = true;
  bool showingLoading = false;
  Rect popupRect;

  int progress = 0;
  for (RecentBook& book : recentBooks) {
    if (!book.coverBmpPath.empty()) {
      const int thumbHeight = coverGridActive() ? gridCoverHeight(progress) : coverHeight;
      std::string coverPath = UITheme::getCoverThumbPath(book.coverBmpPath, thumbHeight);
      if (!Storage.exists(coverPath.c_str())) {
        // If epub, try to load the metadata for title/author and cover
        if (FsHelpers::hasEpubExtension(book.path)) {
          Epub epub(book.path, "/.crosspoint");
          // Skip loading css since we only need metadata here
          epub.load(false, true);

          // Try to generate thumbnail image for Continue Reading card
          if (!showingLoading) {
            showingLoading = true;
            popupRect = GUI.drawPopup(renderer, tr(STR_LOADING_POPUP));
          }
          GUI.fillPopupProgress(renderer, popupRect, 10 + progress * (90 / recentBooks.size()));
          bool success = epub.generateThumbBmp(thumbHeight);
          if (!success) {
            RECENT_BOOKS.updateBook(book.path, book.title, book.author, "");
            book.coverBmpPath = "";
          }
          coverRendered = false;
          requestUpdate();
        } else if (FsHelpers::hasXtcExtension(book.path)) {
          // Handle XTC file
          Xtc xtc(book.path, "/.crosspoint");
          if (xtc.load()) {
            // Try to generate thumbnail image for Continue Reading card
            if (!showingLoading) {
              showingLoading = true;
              popupRect = GUI.drawPopup(renderer, tr(STR_LOADING_POPUP));
            }
            GUI.fillPopupProgress(renderer, popupRect, 10 + progress * (90 / recentBooks.size()));
            bool success = xtc.generateThumbBmp(thumbHeight);
            if (!success) {
              RECENT_BOOKS.updateBook(book.path, book.title, book.author, "");
              book.coverBmpPath = "";
            }
            coverRendered = false;
            requestUpdate();
          }
        }
      }
    }
    progress++;
  }

  recentsLoaded = true;
  recentsLoading = false;
  if (coverGridActive()) {
    gridFrameValid = false;  // Loading popups and new BMPs invalidate the old pixels.
    requestUpdate();
  }
}

void HomeActivity::onEnter() {
  Activity::onEnter();

  hasOpdsServers = OPDS_STORE.hasServers();

  const auto& metrics = UITheme::getInstance().getMetrics();
  loadRecentBooks(coverGridActive() ? gridBookLimit() : metrics.homeRecentBooksCount);
  backPressSeen = false;
  gridFrameValid = false;
  previousGridSelection = -1;
  firstRenderDone = false;
  recentsLoaded = false;
  recentsLoading = false;
  coverRendered = false;
  coverBufferStored = false;

  const auto base = static_cast<int>(recentBooks.size());
  selectorIndex = initialMenuItem == HomeMenuItem::NONE ? 0 : base + menuItemToIndex(initialMenuItem, hasOpdsServers);

  // Trigger first update
  requestUpdate();
}

void HomeActivity::onExit() {
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
    switch (indexToMenuItem(menuIndex, hasOpdsServers)) {
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

  buttonNavigator.onNext([this, menuCount] {
    selectorIndex = ButtonNavigator::nextIndex(selectorIndex, menuCount);
    requestUpdate();
  });

  buttonNavigator.onPrevious([this, menuCount] {
    selectorIndex = ButtonNavigator::previousIndex(selectorIndex, menuCount);
    requestUpdate();
  });

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

  const int menuTop = metrics.homeTopPadding + metrics.homeCoverTileHeight + metrics.homeMenuTopOffset;
  const int renderedMenuSelection =
      metrics.homeContinueReadingInMenu ? selectorIndex : selectorIndex - recentBooks.size();
  const int renderedMenuCount =
      menuCount - (metrics.homeContinueReadingInMenu ? 0 : static_cast<int>(recentBooks.size()));
  int menuRow = -1;
  // Row height from the theme, not the metrics table: RoundedRaff draws
  // font-derived rows and the touch grid must match the visuals exactly.
  const int menuRowHeight = GUI.getMenuRowHeight(renderer);
  const auto menuTouch = mappedInput.rowTouch(menuRow, menuTop, menuRowHeight + metrics.menuSpacing, renderedMenuCount,
                                              0, INT32_MAX, menuRowHeight);
  if (menuTouch != MappedInputManager::RowTouch::None) {
    const int touchedIndex =
        metrics.homeContinueReadingInMenu ? menuRow : menuRow + static_cast<int>(recentBooks.size());
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
  coverRectY = metrics.homeTopPadding + 4;
  coverRectW = pageWidth;
  coverRectH = metrics.homeCoverTileHeight;

  GUI.drawRecentBookCover(renderer, Rect{0, metrics.homeTopPadding + 4, pageWidth, metrics.homeCoverTileHeight},
                          recentBooks, selectorIndex, coverRendered, coverBufferStored, bufferRestored,
                          std::bind(&HomeActivity::storeCoverBuffer, this));

  // Build menu items dynamically
  std::vector<const char*> menuItems = {tr(STR_BROWSE_FILES), tr(STR_MENU_RECENT_BOOKS), tr(STR_FILE_TRANSFER),
                                        tr(STR_SETTINGS_TITLE)};
  std::vector<UIIcon> menuIcons = {Folder, Recent, Transfer, Settings};

  if (hasOpdsServers) {
    menuItems.insert(menuItems.begin() + 2, tr(STR_OPDS_BROWSER));
    menuIcons.insert(menuIcons.begin() + 2, Library);
  }

  if (metrics.homeContinueReadingInMenu && !recentBooks.empty()) {
    // Insert Continue Reading at the top if enabled in theme
    menuItems.insert(menuItems.begin(), tr(STR_CONTINUE_READING));
    menuIcons.insert(menuIcons.begin(), Book);
  }

  GUI.drawButtonMenu(
      renderer,
      Rect{0, metrics.homeTopPadding + 4 + metrics.homeCoverTileHeight + metrics.homeMenuTopOffset, pageWidth,
           pageHeight - (metrics.headerHeight + metrics.homeTopPadding + metrics.verticalSpacing +
                         metrics.homeMenuTopOffset + metrics.buttonHintsHeight)},
      static_cast<int>(menuItems.size()),
      metrics.homeContinueReadingInMenu ? selectorIndex : selectorIndex - recentBooks.size(),
      [&menuItems](int index) { return std::string(menuItems[index]); },
      [&menuIcons](int index) { return menuIcons[index]; });

  const auto labels = mappedInput.mapLabels(recentBooks.empty() ? "" : tr(STR_RESUME), tr(STR_SELECT), tr(STR_DIR_UP),
                                            tr(STR_DIR_DOWN));
  GUI.drawButtonHints(renderer, labels.btn1, labels.btn2, labels.btn3, labels.btn4);

  renderer.displayBuffer();

  if (!firstRenderDone) {
    firstRenderDone = true;
    requestUpdate();
  } else if (!recentsLoaded && !recentsLoading) {
    recentsLoading = true;
    loadRecentCovers(metrics.homeCoverHeight);
  }
}

void HomeActivity::onSelectBook(const std::string& path) { activityManager.goToReader(path); }

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
  const std::string path = UITheme::getCoverThumbPath(book.coverBmpPath, gridCoverHeight(static_cast<int>(index)));
  bool drawn = false;
  if (!book.coverBmpPath.empty()) {
    HalFile file;
    if (Storage.openFileForRead("HOME", path, file)) {
      Bitmap bmp(file);
      if (bmp.parseHeaders() == BmpReaderError::Ok && bmp.getWidth() > 0 && bmp.getHeight() > 0) {
        const float imageRatio = static_cast<float>(bmp.getWidth()) / bmp.getHeight();
        const float targetRatio = static_cast<float>(rect.width) / rect.height;
        const float cropX = std::max(0.0f, 1.0f - targetRatio / imageRatio);
        renderer.drawBitmap(bmp, rect.x, rect.y, rect.width, rect.height, cropX);
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
    renderer.drawRect(rect.x - 3, rect.y - 3, rect.width + 6, rect.height + 6, true);
}

void HomeActivity::loopCoverGrid() {
  const int bookCount = static_cast<int>(recentBooks.size());
  const int navCount = getMenuItemCount();
  auto activate = [this, bookCount]() {
    if (selectorIndex < bookCount) {
      onSelectBook(recentBooks[selectorIndex].path);
      return;
    }
    switch (indexToMenuItem(selectorIndex - bookCount, hasOpdsServers)) {
      case HomeMenuItem::FILE_BROWSER: onFileBrowserOpen(); break;
      case HomeMenuItem::RECENTS: onRecentsOpen(); break;
      case HomeMenuItem::OPDS_BROWSER: onOpdsBrowserOpen(); break;
      case HomeMenuItem::FILE_TRANSFER: onFileTransferOpen(); break;
      case HomeMenuItem::SETTINGS_MENU: onSettingsOpen(); break;
      default: break;
    }
  };
  buttonNavigator.onNext([this, navCount]() {
    selectorIndex = ButtonNavigator::nextIndex(selectorIndex, navCount);
    requestUpdate();
  });
  buttonNavigator.onPrevious([this, navCount]() {
    selectorIndex = ButtonNavigator::previousIndex(selectorIndex, navCount);
    requestUpdate();
  });
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
    onSelectBook(recentBooks[0].path);
    return;
  }
#if defined(BOARD_HAS_PSRAM)
  const int coverW = 136, coverH = 165, coverTop = 333, rowGap = 24, colGap = 12, left = 24, columns = 3;
  const int featuredW = 156, featuredH = 220, featuredTop = 91;
#else
  const int coverW = (renderer.getScreenWidth() - 72) / 2, coverH = 292;
  const int coverTop = 392, rowGap = 0, colGap = 24, left = 24, columns = 2;
  const int featuredW = 180, featuredH = 265, featuredTop = 91;
#endif
  for (int i = 0; i < bookCount; ++i) {
    const int x = i == 0 ? 24 : left + ((i - 1) % columns) * (coverW + colGap);
    const int y = i == 0 ? featuredTop : coverTop + ((i - 1) / columns) * (coverH + rowGap);
    const int w = i == 0 ? featuredW : coverW;
    const int h = i == 0 ? featuredH : coverH;
    if (mappedInput.wasTapInRect(x, y, w, h)) {
      selectorIndex = i;
      activate();
      return;
    }
  }
  const int menuEntries = 4 + (hasOpdsServers ? 1 : 0);
  const int menuWidth = renderer.getScreenWidth() / menuEntries;
  for (int i = 0; i < menuEntries; ++i) {
    if (mappedInput.wasTapInRect(i * menuWidth, 702, menuWidth, 50)) {
      selectorIndex = bookCount + i;
      activate();
      return;
    }
  }
  if (mappedInput.wasReleased(MappedInputManager::Button::Confirm)) activate();
}

void HomeActivity::renderCoverGrid() {
  const auto& metrics = UITheme::getInstance().getMetrics();
  const int width = renderer.getScreenWidth();
  // The framebuffer persists while Home is active. Only repaint the old and
  // new one-pixel selection outlines when navigating; leave the BMPs intact.
  // onEnter() and thumbnail generation always invalidate this fast path.
  if (gridFrameValid) {
#if defined(BOARD_HAS_PSRAM)
    const int coverW = 136, coverH = 165, coverTop = 333, rowGap = 24, colGap = 12, columns = 3;
    const int featuredW = 156, featuredH = 220;
#else
    const int coverW = (width - 72) / 2, coverH = 292, coverTop = 392, rowGap = 0, colGap = 24, columns = 2;
    const int featuredW = 180, featuredH = 265;
#endif
    const int menuEntries = 4 + (hasOpdsServers ? 1 : 0);
    const int menuWidth = width / menuEntries;
    auto outline = [this, coverW, coverH, coverTop, rowGap, colGap, columns,
                    featuredW, featuredH, menuWidth](const int selected, const bool black) {
      if (selected < 0) return;
      if (selected < static_cast<int>(recentBooks.size())) {
        if (selected == 0) {
          renderer.drawRect(21, 88, featuredW + 6, featuredH + 6, black);
        } else {
          const int i = selected - 1;
          const int x = 24 + (i % columns) * (coverW + colGap);
          const int y = coverTop + (i / columns) * (coverH + rowGap);
          renderer.drawRect(x - 3, y - 3, coverW + 6, coverH + 6, black);
        }
      } else {
        const int i = selected - static_cast<int>(recentBooks.size());
        renderer.drawRect(i * menuWidth + 8, 703, menuWidth - 16, 49, black);
      }
    };
    if (previousGridSelection != selectorIndex) {
      outline(previousGridSelection, false);
      outline(selectorIndex, true);
    }
    previousGridSelection = selectorIndex;
    renderer.displayBuffer();
    return;
  }
  renderer.clearScreen();
  GUI.drawHeader(renderer, Rect{0, metrics.topPadding, width, metrics.homeTopPadding - metrics.topPadding}, nullptr);
  renderer.drawText(UI_12_FONT_ID, 24, 59, tr(STR_CONTINUE_READING), true, EpdFontFamily::BOLD);
#if defined(BOARD_HAS_PSRAM)
  const int featuredW = 156, featuredH = 220, featuredTop = 91;
  const int coverW = 136, coverH = 165, coverTop = 333, rowGap = 24, colGap = 12, left = 24;
  const int columns = 3;
#else
  const int featuredW = 180, featuredH = 265, featuredTop = 91;
  const int coverW = (width - 72) / 2, coverH = 292, coverTop = 392, rowGap = 0, colGap = 24, left = 24;
  const int columns = 2;
#endif
  if (!recentBooks.empty()) {
    paintGridCover(0, Rect{24, featuredTop, featuredW, featuredH});
    const int textX = 24 + featuredW + 16;
    const int textW = std::max(40, width - textX - 20);
    const auto title = renderer.wrappedText(UI_12_FONT_ID, recentBooks[0].title.c_str(), textW, 3);
    int titleY = featuredTop + featuredH / 2 - 35;
    for (const auto& line : title) {
      renderer.drawText(UI_12_FONT_ID, textX, titleY, line.c_str(), true, EpdFontFamily::BOLD);
      titleY += renderer.getLineHeight(UI_12_FONT_ID);
    }
    if (!recentBooks[0].author.empty()) {
      const auto author = renderer.truncatedText(UI_10_FONT_ID, recentBooks[0].author.c_str(), textW);
      renderer.drawText(UI_10_FONT_ID, textX, titleY + 5, author.c_str());
    }
    for (size_t i = 1; i < recentBooks.size(); ++i) {
      const int x = left + ((static_cast<int>(i) - 1) % columns) * (coverW + colGap);
      const int y = coverTop + ((static_cast<int>(i) - 1) / columns) * (coverH + rowGap);
      paintGridCover(i, Rect{x, y, coverW, coverH});
    }
  } else {
    renderer.drawText(UI_12_FONT_ID, 24, featuredTop + 50, tr(STR_NO_OPEN_BOOK));
  }
  const UIIcon menuIcons[5] = {Folder, Recent, Library, Transfer, Settings};
  const int menuEntries = 4 + (hasOpdsServers ? 1 : 0);
  const int menuWidth = width / menuEntries;
  for (int i = 0; i < menuEntries; ++i) {
    const int x = i * menuWidth + menuWidth / 2 - 16;
    const UIIcon icon = hasOpdsServers ? menuIcons[i] : menuIcons[i >= 2 ? i + 1 : i];
    const uint8_t* bitmap = nullptr;
    switch (icon) {
      case Folder: bitmap = FolderIcon; break;
      case Recent: bitmap = RecentIcon; break;
      case Library: bitmap = LibraryIcon; break;
      case Transfer: bitmap = TransferIcon; break;
      case Settings: bitmap = Settings2Icon; break;
      default: break;
    }
    if (bitmap) renderer.drawIcon(bitmap, x, 713, 32);
    if (selectorIndex == static_cast<int>(recentBooks.size()) + i)
      renderer.drawRect(i * menuWidth + 8, 703, menuWidth - 16, 49, true);
  }
  const auto labels = mappedInput.mapLabels(recentBooks.empty() ? "" : tr(STR_RESUME), tr(STR_SELECT),
                                            tr(STR_DIR_UP), tr(STR_DIR_DOWN));
  GUI.drawButtonHints(renderer, labels.btn1, labels.btn2, labels.btn3, labels.btn4);
  renderer.displayBuffer();
  gridFrameValid = true;
  previousGridSelection = selectorIndex;
  if (!firstRenderDone) {
    firstRenderDone = true;
    requestUpdate();
  } else if (!recentsLoaded && !recentsLoading) {
    recentsLoading = true;
    loadRecentCovers(metrics.homeCoverHeight);
  }
}
