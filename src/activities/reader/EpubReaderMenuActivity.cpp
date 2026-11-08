#include "EpubReaderMenuActivity.h"

#include <BlePageTurner.h>
#include <GfxRenderer.h>
#include <HalFrontlight.h>
#include <I18n.h>

#include <algorithm>
#include <iterator>

#include "CrossPointSettings.h"
#include "KOReaderCredentialStore.h"
#include "MappedInputManager.h"
#include "ReaderUtils.h"
#include "components/UITheme.h"
#include "util/PluginEvents.h"
#include "util/SlideSwitch.h"

namespace fui = freeink::ui;

EpubReaderMenuActivity::EpubReaderMenuActivity(GfxRenderer& renderer, MappedInputManager& mappedInput,
                                               const std::string& title, const int currentPage, const int totalPages,
                                               const int bookProgressPercent, const uint8_t currentOrientation,
                                               const bool hasFootnotes, const bool hasBookmarks,
                                               const bool hasClippings, const bool currentPageBookmarked, MenuAction& selectedAction)
    : UiTabListActivity("EpubReaderMenu", renderer, mappedInput),
      selectedAction(selectedAction),
      currentPageBookmarked(currentPageBookmarked),
      title(title),
      pendingOrientation(currentOrientation),
      currentPage(currentPage),
      totalPages(totalPages),
      bookProgressPercent(bookProgressPercent) {
  buildMenuItems(menuItems, hasFootnotes, hasBookmarks, hasClippings);
  splitMenuItems();
  buildMenuRowItems();
}

const std::vector<EpubReaderMenuActivity::MenuItem>& EpubReaderMenuActivity::activeItems() const {
  return tab_ == Tab::Reading ? readingItems : bookItems;
}

const char* EpubReaderMenuActivity::tabLabel(int index) const {
  return index == 0 ? (I18N.getLanguage() == Language::HU ? "Olvasás" : "Reading")
                    : (I18N.getLanguage() == Language::HU ? "Könyv" : "Book");
}

void EpubReaderMenuActivity::splitMenuItems() {
  readingItems.clear();
  bookItems.clear();
  // Keep only implemented actions. Reorder within the two tabs to match the
  // CPHUN-261007-224 X4 menu; missing X4 features will be ported separately.
  constexpr MenuAction readingOrder[] = {
      MenuAction::SELECT_CHAPTER, MenuAction::FOOTNOTES, MenuAction::BOOKMARKS,
      MenuAction::TOGGLE_BOOKMARK, MenuAction::SAVE_CLIPPING, MenuAction::VIEW_CLIPPINGS,
      MenuAction::DICTIONARY, MenuAction::FRONTLIGHT, MenuAction::AUTO_PAGE_TURN,
      MenuAction::GO_TO_PERCENT};
  constexpr MenuAction bookOrder[] = {
      MenuAction::BOOK_DESCRIPTION, MenuAction::BOOK_METADATA, MenuAction::ROTATE_SCREEN,
      MenuAction::TEXT_SETTINGS, MenuAction::SCREENSHOT, MenuAction::SYNC,
      MenuAction::BLUETOOTH, MenuAction::GO_HOME};
  auto appendInOrder = [this](const MenuAction* order, size_t count, std::vector<MenuItem>& target) {
    for (size_t i = 0; i < count; ++i) {
      const auto found = std::find_if(menuItems.begin(), menuItems.end(),
                                    [action = order[i]](const MenuItem& item) { return item.action == action; });
      if (found != menuItems.end()) target.push_back(*found);
    }
  };
  appendInOrder(readingOrder, std::size(readingOrder), readingItems);
  appendInOrder(bookOrder, std::size(bookOrder), bookItems);
}

void EpubReaderMenuActivity::onTabAction(int index) {
  if (index < 0 || index >= tabCount()) return;
  tab_ = static_cast<Tab>(index);
  buildMenuRowItems();
  moveRingTo(0);
}

void EpubReaderMenuActivity::stepTab(int direction) {
  onTabAction((activeTab() + direction + tabCount()) % tabCount());
}

void EpubReaderMenuActivity::onEnter() {
  RenderLock lock;
  UiTabListActivity::onEnter();
  for (int tab = 0; tab < tabCount(); ++tab) {
    const auto& items = tab == 0 ? readingItems : bookItems;
    for (size_t i = 0; i < items.size(); ++i) {
      if (items[i].action == selectedAction) {
        tab_ = static_cast<Tab>(tab);
        tabNavs[tab].selected = static_cast<int>(i) + 1;
        buildMenuRowItems();
        return;
      }
    }
  }
  tabNavs[activeTab()].selected = 0;
}

void EpubReaderMenuActivity::onExit() {
  const auto& items = activeItems();
  if (ringPos() > 0 && ringPos() <= static_cast<int>(items.size())) {
    selectedAction = items[ringPos() - 1].action;
  }
  UiTabListActivity::onExit();
}

// Populates menuRowItems's labels/actionValue from menuItems. Called once
// here since menuItems (and thus which rows exist) never changes after
// construction; buildScreen() only touches the two rows with a live value.
void EpubReaderMenuActivity::buildMenuRowItems() {
  for (auto& item : menuRowItems) item = {};
  const auto& items = activeItems();
  for (size_t i = 0; i < items.size() && i < MAX_MENU_ITEMS; i++) {
    fui::ListItem item;
    item.label = items[i].action == MenuAction::TOGGLE_BOOKMARK
                     ? (I18N.getLanguage() == Language::HU
                            ? (currentPageBookmarked ? "Könyvjelző törlése" : "Könyvjelző hozzáadása")
                            : (currentPageBookmarked ? "Remove Bookmark" : "Add Bookmark"))
                     : (items[i].customLabel ? items[i].customLabel : I18N.get(items[i].labelId));
    item.actionValue = static_cast<int16_t>(i);
    menuRowItems[i] = item;
  }
}

void EpubReaderMenuActivity::buildMenuItems(std::vector<MenuItem>& items, const bool hasFootnotes,
                                            const bool hasBookmarks, const bool hasClippings) {
  items.clear();
  items.reserve(MAX_MENU_ITEMS);
  items.push_back({MenuAction::SELECT_CHAPTER, StrId::STR_SELECT_CHAPTER});
  if (hasFootnotes) {
    items.push_back({MenuAction::FOOTNOTES, StrId::STR_FOOTNOTES});
  }
  if (hasBookmarks) {
    items.push_back({MenuAction::BOOKMARKS, StrId::STR_BOOKMARKS});
  }
  items.push_back({MenuAction::TOGGLE_BOOKMARK, StrId::STR_TOGGLE_BOOKMARK});
  items.push_back({MenuAction::SAVE_CLIPPING, StrId::STR_SAVE_CLIPPING});
  if (hasClippings) {
    items.push_back({MenuAction::VIEW_CLIPPINGS, StrId::STR_VIEW_CLIPPINGS});
  }
  if (Frontlight.present() && !slideSwitchOwnsLight()) {
    items.push_back({MenuAction::FRONTLIGHT, StrId::STR_FRONTLIGHT});
  }
  if (bleturner::status().compiledIn && SETTINGS.ble.peerAddr[0] != '\0') {
    items.push_back({MenuAction::BLUETOOTH, StrId::STR_BT_PAGE_TURNER});
  }
  if (SETTINGS.dictionaryName[0] != '\0') {
    items.push_back({MenuAction::DICTIONARY, StrId::STR_LOOKUP});
  }
  items.push_back({MenuAction::ROTATE_SCREEN, StrId::STR_ORIENTATION});
  items.push_back({MenuAction::AUTO_PAGE_TURN, StrId::STR_AUTO_TURN_PAGES_PER_MIN});
  items.push_back({MenuAction::GO_TO_PERCENT, StrId::STR_GO_TO_PERCENT});
  items.push_back({MenuAction::SCREENSHOT, StrId::STR_SCREENSHOT_BUTTON});
  items.push_back({MenuAction::GO_HOME, StrId::STR_GO_HOME_BUTTON});
  bool canSync = KOREADER_STORE.hasCredentials();
  for (size_t event = 0; !canSync && event < static_cast<size_t>(pluginevents::Event::COUNT); ++event) {
    canSync = pluginevents::anySubscriber(static_cast<pluginevents::Event>(event));
  }
  if (canSync) {
    items.push_back({MenuAction::SYNC, StrId::STR_SYNC_PROGRESS});
  }
  items.push_back({MenuAction::BOOK_DESCRIPTION, StrId::STR_TEXT_SETTINGS,
                   I18N.getLanguage() == Language::HU ? "Fülszöveg" : "Description"});
  items.push_back({MenuAction::BOOK_METADATA, StrId::STR_TEXT_SETTINGS,
                   I18N.getLanguage() == Language::HU ? "Metaadatok" : "Metadata"});
  items.push_back({MenuAction::TEXT_SETTINGS, StrId::STR_TEXT_SETTINGS});
}

void EpubReaderMenuActivity::toggleBluetooth() {
  SETTINGS.ble.enabled = SETTINGS.ble.enabled ? 0 : 1;
  if (!SETTINGS.ble.enabled) bleturner::switchOff();
  SETTINGS.saveToFile();
  // Enabling waits for the main-loop lifecycle's reader heap gates, then says in the status bar
  // whether a remote linked.
  if (SETTINGS.ble.enabled) bleturner::requestConnect();
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
  // The activated row leaves this screen (popup or finish); a lingering flash
  // would gray an unrelated element on the next render.
  app.clearTapFlash();
  if (index < 0 || index >= listCount()) return;
  activeNav().selected = index + 1;

  const auto selectedAction = activeItems()[index].action;
  if (selectedAction == MenuAction::ROTATE_SCREEN) {
    optionPopup.show(StrId::STR_ORIENTATION, orientationLabels.data(), static_cast<int>(orientationLabels.size()),
                     pendingOrientation, [this](int idx) {
                       pendingOrientation = idx;
                       // Rotate the menu immediately. Only the renderer turns;
                       // SETTINGS.orientation stays unchanged so the reader's
                       // result handler still detects the change and reflows.
                       ReaderUtils::applyOrientation(renderer, pendingOrientation);
                       app.setDevice(uiTarget.deviceContext());  // hit rects follow the new frame
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

  if (selectedAction == MenuAction::NIGHT_MODE) {
    SETTINGS.screenInverted = SETTINGS.screenInverted == 0 ? 1 : 0;
    SETTINGS.saveToFile();
    requestUpdate();
    return;
  }

  if (selectedAction == MenuAction::BLUETOOTH) {
    toggleBluetooth();
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
    if (ringPos() == 0) stepTab(1);
    else activateIndex(ringPos() - 1);
    return true;
  }

  return false;
}

void EpubReaderMenuActivity::buildScreen(UiScreen& screen) {
  const auto& metrics = UITheme::getInstance().getMetrics();
  const Rect safe = UITheme::getInstance().getScreenSafeArea(renderer, true, false);
  // Content: the safe area minus the header band GUI.drawHeader paints.
  screen.setContentMarginFromScreen(fui::Insets{
      static_cast<int16_t>(safe.y + metrics.topPadding + metrics.headerHeight),
      static_cast<int16_t>(renderer.getScreenWidth() - (safe.x + safe.width)),
      static_cast<int16_t>(renderer.getScreenHeight() - (safe.y + safe.height)), static_cast<int16_t>(safe.x)});

  buildTabBar(screen);

  // Progress summary below the two reading/book tabs.
  std::string progressLine;
  if (totalPages > 0) {
    progressLine = std::string(tr(STR_CHAPTER_PREFIX)) + std::to_string(currentPage) + "/" +
                   std::to_string(totalPages) + std::string(tr(STR_PAGES_SEPARATOR));
  }
  progressLine += std::string(tr(STR_BOOK_PREFIX)) + std::to_string(bookProgressPercent) + "%";
  const fui::Rect band = screen.takeTop(static_cast<int16_t>(metrics.tabBarHeight));
  const int16_t pad = screen.theme().headerSidePadding;
  screen.target().text(band.inset(fui::Insets{0, pad, 0, pad}), progressLine.c_str(), screen.theme().smallText);
  screen.spacer(static_cast<int16_t>(metrics.verticalSpacing));

  // menuRowItems's labels/actionValue were set once in the constructor (see
  // buildMenuRowItems()); only rows with live values need refreshing here.
  const auto& items = activeItems();
  for (size_t i = 0; i < items.size(); i++) {
    const auto action = items[i].action;
    if (action == MenuAction::ROTATE_SCREEN) {
      menuRowItems[i].value = I18N.get(orientationLabels[pendingOrientation]);
    } else if (action == MenuAction::AUTO_PAGE_TURN) {
      menuRowItems[i].value = pageTurnLabels[selectedPageTurnOption];
    } else if (action == MenuAction::NIGHT_MODE) {
      menuRowItems[i].toggle = false;
      menuRowItems[i].value = SETTINGS.screenInverted ? tr(STR_STATE_ON) : tr(STR_STATE_OFF);
    } else if (action == MenuAction::BLUETOOTH) {
      GUI.setCheckboxRow(menuRowItems[i], SETTINGS.ble.enabled);
    } else if (action == MenuAction::FRONTLIGHT) {
      GUI.setCheckboxRow(menuRowItems[i], Frontlight.isOn());
    }
  }

  fui::ListProps props;
  props.items = menuRowItems;
  props.count = static_cast<uint16_t>(items.size());
  props.action = ACTION_ROW;
  props.inputMask = fui::InputTouch;  // physical buttons stay in loop()
  props.valueInset = 8;               // air between the value and the row edge
  // Label at the value's font size: both sides of the row read as one unit.
  // maxLines=2 also marks the style caller-owned (see textStyleUnset).
#if FREEINK_DEVICE_PICCO
  props.labelText = SETTINGS.uiSize == CrossPointSettings::UI_SIZE_NORMAL ? screen.theme().bodyText
                                                                          : screen.theme().smallText;
#else
  props.labelText = screen.theme().smallText;
#endif
  props.labelText.maxLines = 2;
#if FREEINK_DEVICE_PICCO
  props.rowHeight = 47;
#endif
  syncTabListViewport(screen, props);
  screen.list(props);
}

void EpubReaderMenuActivity::drawChrome() {
  // Header via GUI.drawHeader (already FreeInkUI-themed) for the battery
  // indicator; the rest of the screen renders through the app.
  GUI.drawHeader(renderer, UITheme::getInstance().getHeaderRect(renderer, true, false), title.c_str());
}

void EpubReaderMenuActivity::render(RenderLock&& lock) {
  if (optionPopup.processRender(renderer, mappedInput)) return;

  UiListActivity::render(std::move(lock));
}
