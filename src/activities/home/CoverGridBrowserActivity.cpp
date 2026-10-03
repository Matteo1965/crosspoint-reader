#include "CoverGridBrowserActivity.h"

#include <Bitmap.h>
#include <Epub.h>
#include <FsHelpers.h>
#include <GfxRenderer.h>
#include <HalStorage.h>
#include <I18n.h>
#include <LibraryBuilder.h>

#include <algorithm>
#include <cmath>
#include <memory>
#include <utility>

#include "CrossPointSettings.h"
#include "MappedInputManager.h"
#include "components/UITheme.h"
#include "fontIds.h"
#include "reader/BookInfoActivity.h"
#include "util/BmpViewerActivity.h"

namespace {

constexpr int HEADER_TITLE_Y = 8;
constexpr int TAB_Y = 36;
constexpr int TAB_H = 34;

constexpr int FEATURED_X = 24;
constexpr int FEATURED_Y = 82;
constexpr int FEATURED_W = 126;
constexpr int FEATURED_H = 196;
constexpr int FEATURED_TEXT_X = 170;

constexpr int GRID_LEFT = 28;
constexpr int GRID_TOP = 316;
constexpr int GRID_W = 132;
constexpr int GRID_H = 174;
constexpr int GRID_GAP_X = 14;
constexpr int GRID_GAP_Y = 18;
constexpr int GRID_COLS = 3;

constexpr int PAGE_READOUT_Y = 704;
constexpr unsigned long LONG_PRESS_MS = 700;

bool validBmpFile(const std::string& path) {
  if (path.empty()) return false;
  HalFile file;
  if (!Storage.openFileForRead("GRID", path, file)) return false;
  Bitmap bmp(file);
  const bool ok = bmp.parseHeaders() == BmpReaderError::Ok && bmp.getWidth() > 0 && bmp.getHeight() > 0;
  file.close();
  return ok;
}

const char* gridTitle() {
  return I18N.getLanguage() == Language::HU ? "Borítórács" : "Cover Grid";
}

const char* bookWord() {
  return I18N.getLanguage() == Language::HU ? "könyv" : "books";
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
  activeSortTab_ = 0;
  descendingTabs_ = 1u;  // Recent descending, Title/Author ascending.
  thumbnailsReady_ = false;
  thumbnailsLoading_ = false;

  if (!openIndex()) {
    GUI.drawPopup(renderer, I18N.getLanguage() == Language::HU ? "Könyvtár indexelése…" : "Indexing library…");
    if (!rebuildIndex() || !openIndex()) {
      LOG_ERR("GRID", "Cannot open Library index");
    }
  }

  loadPage();
  ensurePageThumbs();
  requestUpdate();
}

void CoverGridBrowserActivity::onExit() {
  optionPopup_.dismiss();
  index_.close();
  books_.clear();
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
  return true;
}

bool CoverGridBrowserActivity::rebuildIndex() {
  index_.close();
  library::BuildStats stats;
  return library::buildLibraryIndex("/", stats, SETTINGS.libraryUseMetadata != 0);
}

library::SortOrder CoverGridBrowserActivity::sortOrder() const {
  const bool desc = (descendingTabs_ & static_cast<uint8_t>(1u << activeSortTab_)) != 0;
  if (activeSortTab_ == 1) return desc ? library::SortOrder::TitleDesc : library::SortOrder::TitleAsc;
  if (activeSortTab_ == 2) return desc ? library::SortOrder::AuthorDesc : library::SortOrder::AuthorAsc;
  return desc ? library::SortOrder::RecentDesc : library::SortOrder::RecentAsc;
}

int CoverGridBrowserActivity::totalBooks() const { return index_.isOpen() ? static_cast<int>(index_.bookCount()) : 0; }

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
    const uint16_t ordinal = index_.ordinalForRow(sortOrder(), static_cast<uint16_t>(pageStart_ + i));
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
  index_.close();

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

  if (!openIndex()) {
    LOG_ERR("GRID", "Cannot reopen index after thumbnail generation");
    ok = false;
  }

  thumbnailsReady_ = true;
  thumbnailsLoading_ = false;
  return ok;
}

bool CoverGridBrowserActivity::reopenAfterChild() {
  if (!openIndex()) {
    if (!rebuildIndex() || !openIndex()) return false;
  }
  loadPage();
  thumbnailsReady_ = true;
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
  loadPage();
  ensurePageThumbs();
  requestUpdate();
}

void CoverGridBrowserActivity::toggleSortDirection() {
  descendingTabs_ ^= static_cast<uint8_t>(1u << activeSortTab_);
  pageStart_ = 0;
  selected_ = 0;
  loadPage();
  ensurePageThumbs();
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
  const int nextPage = (next / PAGE_SIZE) * PAGE_SIZE;
  if (nextPage != pageStart_) {
    pageStart_ = nextPage;
    selected_ = next - pageStart_;
    loadPage();
    ensurePageThumbs();
  } else {
    selected_ = next - pageStart_;
  }
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
  loadPage();
  ensurePageThumbs();
  requestUpdate();
}

std::shared_ptr<Epub> CoverGridBrowserActivity::loadSelectedEpub() {
  if (selected_ < 0 || selected_ >= static_cast<int>(books_.size())) return {};
  const std::string path = books_[selected_].path;

  index_.close();
  auto epub = std::make_shared<Epub>(path, "/.crosspoint");
  bool loaded = epub->load(false, true);
  if (!loaded) loaded = epub->load(true, true);
  if (!loaded) {
    LOG_ERR("GRID", "Cannot load selected EPUB: %s", path.c_str());
    openIndex();
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
    openIndex();
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
    const int ry = GRID_TOP + row * (GRID_H + GRID_GAP_Y);
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
  if (mappedInput.wasLongPressed(MappedInputManager::Button::NavPrevious, LONG_PRESS_MS)) {
    stepSortTab(-1);
    return;
  }
  if (mappedInput.wasLongPressed(MappedInputManager::Button::NavNext, LONG_PRESS_MS)) {
    stepSortTab(1);
    return;
  }

  if (mappedInput.wasReleased(MappedInputManager::Button::Back)) {
    finish();
    return;
  }
  if (mappedInput.wasReleased(MappedInputManager::Button::PageBack)) {
    stepPage(-1);
    return;
  }
  if (mappedInput.wasReleased(MappedInputManager::Button::PageForward)) {
    stepPage(1);
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
    openSelectedBook();
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
      if (selected_ == hit) openSelectedBook();
      else {
        selected_ = hit;
        requestUpdate();
      }
      return;
    }
    if (hitFeaturedCover(x, y)) {
      openSelectedBook();
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
  if (selectedFrame) renderer.drawRect(rect.x - 3, rect.y - 3, rect.width + 6, rect.height + 6, 2, true);
}

void CoverGridBrowserActivity::render(RenderLock&&) {
  const int width = renderer.getScreenWidth();
  const int height = renderer.getScreenHeight();

  renderer.clearScreen();
  drawCenteredIn(renderer, UI_12_FONT_ID, 0, width, HEADER_TITLE_Y, gridTitle(), EpdFontFamily::BOLD);

  static constexpr const char* HU_TABS[] = {"Legutóbbi", "Cím", "Szerző"};
  static constexpr const char* EN_TABS[] = {"Recent", "Title", "Author"};
  const char* const* tabs = I18N.getLanguage() == Language::HU ? HU_TABS : EN_TABS;
  for (int i = 0; i < 3; ++i) {
    const int x = i * width / 3;
    const int w = (i + 1) * width / 3 - x;
    drawCenteredIn(renderer, UI_10_FONT_ID, x, w, TAB_Y + 5, tabs[i],
                   i == activeSortTab_ ? EpdFontFamily::BOLD : EpdFontFamily::REGULAR);
    if (i == activeSortTab_) {
      renderer.drawLine(x + 10, TAB_Y + TAB_H - 2, x + w - 10, TAB_Y + TAB_H - 2, true);
      const bool desc = (descendingTabs_ & static_cast<uint8_t>(1u << i)) != 0;
      renderer.drawText(UI_10_FONT_ID, x + w - 20, TAB_Y + 5, desc ? "↓" : "↑");
    }
  }

  if (!books_.empty()) {
    const GridBook& selectedBook = books_[std::clamp(selected_, 0, static_cast<int>(books_.size()) - 1)];
    paintCover(selectedBook, Rect{FEATURED_X, FEATURED_Y, FEATURED_W, FEATURED_H}, false);

    const int textW = std::max(40, width - FEATURED_TEXT_X - 22);
    const auto titleLines = renderer.wrappedText(UI_12_FONT_ID, selectedBook.title.c_str(), textW, 4);
    int y = FEATURED_Y + 8;
    for (const auto& line : titleLines) {
      renderer.drawText(UI_12_FONT_ID, FEATURED_TEXT_X, y, line.c_str(), true, EpdFontFamily::BOLD);
      y += renderer.getLineHeight(UI_12_FONT_ID);
    }
    if (!selectedBook.author.empty()) {
      y += 8;
      const auto authorLines = renderer.wrappedText(UI_10_FONT_ID, selectedBook.author.c_str(), textW, 3);
      for (const auto& line : authorLines) {
        renderer.drawText(UI_10_FONT_ID, FEATURED_TEXT_X, y, line.c_str());
        y += renderer.getLineHeight(UI_10_FONT_ID);
      }
    }

    char position[48];
    snprintf(position, sizeof(position), "%d / %d %s", globalSelection() + 1, totalBooks(), bookWord());
    renderer.drawText(UI_10_FONT_ID, FEATURED_TEXT_X, FEATURED_Y + FEATURED_H - 20, position);

    for (int i = 0; i < static_cast<int>(books_.size()); ++i) {
      const int col = i % GRID_COLS;
      const int row = i / GRID_COLS;
      const int x = GRID_LEFT + col * (GRID_W + GRID_GAP_X);
      const int gy = GRID_TOP + row * (GRID_H + GRID_GAP_Y);
      paintCover(books_[i], Rect{x, gy, GRID_W, GRID_H}, i == selected_);
    }
  } else {
    drawCenteredIn(renderer, UI_12_FONT_ID, 20, width - 40, FEATURED_Y + 80,
                   I18N.getLanguage() == Language::HU ? "Nincs indexelt EPUB." : "No indexed EPUB files.");
  }

  if (totalBooks() > 0) {
    const int first = pageStart_ + 1;
    const int last = pageStart_ + static_cast<int>(books_.size());
    char pageText[48];
    snprintf(pageText, sizeof(pageText), "%d–%d / %d %s", first, last, totalBooks(), bookWord());
    drawCenteredIn(renderer, UI_10_FONT_ID, 0, width, PAGE_READOUT_Y, pageText);
  }

  const char* hint = I18N.getLanguage() == Language::HU
                         ? "Hosszan OK: Infó · Hosszan Vissza: Fordított rendezés"
                         : "Hold OK: Info · Hold Back: Reverse sort";
  drawCenteredIn(renderer, UI_10_FONT_ID, 8, width - 16, PAGE_READOUT_Y + 22,
                 renderer.truncatedText(UI_10_FONT_ID, hint, width - 16).c_str());

  const auto labels = mappedInput.mapLabels(I18N.getLanguage() == Language::HU ? "Vissza" : "Back",
                                            I18N.getLanguage() == Language::HU ? "Megnyitás" : "Open", "<", ">");
  GUI.drawButtonHints(renderer, labels.btn1, labels.btn2, labels.btn3, labels.btn4);

  if (optionPopup_.isActive()) {
    optionPopup_.processRender(renderer, mappedInput);
    return;
  }

  renderer.displayBuffer();
}
