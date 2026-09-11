#include "RecentBooksActivity.h"

#include <GfxRenderer.h>
#include <HalStorage.h>
#include <I18n.h>

#include <algorithm>
#include <memory>

#include "MappedInputManager.h"
#include "RecentBooksStore.h"
#include "activities/util/ConfirmationActivity.h"
#include "components/UITheme.h"
#include "components/UiAppHelpers.h"

namespace fui = freeink::ui;

namespace {
constexpr unsigned long LONG_PRESS_MS = 1000;

std::string fileNameFromPath(const std::string& path) {
  const size_t slash = path.find_last_of('/');
  return slash == std::string::npos ? path : path.substr(slash + 1);
}
}  // namespace

RecentBooksActivity::RecentBooksActivity(GfxRenderer& renderer, MappedInputManager& mappedInput)
    : UiListActivity("RecentBooks", renderer, mappedInput, /*wantsTouchLongPress=*/true) {}

void RecentBooksActivity::loadRecentBooks() {
  recentBooks = RECENT_BOOKS.getBooks();
  rebuildRowItems();
}

void RecentBooksActivity::rebuildRowItems() {
  rowItems.clear();
  subtitleTexts.clear();
  rowItems.reserve(recentBooks.size());
  subtitleTexts.reserve(recentBooks.size());

  for (size_t i = 0; i < recentBooks.size(); ++i) {
    const auto& book = recentBooks[i];
    const bool duplicateTitle = !book.title.empty() &&
                                std::count_if(recentBooks.begin(), recentBooks.end(), [&](const RecentBook& other) {
                                  return other.title == book.title;
                                }) > 1;
    subtitleTexts.push_back(duplicateTitle ? fileNameFromPath(book.path) : book.author);

    fui::ListItem item;
    item.label = book.title.c_str();
    if (!subtitleTexts.back().empty()) item.subtitle = subtitleTexts.back().c_str();
    item.icon = listIconFor(UITheme::getFileIcon(book.path), 32);
    item.actionValue = static_cast<int16_t>(rowItems.size());
    rowItems.push_back(item);
  }

  const auto count = static_cast<uint32_t>(recentBooks.size());
  renderer.prewarmFallbackText(
      uiScaleSpec().smallFontId,
      [](const void* ctx, uint32_t i) -> const char* {
        return (*static_cast<const std::vector<RecentBook>*>(ctx))[i].title.c_str();
      },
      &recentBooks, count, EpdFontFamily::BOLD);
  renderer.prewarmFallbackText(
      uiScaleSpec().smallFontId,
      [](const void* ctx, uint32_t i) -> const char* {
        return (*static_cast<const std::vector<std::string>*>(ctx))[i].c_str();
      },
      &subtitleTexts, static_cast<uint32_t>(subtitleTexts.size()));
}

void RecentBooksActivity::onEnter() {
  UiListActivity::onEnter();
  if (RECENT_BOOKS.pruneMissing()) RECENT_BOOKS.saveToFile();
  loadRecentBooks();
}

void RecentBooksActivity::onExit() {
  Activity::onExit();
  rowItems.clear();
  subtitleTexts.clear();
  recentBooks.clear();
}

void RecentBooksActivity::activateIndex(const int index) {
  if (index < 0 || index >= listCount()) return;
  app.clearTapFlash();
  LOG_DBG("RBA", "Selected recent book: %s", recentBooks[index].path.c_str());
  onSelectBook(recentBooks[index].path);
}

void RecentBooksActivity::onRowLongPress(const int index) {
  if (index < 0 || index >= listCount()) return;
  app.clearTapFlash();
  promptRemoveBook(recentBooks[index].path, recentBooks[index].title);
}

bool RecentBooksActivity::handleButtons() {
  if (mappedInput.wasReleased(MappedInputManager::Button::Confirm)) {
    if (!recentBooks.empty() && nav.selected < listCount()) {
      if (mappedInput.getHeldTime() >= LONG_PRESS_MS) {
        promptRemoveBook(recentBooks[nav.selected].path, recentBooks[nav.selected].title);
      } else {
        activateIndex(nav.selected);
      }
      return true;
    }
  }
  if (mappedInput.wasReleased(MappedInputManager::Button::Back)) {
    onGoHome();
    return true;
  }
  return false;
}

void RecentBooksActivity::promptRemoveBook(const std::string& path, const std::string& title) {
  auto handler = [this, path](const ActivityResult& res) {
    if (res.isCancelled) return;
    if (RECENT_BOOKS.removeByPath(path)) {
      closeRouting();
      loadRecentBooks();
      if (recentBooks.empty()) {
        nav.selected = 0;
      } else if (nav.selected >= listCount()) {
        nav.selected = listCount() - 1;
      }
      nav.follow(listCount());
      requestUpdate(true);
    }
  };
  startActivityForResult(
      std::make_unique<ConfirmationActivity>(renderer, mappedInput, tr(STR_REMOVE_FROM_RECENTS), title),
      std::move(handler));
}

void RecentBooksActivity::buildScreen(UiScreen& screen) {
  const auto& metrics = UITheme::getInstance().getMetrics();
  screen.setContentMargin(fui::Insets{static_cast<int16_t>(metrics.topPadding + metrics.headerHeight), 0,
                                      static_cast<int16_t>(metrics.buttonHintsHeight), 0});
  screen.spacer(static_cast<int16_t>(metrics.verticalSpacing));

  if (recentBooks.empty()) {
    screen.centeredText(tr(STR_NO_RECENT_BOOKS), screen.theme().bodyText);
    return;
  }

  fui::ListProps props;
  props.items = rowItems.data();
  props.count = static_cast<uint16_t>(rowItems.size());
  props.action = ACTION_ROW;
  props.inputMask = fui::InputTouch | fui::InputLongPress;
  fui::TextStyle label = screen.theme().smallText;
  label.bold = true;
  props.labelText = label;
  syncListViewport(screen, props, /*hasSubtitle=*/true);
  screen.list(props);
}

void RecentBooksActivity::drawFooter() {
  const bool empty = recentBooks.empty();
  const auto labels = mappedInput.mapLabels(tr(STR_HOME), empty ? "" : tr(STR_OPEN), empty ? "" : tr(STR_DIR_UP),
                                            empty ? "" : tr(STR_DIR_DOWN));
  GUI.drawButtonHints(renderer, labels.btn1, labels.btn2, labels.btn3, labels.btn4);
}
