#include "CoverGridBrowserActivity.h"

#include <Bitmap.h>
#include <Epub.h>
#include <Epub/Section.h>
#include <FsHelpers.h>
#include <GfxRenderer.h>
#include <HalStorage.h>
#include <I18n.h>
#include <LibraryBuilder.h>

#include <Arduino.h>
#include <algorithm>
#include <cmath>
#include <cstdio>
#include <memory>
#include <utility>

#include "CrossPointSettings.h"
#include "MappedInputManager.h"
#include "components/UITheme.h"
#include "fontIds.h"
#include "../reader/BookInfoActivity.h"
#include "../util/BmpViewerActivity.h"

namespace {

constexpr int TAB_Y = 12;
constexpr int TAB_H = 34;

constexpr int FEATURED_X = 28;
constexpr int FEATURED_Y = 56;
constexpr int FEATURED_W = 132;
constexpr int FEATURED_H = 220;
constexpr int FEATURED_TEXT_X = 182;

constexpr int GRID_LEFT = 28;
constexpr int GRID_TOP = 288;
constexpr int GRID_W = 132;
constexpr int GRID_H = 220;
constexpr int GRID_GAP_X = 14;
constexpr int GRID_GAP_Y = 6;
constexpr int GRID_SECOND_ROW_EXTRA_Y = 6;
constexpr int GRID_COLS = 3;

constexpr unsigned long LONG_PRESS_MS = 700;
constexpr unsigned long SELECTION_SETTLE_MS = 350;

bool validBmpFile(const std::string& path) {
  if (path.empty()) return false;
  HalFile file;
  if (!Storage.openFileForRead("GRID", path, file)) return false;
  Bitmap bmp(file);
  const bool ok = bmp.parseHeaders() == BmpReaderError::Ok && bmp.getWidth() > 0 && bmp.getHeight() > 0;
  file.close();
  return ok;
}

const char* bookWord() {
  return I18N.getLanguage() == Language::HU ? "könyv" : "books";
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
  static constexpr const char* noSuffix[] = {"előszó", "prológus", "epilógus", "szószedet", "bevezető"};
  for (const char* item : noSuffix) {
    if (lower.rfind(item, 0) == 0) return false;
  }
  return true;
}

int scaledCalibrePageCount(const int referencePages, const GfxRenderer& renderer) {
  if (referencePages <= 0) return 0;
  constexpr float REFERENCE_FONT_PT = 16.0f;
  constexpr int REFERENCE_MARGIN_PX = 10;
  const float fontScale = static_cast<float>(SETTINGS.fontPointSize) / REFERENCE_FONT_PT;
  const float lineScale = SETTINGS.getReaderLineCompression();
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

void drawCenteredIn(GfxRenderer& renderer, const int fontId, const int x, const int width, const int y,
                    const char* text, const EpdFontFamily::Style style = EpdFontFamily::REGULAR) {
  const int textW = renderer.getTextAdvanceX(fontId, text, style);
  renderer.drawText(fontId, x + std::max(0, (width - textW) / 2), y, text, true, style);
}

}  // namespace

CoverGridBrowserActivity::CoverGridBrowserActivity(GfxRenderer& renderer, MappedInputManager& mappedInput)
    : Activity("CoverGridBrowser", renderer, mappedInput) {}

void CoverGridBrowserActivity::onEnter() {
  Activity::onEnter();
  pageStart_ = 0;
  selected_ = 0;
  previewSelected_ = 0;
  activeSortTab_ = 0;
  descendingTabs_ = 3u;  // Recent/New descending, Title/Author ascending.
  thumbnailsReady_ = false;
  thumbnailsLoading_ = false;
  previousSelected_ = -1;
  selectionFastRefresh_ = false;
  sidePageHoldAction_ = 0;
  frontTabHoldAction_ = 0;
  backSortHoldActive_ = false;
  recentOrdinals_.clear();
  newOrdinals_.clear();

  if (!openIndex()) {
    GUI.drawPopup(renderer, I18N.getLanguage() == Language::HU ? "Könyvtár indexelése…" : "Indexing library…");
    if (!rebuildIndex() || !openIndex()) {
      LOG_ERR("GRID", "Cannot open Library index");
    }
  }

  buildReadingShelves();
  loadPage();
  index_.close();
  ensurePageThumbs();
  loadSelectedDetails();
  requestUpdate();
}

void CoverGridBrowserActivity::onExit() {
  optionPopup_.dismiss();
  index_.close();
  books_.clear();
  recentOrdinals_.clear();
  newOrdinals_.clear();
  Activity::onExit();
}

bool CoverGridBrowserActivity::openIndex() {
  index_.close();
  const bool readMetadata = SETTINGS.libraryUseMetadata != 0;
  if (library::isLibraryIndexDirty()) return false;
  if (!index_.open(library::libraryIndexPath())) return false;
  if (index_.header().metadataEnabled != readMetadata) {
    index_.close();
    return false;
  }
  totalBooks_ = static_cast<int>(index_.bookCount());
  return true;
}

bool CoverGridBrowserActivity::rebuildIndex() {
  index_.close();
  library::BuildStats stats;
  return library::buildLibraryIndex("/", stats, SETTINGS.libraryUseMetadata != 0);
}

library::SortOrder CoverGridBrowserActivity::sortOrder() const {
  const bool desc = (descendingTabs_ & static_cast<uint8_t>(1u << activeSortTab_)) != 0;
  if (activeSortTab_ == 2) return desc ? library::SortOrder::TitleDesc : library::SortOrder::TitleAsc;
  if (activeSortTab_ == 3) return desc ? library::SortOrder::AuthorDesc : library::SortOrder::AuthorAsc;
  return desc ? library::SortOrder::RecentDesc : library::SortOrder::RecentAsc;
}

int CoverGridBrowserActivity::totalBooks() const {
  if (activeSortTab_ == 0) return static_cast<int>(recentOrdinals_.size());
  if (activeSortTab_ == 1) return static_cast<int>(newOrdinals_.size());
  return totalBooks_;
}

uint16_t CoverGridBrowserActivity::ordinalForActiveRow(const int row) const {
  if (row < 0) return 0xFFFF;
  const bool desc = (descendingTabs_ & static_cast<uint8_t>(1u << activeSortTab_)) != 0;
  if (activeSortTab_ == 0 || activeSortTab_ == 1) {
    const auto& ordinals = activeSortTab_ == 0 ? recentOrdinals_ : newOrdinals_;
    if (row >= static_cast<int>(ordinals.size())) return 0xFFFF;
    const size_t pos = desc ? ordinals.size() - 1 - static_cast<size_t>(row) : static_cast<size_t>(row);
    return ordinals[pos];
  }
  return index_.ordinalForRow(sortOrder(), static_cast<uint16_t>(row));
}

bool CoverGridBrowserActivity::buildReadingShelves() {
  recentOrdinals_.clear();
  newOrdinals_.clear();
  if (!index_.isOpen()) return false;

  struct RecentEntry {
    uint16_t ordinal;
    uint32_t lastRead;
    uint16_t addedRank;
  };
  std::vector<RecentEntry> recent;
  recent.reserve(totalBooks_);
  newOrdinals_.reserve(totalBooks_);

  // Walk the library in ascending arrival order so unopened books naturally keep
  // the Library index's "added" ordering, while opened books are re-ranked by
  // progress.bin modification time (the time progress was last saved).
  for (int row = 0; row < totalBooks_; ++row) {
    const uint16_t ordinal =
        index_.ordinalForRow(library::SortOrder::RecentAsc, static_cast<uint16_t>(row));
    if (ordinal == 0xFFFF) continue;

    library::ClixRecord record{};
    std::string path;
    if (!index_.readRecord(ordinal, record) || !index_.readPath(record, path)) continue;

    Epub epub(path, "/.crosspoint");
    const std::string progressPath = epub.getCachePath() + "/progress.bin";
    HalFile progressFile;
    if (!Storage.openFileForRead("GRID", progressPath, progressFile)) {
      newOrdinals_.push_back(ordinal);
      continue;
    }
    const uint32_t lastRead = progressFile.modificationTime();
    progressFile.close();
    recent.push_back({ordinal, lastRead, static_cast<uint16_t>(row)});
  }

  std::stable_sort(recent.begin(), recent.end(), [](const RecentEntry& a, const RecentEntry& b) {
    if (a.lastRead != b.lastRead) return a.lastRead < b.lastRead;
    return a.addedRank < b.addedRank;
  });
  recentOrdinals_.reserve(recent.size());
  for (const auto& entry : recent) recentOrdinals_.push_back(entry.ordinal);
  return true;
}

int CoverGridBrowserActivity::globalSelection() const {
  if (books_.empty()) return -1;
  return pageStart_ + std::clamp(selected_, 0, static_cast<int>(books_.size()) - 1);
}

int CoverGridBrowserActivity::thumbHeight() const {
  // One thumbnail size feeds both the six cells and the highlighted preview.
  // This keeps the page to six unique cover cache files.
  return 220;
}

bool CoverGridBrowserActivity::loadPage() {
  books_.clear();
  thumbnailsReady_ = false;
  if (!index_.isOpen()) return false;

  const int total = totalBooks();
  if (total <= 0) {
    pageStart_ = 0;
    selected_ = 0;
    return true;
  }

  pageStart_ = std::clamp(pageStart_, 0, ((total - 1) / PAGE_SIZE) * PAGE_SIZE);
  const int count = std::min(PAGE_SIZE, total - pageStart_);
  books_.reserve(count);

  for (int i = 0; i < count; ++i) {
    const uint16_t ordinal = ordinalForActiveRow(pageStart_ + i);
    if (ordinal == 0xFFFF) continue;

    library::ClixRecord record{};
    if (!index_.readRecord(ordinal, record)) continue;

    GridBook book;
    if (!index_.readPath(record, book.path)) continue;
    if (!index_.readTitle(record, book.title) || book.title.empty()) index_.readName(record, book.title);
    index_.readAuthor(record, book.author);
    if (book.title.empty()) book.title = book.path;

    Epub epub(book.path, "/.crosspoint");
    book.thumbPath = epub.getThumbBmpPath(thumbHeight());
    books_.push_back(std::move(book));
  }

  if (books_.empty()) {
    selected_ = 0;
  } else {
    selected_ = std::clamp(selected_, 0, static_cast<int>(books_.size()) - 1);
  }
  return true;
}

bool CoverGridBrowserActivity::ensurePageThumbs() {
  if (books_.empty()) {
    thumbnailsReady_ = true;
    return true;
  }

  bool allValid = true;
  for (const auto& book : books_) {
    if (!validBmpFile(book.thumbPath)) {
      allValid = false;
      break;
    }
  }
  if (allValid) {
    thumbnailsReady_ = true;
    return true;
  }

  thumbnailsLoading_ = true;
  Rect popup = GUI.drawPopup(renderer, I18N.getLanguage() == Language::HU ? "Borítók betöltése…" : "Loading covers…");

  bool ok = true;
  for (size_t i = 0; i < books_.size(); ++i) {
    auto& book = books_[i];
    if (!validBmpFile(book.thumbPath)) {
      Epub epub(book.path, "/.crosspoint");
      bool loaded = epub.load(false, true);
      if (!loaded) loaded = epub.load(true, true);
      if (!loaded || !epub.generateThumbBmp(thumbHeight())) {
        LOG_ERR("GRID", "Cannot generate thumbnail: %s", book.path.c_str());
        ok = false;
      }
      book.thumbPath = epub.getThumbBmpPath(thumbHeight());
    }
    GUI.fillPopupProgress(renderer, popup,
                          10 + static_cast<int>((90u * static_cast<unsigned>(i + 1)) /
                                                std::max<size_t>(1, books_.size())));
  }

  thumbnailsReady_ = true;
  thumbnailsLoading_ = false;
  return ok;
}

void CoverGridBrowserActivity::clearSelectedDetails() {
  featuredProgressTenths_ = -1;
  featuredCurrentPage_ = 0;
  featuredTotalPages_ = 0;
  featuredSeries_.clear();
  featuredChapterTitle_.clear();
}

void CoverGridBrowserActivity::loadSelectedDetails() {
  clearSelectedDetails();
  if (previewSelected_ < 0 || previewSelected_ >= static_cast<int>(books_.size())) return;

  auto epub = std::make_shared<Epub>(books_[previewSelected_].path, "/.crosspoint");
  if (!epub->load(false, true) || epub->getBookSize() == 0) return;

  Epub::BookInfo info;
  int calibrePageCount = 0;
  if (epub->readBookInfo(info)) {
    calibrePageCount = info.calibrePageCount;
    if (!info.series.empty()) {
      featuredSeries_ = info.series;
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
        featuredSeries_ += " #" + seriesIndex;
      }
    }
  }

  HalFile progressFile;
  if (!Storage.openFileForRead("GRID", epub->getCachePath() + "/progress.bin", progressFile)) return;
  uint8_t data[10] = {};
  const int dataSize = progressFile.read(data, sizeof(data));
  progressFile.close();
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
  featuredProgressTenths_ = static_cast<int>(progress * 1000.0f + 0.5f);

  const int tocIndex = epub->getTocIndexForSpineIndex(spineIndex);
  if (tocIndex >= 0 && tocIndex < epub->getTocItemsCount()) {
    featuredChapterTitle_ = trimCopy(epub->getTocItem(tocIndex).title);
    std::string foldedChapter = asciiLowerCopy(featuredChapterTitle_);
    const size_t splitPos = foldedChapter.find("split");
    if (splitPos != std::string::npos) {
      featuredChapterTitle_ = trimCopy(featuredChapterTitle_.substr(0, splitPos));
      foldedChapter = asciiLowerCopy(featuredChapterTitle_);
    }
    if (featuredChapterTitle_.empty() ||
        foldedChapter.rfind("index split", 0) == 0 ||
        foldedChapter.rfind("index_split", 0) == 0 ||
        isTechnicalPartTitle(foldedChapter) ||
        isHiddenChapterTitle(foldedChapter)) {
      featuredChapterTitle_.clear();
    }
  }

  if (calibrePageCount > 0) {
    featuredTotalPages_ = scaledCalibrePageCount(calibrePageCount, renderer);
    if (featuredTotalPages_ > 0) {
      featuredCurrentPage_ = std::clamp(
          1 + static_cast<int>(std::lround(progress * static_cast<float>(featuredTotalPages_ - 1))),
          1, featuredTotalPages_);
    }
    return;
  }

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
    featuredCurrentPage_ = std::min(total, pagesBefore + std::max(0, pageIndex) + 1);
    featuredTotalPages_ = total;
  }
}

bool CoverGridBrowserActivity::reopenAfterChild() {
  // The page metadata and six thumbnail paths stay resident while the child
  // activity is open. Keep the Library index closed so cover/info file access
  // never competes for the SD reader handle.
  thumbnailsReady_ = true;
  loadSelectedDetails();
  requestUpdate();
  return true;
}

void CoverGridBrowserActivity::selectSortTab(const int tab, const bool toggleIfActive) {
  if (tab < 0 || tab > 2) return;
  if (toggleIfActive && tab == activeSortTab_) {
    descendingTabs_ ^= static_cast<uint8_t>(1u << tab);
  } else {
    activeSortTab_ = tab;
  }
  pageStart_ = 0;
  selected_ = 0;
  previewSelected_ = 0;
  if (!openIndex()) return;
  loadPage();
  index_.close();
  ensurePageThumbs();
  loadSelectedDetails();
  requestUpdate();
}

void CoverGridBrowserActivity::toggleSortDirection() {
  descendingTabs_ ^= static_cast<uint8_t>(1u << activeSortTab_);
  pageStart_ = 0;
  selected_ = 0;
  previewSelected_ = 0;
  if (!openIndex()) return;
  loadPage();
  index_.close();
  ensurePageThumbs();
  loadSelectedDetails();
  requestUpdate();
}

void CoverGridBrowserActivity::stepSortTab(const int delta) {
  int tab = (activeSortTab_ + delta) % 3;
  if (tab < 0) tab += 3;
  selectSortTab(tab, false);
}

void CoverGridBrowserActivity::moveSelection(const int delta) {
  const int total = totalBooks();
  const int current = globalSelection();
  if (total <= 0 || current < 0) return;

  const int next = std::clamp(current + delta, 0, total - 1);
  if (next == current) return;
  const int nextPage = (next / PAGE_SIZE) * PAGE_SIZE;
  if (nextPage != pageStart_) {
    pageStart_ = nextPage;
    selected_ = next - pageStart_;
    previewSelected_ = selected_;
    previousSelected_ = -1;
    selectionFastRefresh_ = false;
    if (!openIndex()) return;
    loadPage();
    index_.close();
    ensurePageThumbs();
    loadSelectedDetails();
    requestUpdate();
    return;
  }

  previousSelected_ = selected_;
  selected_ = next - pageStart_;

  // CPHUN-202: cursor movement never changes the featured preview.
  // Keep the six covers and confirmed preview static; redraw only the frame.
  selectionFastRefresh_ = true;
  requestUpdate();
}

void CoverGridBrowserActivity::stepPage(const int delta) {
  const int total = totalBooks();
  if (total <= 0) return;
  const int maxStart = ((total - 1) / PAGE_SIZE) * PAGE_SIZE;
  const int nextStart = std::clamp(pageStart_ + delta * PAGE_SIZE, 0, maxStart);
  if (nextStart == pageStart_) return;
  pageStart_ = nextStart;
  selected_ = 0;
  previewSelected_ = 0;
  if (!openIndex()) return;
  loadPage();
  index_.close();
  ensurePageThumbs();
  loadSelectedDetails();
  requestUpdate();
}

std::shared_ptr<Epub> CoverGridBrowserActivity::loadSelectedEpub() {
  if (selected_ < 0 || selected_ >= static_cast<int>(books_.size())) return {};
  const std::string path = books_[selected_].path;

  auto epub = std::make_shared<Epub>(path, "/.crosspoint");
  bool loaded = epub->load(false, true);
  if (!loaded) loaded = epub->load(true, true);
  if (!loaded) {
    LOG_ERR("GRID", "Cannot load selected EPUB: %s", path.c_str());
    return {};
  }
  return epub;
}

void CoverGridBrowserActivity::openSelectedBook() {
  if (selected_ < 0 || selected_ >= static_cast<int>(books_.size())) return;
  const std::string path = books_[selected_].path;
  index_.close();
  activityManager.goToReader(path);
}

void CoverGridBrowserActivity::openSelectedInfo(const bool metadata) {
  auto epub = loadSelectedEpub();
  if (!epub) {
    requestUpdate();
    return;
  }
  startActivityForResult(
      std::make_unique<BookInfoActivity>(renderer, mappedInput, epub,
                                         metadata ? BookInfoActivity::Page::Metadata : BookInfoActivity::Page::Description),
      [this](const ActivityResult&) { reopenAfterChild(); });
}

void CoverGridBrowserActivity::openSelectedCover() {
  auto epub = loadSelectedEpub();
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
                         [this](const ActivityResult&) { reopenAfterChild(); });
}

void CoverGridBrowserActivity::showSelectedOptions() {
  if (selected_ < 0 || selected_ >= static_cast<int>(books_.size())) return;
  static constexpr const char* OPTIONS_HU[] = {"Fülszöveg", "Metaadatok", "Borító megjelenítése", "Megnyitás"};
  static constexpr const char* OPTIONS_EN[] = {"Description", "Metadata", "Show cover", "Open"};
  const char* const* options = I18N.getLanguage() == Language::HU ? OPTIONS_HU : OPTIONS_EN;
  optionPopup_.showMultilineTitle(books_[selected_].title.c_str(), options, 4, 0, [this](const int choice) {
    if (choice == 0) openSelectedInfo(false);
    else if (choice == 1) openSelectedInfo(true);
    else if (choice == 2) openSelectedCover();
    else if (choice == 3) openSelectedBook();
  });
  requestUpdate();
}

bool CoverGridBrowserActivity::hitSortTab(const int x, const int y, int& tab) const {
  if (y < TAB_Y || y >= TAB_Y + TAB_H) return false;
  const int width = renderer.getScreenWidth();
  tab = std::clamp((x * 3) / std::max(1, width), 0, 2);
  return true;
}

int CoverGridBrowserActivity::hitGridCover(const int x, const int y) const {
  for (int i = 0; i < static_cast<int>(books_.size()); ++i) {
    const int col = i % GRID_COLS;
    const int row = i / GRID_COLS;
    const int rx = GRID_LEFT + col * (GRID_W + GRID_GAP_X);
    const int ry = GRID_TOP + row * (GRID_H + GRID_GAP_Y) + (row == 1 ? GRID_SECOND_ROW_EXTRA_Y : 0);
    if (x >= rx && x < rx + GRID_W && y >= ry && y < ry + GRID_H) return i;
  }
  return -1;
}

bool CoverGridBrowserActivity::hitFeaturedCover(const int x, const int y) const {
  return x >= FEATURED_X && x < FEATURED_X + FEATURED_W && y >= FEATURED_Y && y < FEATURED_Y + FEATURED_H;
}

void CoverGridBrowserActivity::loop() {
  if (optionPopup_.isActive()) {
    optionPopup_.handleInput(mappedInput, [this] { requestUpdate(); });
    return;
  }

  if (mappedInput.wasLongPressed(MappedInputManager::Button::Confirm, LONG_PRESS_MS)) {
    showSelectedOptions();
    return;
  }
  if (mappedInput.wasLongPressed(MappedInputManager::Button::Back, LONG_PRESS_MS)) {
    toggleSortDirection();
    return;
  }

  // CPHUN-208: front Left/Right have dual behavior.
  // Short release remains NavPrevious/NavNext (one cover). A long hold
  // switches sort tabs. Latch through release so it cannot also move a cover.
  if (frontTabHoldAction_ != 0) {
    const auto heldFront = frontTabHoldAction_ < 0 ? MappedInputManager::Button::Left
                                                   : MappedInputManager::Button::Right;
    if (mappedInput.wasReleased(heldFront)) frontTabHoldAction_ = 0;
    return;
  }
  if (mappedInput.isPressed(MappedInputManager::Button::Left) &&
      mappedInput.getHeldTime() >= LONG_PRESS_MS) {
    frontTabHoldAction_ = -1;
    stepSortTab(-1);
    return;
  }
  if (mappedInput.isPressed(MappedInputManager::Button::Right) &&
      mappedInput.getHeldTime() >= LONG_PRESS_MS) {
    frontTabHoldAction_ = 1;
    stepSortTab(1);
    return;
  }

  // CPHUN-202: side buttons have dual behavior in the 6+1 grid.
  // Short release falls through to NavPrevious/NavNext (one cover).
  // Holding past LONG_PRESS_MS changes a whole six-book page. Keep a latch
  // until release so the same physical release cannot also move one cover.
  if (sidePageHoldAction_ != 0) {
    const auto heldButton = sidePageHoldAction_ < 0 ? MappedInputManager::Button::PageBack
                                                    : MappedInputManager::Button::PageForward;
    if (mappedInput.wasReleased(heldButton)) sidePageHoldAction_ = 0;
    return;
  }
  if (mappedInput.isPressed(MappedInputManager::Button::PageBack) &&
      mappedInput.getHeldTime() >= LONG_PRESS_MS) {
    sidePageHoldAction_ = -1;
    stepPage(-1);
    return;
  }
  if (mappedInput.isPressed(MappedInputManager::Button::PageForward) &&
      mappedInput.getHeldTime() >= LONG_PRESS_MS) {
    sidePageHoldAction_ = 1;
    stepPage(1);
    return;
  }

  if (mappedInput.wasReleased(MappedInputManager::Button::Back)) {
    finish();
    return;
  }
  if (mappedInput.wasReleased(MappedInputManager::Button::NavPrevious)) {
    moveSelection(-1);
    return;
  }
  if (mappedInput.wasReleased(MappedInputManager::Button::NavNext)) {
    moveSelection(1);
    return;
  }
  if (mappedInput.wasReleased(MappedInputManager::Button::Confirm)) {
    if (previewSelected_ != selected_) {
      previewSelected_ = selected_;
      loadSelectedDetails();
      selectionFastRefresh_ = false;
      previousSelected_ = -1;
      requestUpdate();
    } else {
      openSelectedBook();
    }
    return;
  }

  int x = -1;
  int y = -1;
  if (mappedInput.wasScreenLongPress(x, y)) {
    const int hit = hitGridCover(x, y);
    if (hit >= 0) {
      selected_ = hit;
      showSelectedOptions();
      return;
    }
    if (hitFeaturedCover(x, y)) {
      showSelectedOptions();
      return;
    }
  }

  if (mappedInput.wasScreenTapped(x, y)) {
    int tab = -1;
    if (hitSortTab(x, y, tab)) {
      selectSortTab(tab, true);
      return;
    }
    const int hit = hitGridCover(x, y);
    if (hit >= 0) {
      if (selected_ == hit && previewSelected_ == hit) {
        openSelectedBook();
      } else if (selected_ == hit) {
        previewSelected_ = hit;
        loadSelectedDetails();
        selectionFastRefresh_ = false;
        previousSelected_ = -1;
        requestUpdate();
      } else {
        previousSelected_ = selected_;
        selected_ = hit;
        selectionFastRefresh_ = true;
        requestUpdate();
      }
      return;
    }
    if (hitFeaturedCover(x, y)) {
      if (previewSelected_ >= 0 && previewSelected_ < static_cast<int>(books_.size())) {
        const int saved = selected_;
        selected_ = previewSelected_;
        openSelectedBook();
        selected_ = saved;
      }
      return;
    }
  }

  const auto swipe = mappedInput.wasSwipe();
  if (swipe == MappedInputManager::SwipeDir::Left) {
    stepPage(1);
    return;
  }
  if (swipe == MappedInputManager::SwipeDir::Right && !mappedInput.wasBackGesture()) {
    stepPage(-1);
    return;
  }

}

void CoverGridBrowserActivity::paintCover(const GridBook& book, const Rect rect, const bool selectedFrame) {
  bool drawn = false;
  if (validBmpFile(book.thumbPath)) {
    HalFile file;
    if (Storage.openFileForRead("GRID", book.thumbPath, file)) {
      Bitmap bmp(file);
      if (bmp.parseHeaders() == BmpReaderError::Ok && bmp.getWidth() > 0 && bmp.getHeight() > 0) {
        const float imageRatio = static_cast<float>(bmp.getWidth()) / static_cast<float>(bmp.getHeight());
        const float targetRatio = static_cast<float>(rect.width) / static_cast<float>(rect.height);
        float cropX = 0.0f;
        float cropY = 0.0f;
        if (imageRatio > targetRatio) {
          cropX = std::max(0.0f, 1.0f - targetRatio / imageRatio);
        } else if (imageRatio < targetRatio) {
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
    const auto title = renderer.truncatedText(UI_10_FONT_ID, book.title.c_str(), rect.width - 12);
    renderer.drawText(UI_10_FONT_ID, rect.x + 6, rect.y + rect.height / 2, title.c_str());
  }
  if (selectedFrame) {
    // Strong e-ink selection marker: a white separator keeps the marker
    // distinct even when the cover itself has a dark edge.
    renderer.drawRect(rect.x - 3, rect.y - 3, rect.width + 6, rect.height + 6, 2, false);
    renderer.drawRect(rect.x - 4, rect.y - 4, rect.width + 8, rect.height + 8, 2, true);
  }
}

void CoverGridBrowserActivity::renderGrayscaleCovers() {
  // CPHUN-195: preserve the already-rendered BW UI while replacing only
  // the cover rectangles with Absolute/B 2-bit grayscale.
  const bool stripSupported = renderer.supportsStripGrayscale();
  bool absolute = stripSupported &&
                  renderer.grayscaleCapabilities(HalDisplay::GrayscaleMode::Absolute).supported();

  if (absolute) {
    if (!renderer.displayGrayscaleBase(HalDisplay::GrayscaleMode::Absolute)) absolute = false;
  }
  if (!absolute) {
    renderer.displayGrayscaleBase(HalDisplay::HALF_REFRESH);
  }

  auto drawBookPlane = [this](const GridBook& book, const Rect rect) {
    if (!validBmpFile(book.thumbPath)) return;

    HalFile file;
    if (!Storage.openFileForRead("GRID", book.thumbPath, file)) return;
    Bitmap bmp(file);
    if (bmp.parseHeaders() != BmpReaderError::Ok || bmp.getWidth() <= 0 || bmp.getHeight() <= 0) {
      file.close();
      return;
    }

    const float imageRatio = static_cast<float>(bmp.getWidth()) / static_cast<float>(bmp.getHeight());
    const float targetRatio = static_cast<float>(rect.width) / static_cast<float>(rect.height);
    float cropX = 0.0f;
    float cropY = 0.0f;
    if (imageRatio > targetRatio)
      cropX = std::max(0.0f, 1.0f - targetRatio / imageRatio);
    else if (imageRatio < targetRatio)
      cropY = std::max(0.0f, 1.0f - imageRatio / targetRatio);

    renderer.drawBitmap(bmp, rect.x, rect.y, rect.width, rect.height, cropX, cropY);
    file.close();
  };

  auto drawAllCoverPlanes = [this, &drawBookPlane]() {
    if (books_.empty()) return;

    const GridBook& selectedBook = books_[std::clamp(previewSelected_, 0, static_cast<int>(books_.size()) - 1)];
    drawBookPlane(selectedBook, Rect{FEATURED_X, FEATURED_Y, FEATURED_W, FEATURED_H});

    for (int i = 0; i < static_cast<int>(books_.size()); ++i) {
      const int col = i % GRID_COLS;
      const int row = i / GRID_COLS;
      const int x = GRID_LEFT + col * (GRID_W + GRID_GAP_X);
      const int y = GRID_TOP + row * (GRID_H + GRID_GAP_Y) + (row == 1 ? GRID_SECOND_ROW_EXTRA_Y : 0);
      drawBookPlane(books_[i], Rect{x, y, GRID_W, GRID_H});
    }
  };

  if (absolute && renderer.storeBwBuffer()) {
    renderer.setRenderMode(GfxRenderer::GRAYSCALE_LSB);
    drawAllCoverPlanes();
    renderer.copyGrayscaleLsbBuffers();

    renderer.restoreBwBuffer(false, false);

    renderer.setRenderMode(GfxRenderer::GRAYSCALE_MSB);
    drawAllCoverPlanes();
    renderer.copyGrayscaleMsbBuffers();

    renderer.displayGrayBuffer();
    renderer.setRenderMode(GfxRenderer::BW);
    renderer.restoreBwBuffer(false, true);
    return;
  }

  if (absolute) {
    constexpr int STRIP_ROWS = 128;
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
          memcpy(scratch, bwPage + static_cast<size_t>(y) * rowBytes, static_cast<size_t>(rows) * rowBytes);
          renderer.beginStripTarget(scratch, y, rows);
          drawAllCoverPlanes();
          renderer.endStripTarget();
          renderer.writeGrayscalePlaneStrip(plane == GfxRenderer::GRAYSCALE_LSB, scratch, y, rows);
        }
      }
      free(scratch);
      renderer.displayGrayBuffer();
      renderer.setRenderMode(GfxRenderer::BW);
      return;
    }
    if (scratch != nullptr) free(scratch);
    renderer.setRenderMode(GfxRenderer::BW);
    return;
  }

  renderer.clearScreen(0x00);
  renderer.setRenderMode(GfxRenderer::GRAYSCALE_LSB);
  drawAllCoverPlanes();
  renderer.copyGrayscaleLsbBuffers();

  renderer.clearScreen(0x00);
  renderer.setRenderMode(GfxRenderer::GRAYSCALE_MSB);
  drawAllCoverPlanes();
  renderer.copyGrayscaleMsbBuffers();

  renderer.displayGrayBuffer();
  renderer.setRenderMode(GfxRenderer::BW);
}

void CoverGridBrowserActivity::render(RenderLock&&) {
  const int width = renderer.getScreenWidth();
  const int height = renderer.getScreenHeight();

  if (selectionFastRefresh_ && previousSelected_ >= 0 &&
      previousSelected_ < static_cast<int>(books_.size()) &&
      selected_ >= 0 && selected_ < static_cast<int>(books_.size())) {
    auto coverRect = [](const int index) {
      const int col = index % GRID_COLS;
      const int row = index / GRID_COLS;
      return Rect{GRID_LEFT + col * (GRID_W + GRID_GAP_X),
                  GRID_TOP + row * (GRID_H + GRID_GAP_Y) + (row == 1 ? GRID_SECOND_ROW_EXTRA_Y : 0), GRID_W, GRID_H};
    };

    const Rect oldRect = coverRect(previousSelected_);
    const Rect newRect = coverRect(selected_);
    renderer.drawRect(oldRect.x - 4, oldRect.y - 4, oldRect.width + 8, oldRect.height + 8, 4, false);
    renderer.drawRect(newRect.x - 3, newRect.y - 3, newRect.width + 6, newRect.height + 6, 2, false);
    renderer.drawRect(newRect.x - 4, newRect.y - 4, newRect.width + 8, newRect.height + 8, 2, true);

    // Same model as the restored 3+1 view: send the already-rendered framebuffer
    // without reopening or decoding any cover bitmap.
    renderer.displayBuffer();
    selectionFastRefresh_ = false;
    previousSelected_ = selected_;
    return;
  }

  renderer.clearScreen();
  static constexpr const char* HU_TABS[] = {"Legutóbbi", "Címek", "Szerzők"};
  static constexpr const char* EN_TABS[] = {"Recent", "Title", "Author"};
  const char* const* tabs = I18N.getLanguage() == Language::HU ? HU_TABS : EN_TABS;
  for (int i = 0; i < 3; ++i) {
    const int x = i * width / 3;
    const int w = (i + 1) * width / 3 - x;
    const int visualX = x + (i == 0 ? 14 : (i == 2 ? -12 : 0));
    drawCenteredIn(renderer, UI_10_FONT_ID, visualX, w, TAB_Y + 5, tabs[i],
                   i == activeSortTab_ ? EpdFontFamily::BOLD : EpdFontFamily::REGULAR);
    if (i == activeSortTab_) {
      renderer.drawLine(visualX + 10, TAB_Y + TAB_H - 2, visualX + w - 10, TAB_Y + TAB_H - 2, true);
      const bool desc = (descendingTabs_ & static_cast<uint8_t>(1u << i)) != 0;
      renderer.drawText(UI_10_FONT_ID, visualX + w - 20, TAB_Y + 5, desc ? "↓" : "↑");
    }
  }

  if (!books_.empty()) {
    const GridBook& selectedBook = books_[std::clamp(selected_, 0, static_cast<int>(books_.size()) - 1)];
    paintCover(selectedBook, Rect{FEATURED_X, FEATURED_Y, FEATURED_W, FEATURED_H}, false);

    const int textW = std::max(40, width - FEATURED_TEXT_X - 22);
    const auto titleLines = renderer.wrappedText(UI_12_FONT_ID, selectedBook.title.c_str(), textW, 3);
    int y = FEATURED_Y + FEATURED_INFO_OFFSET_Y;
    for (const auto& line : titleLines) {
      renderer.drawText(UI_12_FONT_ID, FEATURED_TEXT_X, y, line.c_str(), true, EpdFontFamily::BOLD);
      y += renderer.getLineHeight(UI_12_FONT_ID);
    }
    if (!selectedBook.author.empty()) {
      y += 4;
      std::string author = selectedBook.author;
      if (I18N.getLanguage() == Language::HU) {
        const size_t comma = author.find(',');
        if (comma != std::string::npos) {
          author.erase(comma, 1);
          while (comma < author.size() && author[comma] == ' ') author.erase(comma, 1);
          author.insert(comma, " ");
        }
      }
      author = renderer.truncatedText(UI_10_FONT_ID, author.c_str(), textW);
      renderer.drawText(UI_10_FONT_ID, FEATURED_TEXT_X, y, author.c_str());
      y += renderer.getLineHeight(UI_10_FONT_ID) + 4;
    }
    if (!featuredSeries_.empty()) {
      const auto series = renderer.truncatedText(UI_10_FONT_ID, featuredSeries_.c_str(), textW);
      renderer.drawText(UI_10_FONT_ID, FEATURED_TEXT_X, y, series.c_str());
      y += renderer.getLineHeight(UI_10_FONT_ID) + 4;
    }
    if (!featuredChapterTitle_.empty()) {
      std::string chapter = featuredChapterTitle_;
      const std::string folded = asciiLowerCopy(chapter);
      if (chapterTitleNeedsSuffix(folded)) {
        chapter += I18N.getLanguage() == Language::HU ? " fejezet" : " chapter";
      }
      chapter = renderer.truncatedText(UI_10_FONT_ID, chapter.c_str(), textW);
      renderer.drawText(UI_10_FONT_ID, FEATURED_TEXT_X, y, chapter.c_str());
      y += renderer.getLineHeight(UI_10_FONT_ID) + 4;
    }
    if (featuredProgressTenths_ >= 0) {
      char progressText[48];
      const int whole = featuredProgressTenths_ / 10;
      const int decimal = featuredProgressTenths_ % 10;
      const char decimalSep = I18N.getLanguage() == Language::HU ? ',' : '.';
      if (featuredTotalPages_ > 0 && featuredCurrentPage_ > 0) {
        snprintf(progressText, sizeof(progressText), "%d%c%d%% · %d / %d %s", whole, decimalSep, decimal,
                 featuredCurrentPage_, featuredTotalPages_,
                 I18N.getLanguage() == Language::HU ? "oldal" : "pages");
      } else {
        snprintf(progressText, sizeof(progressText), "%d%c%d%%", whole, decimalSep, decimal);
      }
      renderer.drawText(UI_10_FONT_ID, FEATURED_TEXT_X, y, progressText);
      constexpr int progressBarHeight = 8;
      const int progressBarY = y + renderer.getLineHeight(UI_10_FONT_ID) + 4;
      renderer.fillRect(FEATURED_TEXT_X, progressBarY, textW, progressBarHeight, false);
      renderer.drawRect(FEATURED_TEXT_X, progressBarY, textW, progressBarHeight, true);
      const int innerWidth = std::max(0, textW - 2);
      const int fillWidth = (innerWidth * std::clamp(featuredProgressTenths_, 0, 1000) + 500) / 1000;
      if (fillWidth > 0) {
        renderer.fillRectDither(FEATURED_TEXT_X + 1, progressBarY + 1, fillWidth, progressBarHeight - 2,
                                Color::DarkGray);
      }
    }

    for (int i = 0; i < static_cast<int>(books_.size()); ++i) {
      const int col = i % GRID_COLS;
      const int row = i / GRID_COLS;
      const int x = GRID_LEFT + col * (GRID_W + GRID_GAP_X);
      const int gy = GRID_TOP + row * (GRID_H + GRID_GAP_Y) + (row == 1 ? GRID_SECOND_ROW_EXTRA_Y : 0);
      paintCover(books_[i], Rect{x, gy, GRID_W, GRID_H}, i == selected_);
    }
  } else {
    drawCenteredIn(renderer, UI_12_FONT_ID, 20, width - 40, FEATURED_Y + 80,
                   I18N.getLanguage() == Language::HU ? "Nincs indexelt EPUB." : "No indexed EPUB files.");
  }

  const bool previewMatchesCursor = previewSelected_ == selected_;
  const auto labels = mappedInput.mapLabels(
      I18N.getLanguage() == Language::HU ? "Vissza" : "Back",
      previewMatchesCursor ? (I18N.getLanguage() == Language::HU ? "Megnyitás" : "Open")
                           : (I18N.getLanguage() == Language::HU ? "Előnézet" : "Preview"),
      "<", ">");
  GUI.drawButtonHints(renderer, labels.btn1, labels.btn2, labels.btn3, labels.btn4);

  if (optionPopup_.isActive()) {
    optionPopup_.processRender(renderer, mappedInput);
    return;
  }

  renderer.displayBuffer();
  previousSelected_ = selected_;
}

