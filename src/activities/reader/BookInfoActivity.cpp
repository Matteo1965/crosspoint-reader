#include "BookInfoActivity.h"

#include <GfxRenderer.h>
#include <HalStorage.h>

#include <algorithm>

#include "MappedInputManager.h"
#include "activities/util/BmpViewerActivity.h"
#include "components/UITheme.h"

namespace fui = freeink::ui;

BookInfoActivity::BookInfoActivity(GfxRenderer& renderer, MappedInputManager& mappedInput, std::shared_ptr<Epub> epub)
    : UiTabListActivity("BookInfo", renderer, mappedInput), epub_(std::move(epub)) {}

void BookInfoActivity::onEnter() {
  UiTabListActivity::onEnter();
  if (epub_) {
    epub_->readBookInfo(info_);
    coverPath_ = epub_->getCoverBmpPath(false);
    if (!Storage.exists(coverPath_.c_str())) {
      epub_->generateCoverBmp(false);
    }
  }
  rebuildRows();
}

const char* BookInfoActivity::tabLabel(const int index) const {
  switch (index) {
    case 0:
      return "Fülszöveg";
    case 1:
      return "Metaadatok";
    default:
      return "Borító";
  }
}

int BookInfoActivity::tabWidthPercent(const int index) const {
  constexpr int widths[] = {34, 36, 30};
  return index >= 0 && index < 3 ? widths[index] : 0;
}

void BookInfoActivity::onTabAction(const int index) {
  if (index < 0 || index >= tabCount()) return;
  tab_ = static_cast<Tab>(index);
  rebuildRows();
  moveRingTo(0);
  requestUpdate();
}

void BookInfoActivity::stepTab(const int direction) {
  const int next = (activeTab() + direction + tabCount()) % tabCount();
  onTabAction(next);
}

void BookInfoActivity::addDescriptionRows(const std::string& text) {
  if (text.empty()) {
    rowText_.push_back("Ehhez a könyvhöz nincs fülszöveg.");
    return;
  }

  constexpr size_t TARGET = 58;
  size_t pos = 0;
  while (pos < text.size()) {
    while (pos < text.size() && (text[pos] == ' ' || text[pos] == '\n' || text[pos] == '\r' || text[pos] == '\t')) ++pos;
    if (pos >= text.size()) break;
    size_t end = std::min(text.size(), pos + TARGET);
    if (end < text.size()) {
      const size_t space = text.rfind(' ', end);
      if (space != std::string::npos && space > pos + TARGET / 2) end = space;
    }
    std::string line = text.substr(pos, end - pos);
    std::replace(line.begin(), line.end(), '\n', ' ');
    std::replace(line.begin(), line.end(), '\r', ' ');
    rowText_.push_back(std::move(line));
    pos = end;
  }
}

void BookInfoActivity::addMetadataRow(const char* label, const std::string& value) {
  if (value.empty()) return;
  rowText_.push_back(std::string(label) + value);
}

void BookInfoActivity::rebuildRows() {
  rowText_.clear();
  rows_.clear();

  if (tab_ == Tab::Description) {
    addDescriptionRows(info_.description);
  } else if (tab_ == Tab::Metadata) {
    addMetadataRow("Cím: ", info_.title);
    addMetadataRow("Szerző: ", info_.author);
    addMetadataRow("Sorozat: ", info_.series);
    if (!info_.seriesIndex.empty()) addMetadataRow("Sorozatszám: ", info_.seriesIndex);
    addMetadataRow("Kiadó: ", info_.publisher);
    addMetadataRow("Dátum: ", info_.date);
    addMetadataRow("Nyelv: ", info_.language);
    addMetadataRow("Azonosító: ", info_.identifier);
    addMetadataRow("Fájlnév: ", info_.filename);
    if (info_.fileSize > 0) rowText_.push_back("Fájlméret: " + std::to_string(info_.fileSize) + " byte");
    if (rowText_.empty()) rowText_.push_back("Nincs megjeleníthető metaadat.");
  } else {
    rowText_.push_back(coverPath_.empty() ? "Nincs megjeleníthető borító." : "Borító megnyitása");
  }

  rows_.reserve(rowText_.size());
  for (size_t i = 0; i < rowText_.size(); ++i) {
    fui::ListItem item;
    item.label = rowText_[i].c_str();
    item.actionValue = static_cast<int16_t>(i);
    rows_.push_back(item);
  }
}

void BookInfoActivity::openCover() {
  if (coverPath_.empty() || !Storage.exists(coverPath_.c_str())) return;
  startActivityForResult(std::make_unique<BmpViewerActivity>(renderer, mappedInput, coverPath_),
                         [this](const ActivityResult&) { requestUpdate(); });
}

void BookInfoActivity::activateIndex(const int index) {
  if (index < 0 || index >= listCount()) return;
  if (tab_ == Tab::Cover) openCover();
}

bool BookInfoActivity::handleButtons() {
  if (mappedInput.wasReleased(MappedInputManager::Button::Back)) {
    finish();
    return true;
  }
  if (mappedInput.wasReleased(MappedInputManager::Button::Left) && ringPos() == 0) {
    stepTab(-1);
    return true;
  }
  if (mappedInput.wasReleased(MappedInputManager::Button::Right) && ringPos() == 0) {
    stepTab(1);
    return true;
  }
  if (mappedInput.wasReleased(MappedInputManager::Button::Confirm)) {
    if (ringPos() == 0) {
      stepTab(1);
    } else {
      activateIndex(ringPos() - 1);
    }
    return true;
  }
  return false;
}

void BookInfoActivity::buildScreen(UiScreen& screen) {
  const auto& metrics = UITheme::getInstance().getMetrics();
  const Rect safe = UITheme::getInstance().getScreenSafeArea(renderer, true, false);
  screen.setContentMargin(fui::Insets{static_cast<int16_t>(safe.y + metrics.topPadding + metrics.headerHeight),
                                      static_cast<int16_t>(renderer.getScreenWidth() - (safe.x + safe.width)),
                                      static_cast<int16_t>(metrics.buttonHintsHeight), static_cast<int16_t>(safe.x)});
  buildTabBar(screen);
  screen.spacer(static_cast<int16_t>(metrics.verticalSpacing));

  fui::ListProps props;
  props.items = rows_.data();
  props.count = static_cast<uint16_t>(rows_.size());
  props.action = ACTION_ROW;
  props.inputMask = fui::InputTouch;
  props.labelText = screen.theme().bodyText;
  props.labelText.maxLines = 2;
  syncTabListViewport(screen, props);
  screen.list(props);
}

void BookInfoActivity::drawChrome() {
  const auto& metrics = UITheme::getInstance().getMetrics();
  const Rect safe = UITheme::getInstance().getScreenSafeArea(renderer, true, false);
  GUI.drawHeader(renderer, Rect{safe.x, safe.y + metrics.topPadding, safe.width, metrics.headerHeight}, "Könyv adatai");
}
