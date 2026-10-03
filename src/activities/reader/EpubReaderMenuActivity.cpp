#include "EpubReaderMenuActivity.h"

#include <GfxRenderer.h>
#include <HalFrontlight.h>
#include <I18n.h>

#include "CrossPointSettings.h"
#include "MappedInputManager.h"
#include "ReaderUtils.h"
#include "SettingsList.h"
#include "fontIds.h"
#include "components/UITheme.h"

namespace fui = freeink::ui;

namespace {
std::string fitDictionaryMenuValue(GfxRenderer& renderer, const char* raw) {
  if (!raw) return {};
  constexpr int MAX_VALUE_WIDTH = 170;
  std::string value(raw);
  if (renderer.getTextAdvanceX(NOTOSANS_14_FONT_ID, value.c_str(), EpdFontFamily::REGULAR) <= MAX_VALUE_WIDTH)
    return value;
  constexpr const char* dots = "...";
  while (!value.empty()) {
    const auto candidate = value + dots;
    if (renderer.getTextAdvanceX(NOTOSANS_14_FONT_ID, candidate.c_str(), EpdFontFamily::REGULAR) <= MAX_VALUE_WIDTH)
      return candidate;
    size_t cut = value.size() - 1;
    while (cut > 0 && (static_cast<unsigned char>(value[cut]) & 0xC0) == 0x80) --cut;
    value.resize(cut);
  }
  return dots;
}
}  // namespace

EpubReaderMenuActivity::EpubReaderMenuActivity(GfxRenderer& renderer, MappedInputManager& mappedInput,
                                               const std::string& title, const int currentPage, const int totalPages,
                                               const int bookProgressPercent, const uint8_t currentOrientation,
                                               const bool hasFootnotes, const bool hasBookmarks,
                                               const bool startOnBookTab)
    : UiTabListActivity("EpubReaderMenu", renderer, mappedInput),
      readingItems(buildReadingItems(hasFootnotes, hasBookmarks)),
      moreItems(buildMoreItems()),
      tab_(startOnBookTab ? Tab::Book : Tab::Reading),
      title(title),
      pendingOrientation(currentOrientation),
      currentPage(currentPage),
      totalPages(totalPages),
      bookProgressPercent(bookProgressPercent) {
  std::vector<DictionaryEntry> dictionaries;
  DictionaryRegistry::discover(dictionaries);
  auto dictionarySetting = buildDictionarySetting(dictionaries);
  dictionaryOptionLabels = std::move(dictionarySetting.enumStringValues);
  dictionaryOptionPointers.reserve(dictionaryOptionLabels.size());
  for (const auto& label : dictionaryOptionLabels) dictionaryOptionPointers.push_back(label.c_str());
  selectedDictionaryOption = dictionarySetting.valueGetter ? dictionarySetting.valueGetter() : 0;
  dictionarySetter = std::move(dictionarySetting.valueSetter);
  rebuildMenuRowItems();
}

std::vector<EpubReaderMenuActivity::MenuItem> EpubReaderMenuActivity::buildReadingItems(bool hasFootnotes,
                                                                                        bool hasBookmarks) {
  std::vector<MenuItem> items;
  items.reserve(MAX_MENU_ITEMS);
  items.push_back({MenuAction::SELECT_CHAPTER, StrId::STR_SELECT_CHAPTER});
  if (hasFootnotes) items.push_back({MenuAction::FOOTNOTES, StrId::STR_FOOTNOTES});
  if (hasBookmarks) items.push_back({MenuAction::BOOKMARKS, StrId::STR_BOOKMARKS});
  items.push_back({MenuAction::TOGGLE_BOOKMARK, StrId::STR_TOGGLE_BOOKMARK});
  items.push_back({MenuAction::HIGHLIGHT, StrId::STR_LOOKUP, "Megjelölés"});
  items.push_back({MenuAction::EDIT, StrId::STR_LOOKUP, "Szerkesztés"});
  items.push_back({MenuAction::DICTIONARY, StrId::STR_LOOKUP, "Szótári keresés"});
  items.push_back({MenuAction::MANUAL_DICTIONARY_SEARCH, StrId::STR_LOOKUP, "Kézi keresés"});
  items.push_back({MenuAction::DICTIONARY_SETTINGS, StrId::STR_DICTIONARY, "Szótár:"});
  if (Frontlight.present()) items.push_back({MenuAction::FRONTLIGHT, StrId::STR_FRONTLIGHT});
  items.push_back({MenuAction::WORD_SELECTION_MODE, StrId::STR_LOOKUP, "Mód választó"});
  items.push_back({MenuAction::AUTO_PAGE_TURN, StrId::STR_AUTO_TURN_PAGES_PER_MIN, "Auto. lapozás, lap/perc"});
  items.push_back({MenuAction::GO_TO_PERCENT, StrId::STR_GO_TO_PERCENT});
  return items;
}

std::vector<EpubReaderMenuActivity::MenuItem> EpubReaderMenuActivity::buildMoreItems() {
  return {
      {MenuAction::BOOK_DESCRIPTION, StrId::STR_TEXT_SETTINGS, "Fülszöveg"},
      {MenuAction::BOOK_METADATA, StrId::STR_TEXT_SETTINGS, "Metaadatok"},
      {MenuAction::BOOK_COVER, StrId::STR_TEXT_SETTINGS, "Borító megjelenítése"},
      {MenuAction::ROTATE_SCREEN, StrId::STR_ORIENTATION},
      {MenuAction::NIGHT_MODE, StrId::STR_NIGHT_MODE, "Sötét mód"},
      {MenuAction::TEXT_SETTINGS, StrId::STR_TEXT_SETTINGS},
      {MenuAction::SCREENSHOT, StrId::STR_SCREENSHOT_BUTTON},
      {MenuAction::DISPLAY_QR, StrId::STR_DISPLAY_QR},
      {MenuAction::EXPORT_EDITS, StrId::STR_TEXT_SETTINGS, "Szerkesztések exportálása"},
      {MenuAction::SYNC, StrId::STR_SYNC_PROGRESS},
      {MenuAction::DELETE_CACHE, StrId::STR_DELETE_CACHE},
      {MenuAction::REINDEX_CHAPTER, StrId::STR_DELETE_CACHE, "Fejezet újraindexelése"},
  };
}

const std::vector<EpubReaderMenuActivity::MenuItem>& EpubReaderMenuActivity::activeItems() const {
  return tab_ == Tab::Reading ? readingItems : moreItems;
}

const char* EpubReaderMenuActivity::tabLabel(const int index) const {
  return index == 0 ? "Olvasás" : "Könyv";
}

int EpubReaderMenuActivity::tabWidthPercent(const int) const { return 50; }

void EpubReaderMenuActivity::rebuildMenuRowItems() {
  for (auto& row : menuRowItems) row = {};
  const auto& items = activeItems();
  for (size_t i = 0; i < items.size() && i < menuRowItems.size(); ++i) {
    auto& row = menuRowItems[i];
    row.label = items[i].overrideLabel ? items[i].overrideLabel : I18N.get(items[i].labelId);
    row.actionValue = static_cast<int16_t>(i);
  }
}

void EpubReaderMenuActivity::onTabAction(const int index) {
  if (index < 0 || index >= tabCount()) return;
  tab_ = static_cast<Tab>(index);
  rebuildMenuRowItems();
  moveRingTo(0);
  requestUpdate();
}

void EpubReaderMenuActivity::stepTab(const int direction) {
  const int next = (activeTab() + direction + tabCount()) % tabCount();
  onTabAction(next);
}

void EpubReaderMenuActivity::closeCancelled() {
  ActivityResult result;
  result.isCancelled = true;
  result.data = MenuResult{-1, pendingOrientation, selectedPageTurnOption};
  setResult(std::move(result));
  finish();
}

bool EpubReaderMenuActivity::handleHomeGesture() {
  closeCancelled();
  return true;
}

void EpubReaderMenuActivity::activateIndex(const int index) {
  if (optionPopup.isActive()) return;
  const auto& items = activeItems();
  if (index < 0 || index >= static_cast<int>(items.size())) return;
  app.clearTapFlash();
  activeNav().selected = index + 1;

  const auto selectedAction = items[index].action;
  if (selectedAction == MenuAction::ROTATE_SCREEN) {
    optionPopup.show(StrId::STR_ORIENTATION, orientationLabels.data(), static_cast<int>(orientationLabels.size()),
                     pendingOrientation, [this](int idx) {
                       pendingOrientation = idx;
                       ReaderUtils::applyOrientation(renderer, pendingOrientation);
                       app.setDevice(uiTarget.deviceContext());
                       requestUpdate(true);
                     });
    requestUpdate();
    return;
  }

  if (selectedAction == MenuAction::AUTO_PAGE_TURN) {
    optionPopup.show(I18N.get(StrId::STR_AUTO_TURN_PAGES_PER_MIN), pageTurnLabels.data(),
                     static_cast<int>(pageTurnLabels.size()), selectedPageTurnOption, [this](int idx) {
                       selectedPageTurnOption = idx;
                       requestUpdate();
                     });
    requestUpdate();
    return;
  }

  if (selectedAction == MenuAction::WORD_SELECTION_MODE) {
    static const char* modeLabels[] = {"Szótár", "Megjelölés", "Szerkesztés"};
    const uint8_t selected = SETTINGS.wordSelectionMode <= 2 ? SETTINGS.wordSelectionMode : 0;
    optionPopup.show("Mód választó", modeLabels, 3, selected, [this](int idx) {
      SETTINGS.wordSelectionMode = static_cast<uint8_t>(idx);
      SETTINGS.saveToFile();
      requestUpdate();
    });
    requestUpdate();
    return;
  }

  if (selectedAction == MenuAction::DICTIONARY_SETTINGS) {
    if (!dictionaryOptionPointers.empty()) {
      optionPopup.show("Szótár:", dictionaryOptionPointers.data(),
                       static_cast<int>(dictionaryOptionPointers.size()), selectedDictionaryOption,
                       [this](int idx) {
                         selectedDictionaryOption = static_cast<uint8_t>(idx);
                         if (dictionarySetter) dictionarySetter(selectedDictionaryOption);
                         SETTINGS.saveToFile();
                         requestUpdate();
                       });
      requestUpdate();
    }
    return;
  }

  if (selectedAction == MenuAction::NIGHT_MODE) {
    SETTINGS.screenInverted = SETTINGS.screenInverted == 0 ? 1 : 0;
    SETTINGS.saveToFile();
    requestUpdate();
    return;
  }

  if (selectedAction == MenuAction::FRONTLIGHT) {
    const bool lightOn = !Frontlight.isOn();
    Frontlight.setOn(lightOn);
    SETTINGS.frontlightOn = lightOn ? 1 : 0;
    SETTINGS.saveToFile();
    requestUpdate();
    return;
  }

  setResult(MenuResult{static_cast<int>(selectedAction), pendingOrientation, selectedPageTurnOption});
  finish();
}

bool EpubReaderMenuActivity::handleCustomInput() {
  return optionPopup.handleInput(mappedInput, [this] { requestUpdate(); });
}

bool EpubReaderMenuActivity::handleButtons() {
  if (mappedInput.wasReleased(MappedInputManager::Button::Back)) {
    closeCancelled();
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

void EpubReaderMenuActivity::buildScreen(UiScreen& screen) {
  const auto& metrics = UITheme::getInstance().getMetrics();
  const Rect safe = UITheme::getInstance().getScreenSafeArea(renderer, true, false);
  screen.setContentMargin(fui::Insets{static_cast<int16_t>(safe.y + metrics.topPadding + metrics.headerHeight),
                                      static_cast<int16_t>(renderer.getScreenWidth() - (safe.x + safe.width)),
                                      static_cast<int16_t>(renderer.getScreenHeight() - (safe.y + safe.height)),
                                      static_cast<int16_t>(safe.x)});

  buildTabBar(screen);

  std::string progressLine;
  if (totalPages > 0) {
    progressLine = std::string(tr(STR_CHAPTER_PREFIX)) + std::to_string(currentPage) + "/" +
                   std::to_string(totalPages) + std::string(tr(STR_PAGES_SEPARATOR));
  }
  progressLine += std::string(tr(STR_BOOK_PREFIX)) + std::to_string(bookProgressPercent) + "%";
  const fui::Rect band = screen.takeTop(static_cast<int16_t>(metrics.tabBarHeight));
  const int16_t pad = screen.theme().headerSidePadding;
  screen.target().text(band.inset(fui::Insets{0, pad, 0, pad}), progressLine.c_str(), screen.theme().smallText);
  const int16_t progressGap = static_cast<int16_t>(
      SETTINGS.uiTheme == CrossPointSettings::ROUNDEDRAFF ? metrics.verticalSpacing - 2 : metrics.verticalSpacing);
  screen.spacer(progressGap);

  const auto& items = activeItems();
  for (size_t i = 0; i < items.size(); ++i) {
    const auto action = items[i].action;
    if (action == MenuAction::WORD_SELECTION_MODE) {
      static const char* modeLabels[] = {"Szótár", "Megjelölés", "Szerkesztés"};
      menuRowItems[i].value = modeLabels[SETTINGS.wordSelectionMode <= 2 ? SETTINGS.wordSelectionMode : 0];
    } else if (action == MenuAction::ROTATE_SCREEN) {
      menuRowItems[i].value = I18N.get(orientationLabels[pendingOrientation]);
    } else if (action == MenuAction::AUTO_PAGE_TURN) {
      menuRowItems[i].value = pageTurnLabels[selectedPageTurnOption];
    } else if (action == MenuAction::DICTIONARY_SETTINGS) {
      dictionaryRowLabel = "Szótár: ";
      if (selectedDictionaryOption < dictionaryOptionPointers.size() &&
          dictionaryOptionPointers[selectedDictionaryOption] &&
          dictionaryOptionPointers[selectedDictionaryOption][0] != ' ') {
        dictionaryRowLabel += dictionaryOptionPointers[selectedDictionaryOption];
      } else {
        dictionaryRowLabel += "Nincs beállítva";
      }
      menuRowItems[i].label = dictionaryRowLabel.c_str();
      menuRowItems[i].value = nullptr;
    } else if (action == MenuAction::NIGHT_MODE) {
      menuRowItems[i].value = I18N.get(SETTINGS.screenInverted ? StrId::STR_STATE_ON : StrId::STR_STATE_OFF);
    } else if (action == MenuAction::FRONTLIGHT) {
      menuRowItems[i].value = I18N.get(Frontlight.isOn() ? StrId::STR_STATE_ON : StrId::STR_STATE_OFF);
    }
  }

  fui::ListProps props;
  props.items = menuRowItems.data();
  props.count = static_cast<uint16_t>(items.size());
  props.action = ACTION_ROW;
  props.inputMask = fui::InputTouch;
  props.valueInset = 8;
  if (SETTINGS.uiTheme == CrossPointSettings::ROUNDEDRAFF) props.rowGap = 4;
  props.labelText = screen.theme().bodyText;
  props.labelText.maxLines = 2;
  const int16_t compactRowHeight = static_cast<int16_t>(metrics.listRowHeight - 2);
  syncTabListViewport(screen, props, false, compactRowHeight);
  screen.list(props);
}

void EpubReaderMenuActivity::drawChrome() {
  const auto& metrics = UITheme::getInstance().getMetrics();
  const Rect screen = UITheme::getInstance().getScreenSafeArea(renderer, true, false);
  GUI.drawHeader(renderer, Rect{screen.x, screen.y + metrics.topPadding, screen.width, metrics.headerHeight},
                 title.c_str());
}

void EpubReaderMenuActivity::drawFooter() { UiTabListActivity::drawFooter(); }

void EpubReaderMenuActivity::render(RenderLock&&) {
  if (optionPopup.processRender(renderer, mappedInput)) return;
  renderer.clearScreen();
  drawChrome();
  renderUi();
  drawFooter();
  renderer.displayBuffer(HalDisplay::FAST_REFRESH);
}
