#include "EpubReaderBookmarksActivity.h"

#include <FsHelpers.h>
#include <GfxRenderer.h>
#include <HalStorage.h>
#include <I18n.h>
#include <Logging.h>

#include <algorithm>
#include <cstdio>

#include "../../util/BookmarkFile.h"
#include "MappedInputManager.h"
#include "components/UITheme.h"
#include "components/UiAppHelpers.h"
#include "fontIds.h"

namespace fui = freeink::ui;

namespace {
constexpr int ENTER_DELETE_MODE_MS = 700;
}

EpubReaderBookmarksActivity::EpubReaderBookmarksActivity(GfxRenderer& renderer, MappedInputManager& mappedInput,
                                                         const std::shared_ptr<Epub>& epub, const std::string& epubPath)
    : UiListActivity("EpubReaderBookmarks", renderer, mappedInput, /*wantsTouchLongPress=*/true),
      epub(epub), epubPath(epubPath) {}

void EpubReaderBookmarksActivity::onEnter() {
  UiListActivity::onEnter();
  if (!epub) return;
  if (!BookmarkFile::load(epubPath, bookmarks)) bookmarks.shrink_to_fit();
  highlightStore = std::make_unique<HighlightStore>(epubPath);
  if (!highlightStore->load()) LOG_ERR("EPB", "Failed to load marked words for %s", epubPath.c_str());
  rebuildRows();
}

void EpubReaderBookmarksActivity::rebuildRows() {
  rows.clear(); rowLabels.clear(); rowSubtitles.clear(); rowItems.clear();
  if (!epub) return;
  const size_t highlightCount = highlightStore ? highlightStore->items().size() : 0;
  const size_t total = bookmarks.size() + highlightCount;
  rows.reserve(total); rowLabels.reserve(total); rowSubtitles.reserve(total); rowItems.reserve(total);

  for (size_t i = 0; i < bookmarks.size(); ++i) {
    const auto& bookmark = bookmarks[i];
    rows.push_back({RowKind::Bookmark, i});
    rowLabels.push_back(bookmark.summary);
    const auto tocIndex = epub->getTocIndexForSpineIndex(bookmark.computedSpineIndex);
    const auto tocTitle = (tocIndex >= 0) ? epub->getTocItem(tocIndex).title : tr(STR_UNNAMED);
    std::string subtitle = std::to_string((int)(std::clamp(bookmark.percentage, 0.0f, 1.0f) * 100.0f + 0.5f)) + "% - ";
    if (bookmark.computedChapterPageCount > 0) {
      subtitle += std::to_string(bookmark.computedChapterProgress + 1) + "/" +
                  std::to_string(bookmark.computedChapterPageCount) + " - ";
    }
    subtitle += tocTitle;
    rowSubtitles.push_back(std::move(subtitle));
  }

  if (highlightStore) {
    const auto& highlights = highlightStore->items();
    for (size_t i = 0; i < highlights.size(); ++i) {
      rows.push_back({RowKind::Highlight, i});
      rowLabels.push_back(highlights[i].text);
      const auto tocIndex = epub->getTocIndexForSpineIndex(highlights[i].spineIndex);
      const std::string tocTitle = (tocIndex >= 0) ? epub->getTocItem(tocIndex).title : tr(STR_UNNAMED);
      rowSubtitles.push_back(std::string("Megjelölés - ") + tocTitle);
    }
  }

  for (size_t i = 0; i < rows.size(); ++i) {
    fui::ListItem item;
    item.label = rowLabels[i].c_str();
    item.subtitle = rowSubtitles[i].c_str();
    item.icon = listIconFor(UIIcon::Bookmark, 32);
    item.actionValue = static_cast<int16_t>(i);
    rowItems.push_back(item);
  }
}

void EpubReaderBookmarksActivity::openSelectedItem() {
  if (rows.empty() || nav.selected < 0 || nav.selected >= static_cast<int>(rows.size())) return;
  const RowRef row = rows[nav.selected];
  ProgressChangeResult result{};
  if (row.kind == RowKind::Bookmark) {
    const auto& bookmark = bookmarks.at(row.index);
    result.xpath = bookmark.xpath; result.percentage = bookmark.percentage; result.hasSavedProgress = true;
    result.hasVisibleTextOffset = bookmark.hasVisibleTextOffset; result.visibleTextOffset = bookmark.visibleTextOffset;
    result.spineIndex = bookmark.computedSpineIndex;
    if (bookmark.computedChapterPageCount > 0 && bookmark.computedChapterProgress < bookmark.computedChapterPageCount &&
        bookmark.computedSpineIndex < epub->getSpineItemsCount()) {
      result.page = bookmark.computedChapterProgress; result.totalPages = bookmark.computedChapterPageCount;
    }
  } else {
    const auto& mark = highlightStore->items().at(row.index);
    result.spineIndex = mark.spineIndex;
    result.hasSavedProgress = true;
    result.hasVisibleTextOffset = true;
    result.visibleTextOffset = mark.visibleTextOffset;
    result.percentage = epub->calculateProgress(mark.spineIndex, 0.0f);
  }
  setResult(std::move(result)); finish();
}

void EpubReaderBookmarksActivity::activateIndex(const int index) {
  if (confirmPopup.isActive() || index < 0 || index >= listCount()) return;
  app.clearTapFlash(); nav.selected = index; openSelectedItem();
}

void EpubReaderBookmarksActivity::onRowLongPress(const int index) {
  if (confirmPopup.isActive() || index < 0 || index >= listCount()) return;
  app.clearTapFlash(); nav.selected = index; showDeleteConfirmation();
}

bool EpubReaderBookmarksActivity::handleCustomInput() {
  if (confirmPopup.handleInput(mappedInput, [this] { requestUpdate(); })) return true;
  if (confirmingDelete) { confirmingDelete = false; requestUpdate(); return true; }
  return false;
}

bool EpubReaderBookmarksActivity::handleButtons() {
  if (mappedInput.wasReleased(MappedInputManager::Button::Back)) {
    ActivityResult result;
    result.isCancelled = true;
    setResult(std::move(result));
    finish();
    return true;
  }
  if (mappedInput.wasReleased(MappedInputManager::Button::Confirm)) {
    if (mappedInput.getHeldTime() > ENTER_DELETE_MODE_MS && !rows.empty())
      showDeleteConfirmation();
    else
      openSelectedItem();
    return true;
  }
  return false;
}

void EpubReaderBookmarksActivity::showDeleteConfirmation() {
  if (rows.empty() || confirmPopup.isActive()) return;
  const RowRef row = rows[nav.selected];
  confirmingDelete = true;
  const char* options[] = {tr(STR_CANCEL), tr(STR_DELETE)};
  const char* title = row.kind == RowKind::Highlight ? "Megjelölés törlése?" : tr(STR_CONFIRM_DELETE_BOOKMARK);
  confirmPopup.show(title, options, 2, 0, [this](int idx) {
    confirmingDelete = false;
    if (idx == 1) deleteSelectedItem();
    requestUpdate();
  });
  requestUpdate();
}

void EpubReaderBookmarksActivity::deleteSelectedItem() {
  if (rows.empty()) return;
  const RowRef row = rows[nav.selected];
  if (row.kind == RowKind::Bookmark) {
    bookmarks.erase(bookmarks.begin() + row.index);
    if (!BookmarkFile::save(epubPath, bookmarks)) LOG_ERR("EPB", "Failed to save bookmarks after delete");
  } else if (row.kind == RowKind::Highlight && highlightStore) {
    const HighlightAnchor mark = highlightStore->items().at(row.index);
    if (!highlightStore->remove(mark)) LOG_ERR("EPB", "Failed to remove marked word");
  }
  rebuildRows();
  if (nav.selected >= static_cast<int>(rows.size()) && nav.selected > 0) nav.selected--;
  nav.follow(listCount()); requestUpdate(true);
}

void EpubReaderBookmarksActivity::buildScreen(UiScreen& screen) {
  const auto& metrics = UITheme::getInstance().getMetrics();
  const Rect safe = UITheme::getInstance().getScreenSafeArea(renderer, true, false);
  screen.setContentMargin(fui::Insets{static_cast<int16_t>(safe.y + metrics.topPadding + metrics.headerHeight),
                                      static_cast<int16_t>(renderer.getScreenWidth() - (safe.x + safe.width)),
                                      static_cast<int16_t>(renderer.getScreenHeight() - (safe.y + safe.height)),
                                      static_cast<int16_t>(safe.x)});
  screen.spacer(static_cast<int16_t>(metrics.verticalSpacing));
  if (rows.empty()) { screen.centeredText(tr(STR_NO_BOOKMARKS), screen.theme().bodyText); return; }
  if (!mappedInput.hasTouch()) {
    const int helpLineHeight = renderer.getLineHeight(SMALL_FONT_ID);
    const fui::Rect band = screen.takeBottom(static_cast<int16_t>(helpLineHeight + metrics.verticalSpacing));
    GUI.drawHelpText(renderer, Rect{band.x, band.y + metrics.verticalSpacing, band.width, helpLineHeight},
                     I18N.getLanguage() == Language::HU ? "Törléshez tartsd nyomva: Kijelölés"
                                                        : "Hold Select to Delete");
  }
  fui::ListProps props; props.items = rowItems.data(); props.count = static_cast<uint16_t>(rowItems.size());
  props.action = ACTION_ROW; props.inputMask = fui::InputTouch | fui::InputLongPress;
  if (!mappedInput.hasTouch()) {
        props.rowHeight = static_cast<int16_t>(UITheme::getInstance().getMetrics().listWithSubtitleRowHeight);
      }
      syncListViewport(screen, props); screen.list(props);
}

void EpubReaderBookmarksActivity::render(RenderLock&&) {
  renderer.clearScreen();
  const auto pageWidth = renderer.getScreenWidth(); const auto orientation = renderer.getOrientation();
  const bool cw = orientation == GfxRenderer::Orientation::LandscapeClockwise;
  const bool ccw = orientation == GfxRenderer::Orientation::LandscapeCounterClockwise;
  const bool inv = orientation == GfxRenderer::Orientation::PortraitInverted;
  const int gutter = (cw || ccw) ? 40 : 0; const int contentX = cw ? gutter : 0;
  const int contentWidth = pageWidth - gutter; const int contentY = inv ? 50 : 0;
  const int titleX = contentX + (contentWidth - renderer.getTextWidth(UI_12_FONT_ID, tr(STR_BOOKMARKS), EpdFontFamily::BOLD)) / 2;
  renderer.drawText(UI_12_FONT_ID, titleX, 15 + contentY, tr(STR_BOOKMARKS), true, EpdFontFamily::BOLD);
  renderUi();
  if (confirmPopup.processRender(renderer, mappedInput)) return;
  const auto labels = mappedInput.mapLabels(tr(STR_BACK), rows.empty() ? "" : tr(STR_SELECT), tr(STR_DIR_UP), tr(STR_DIR_DOWN));
  GUI.drawButtonHints(renderer, labels.btn1, labels.btn2, labels.btn3, labels.btn4);
  renderer.displayBuffer();
}
