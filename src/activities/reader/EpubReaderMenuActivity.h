#pragma once
#include <Epub.h>
#include <I18n.h>

#include <array>
#include <string>
#include <vector>

#include "activities/UiTabListActivity.h"
#include "components/OptionPopup.h"

class EpubReaderMenuActivity final : public UiTabListActivity {
 public:
  enum class MenuAction {
    SELECT_CHAPTER,
    FOOTNOTES,
    TEXT_SETTINGS,
    NIGHT_MODE,
    FRONTLIGHT,
    GO_TO_PERCENT,
    AUTO_PAGE_TURN,
    ROTATE_SCREEN,
    BOOKMARKS,
    TOGGLE_BOOKMARK,
    SCREENSHOT,
    DISPLAY_QR,
    GO_HOME,
    SYNC,
    DELETE_CACHE,
    DICTIONARY,
    BOOK_INFO
  };

  explicit EpubReaderMenuActivity(GfxRenderer& renderer, MappedInputManager& mappedInput, const std::string& title,
                                  int currentPage, int totalPages, int bookProgressPercent, uint8_t currentOrientation,
                                  bool hasFootnotes, bool hasBookmarks);

  void render(RenderLock&&) override;
  bool handleHomeGesture() override;

 private:
  struct MenuItem {
    MenuAction action;
    StrId labelId;
    const char* overrideLabel = nullptr;
  };

  enum class Tab : uint8_t { Reading = 0, More = 1, Count = 2 };

  static std::vector<MenuItem> buildReadingItems(bool hasFootnotes, bool hasBookmarks);
  static std::vector<MenuItem> buildMoreItems();
  const std::vector<MenuItem>& activeItems() const;
  void rebuildMenuRowItems();

  static constexpr size_t MAX_MENU_ITEMS = 12;
  std::array<freeink::ui::ListItem, MAX_MENU_ITEMS> menuRowItems{};

  int listCount() const override { return static_cast<int>(activeItems().size()); }
  int tabCount() const override { return static_cast<int>(Tab::Count); }
  int activeTab() const override { return static_cast<int>(tab_); }
  const char* tabLabel(int index) const override;
  int tabWidthPercent(int index) const override;
  void onTabAction(int index) override;
  void stepTab(int direction) override;

  void buildScreen(UiScreen& screen) override;
  void activateIndex(int index) override;
  bool handleCustomInput() override;
  bool handleButtons() override;
  void drawChrome() override;
  void closeCancelled();

  std::vector<MenuItem> readingItems;
  std::vector<MenuItem> moreItems;
  Tab tab_ = Tab::Reading;
  OptionPopup optionPopup;
  std::string title = "Reader Menu";
  uint8_t pendingOrientation = 0;
  uint8_t selectedPageTurnOption = 0;
  const std::vector<StrId> orientationLabels = {StrId::STR_PORTRAIT, StrId::STR_LANDSCAPE_CW, StrId::STR_INVERTED,
                                                StrId::STR_LANDSCAPE_CCW};
  const std::vector<const char*> pageTurnLabels = {I18N.get(StrId::STR_STATE_OFF), "1", "3", "6", "12"};
  int currentPage = 0;
  int totalPages = 0;
  int bookProgressPercent = 0;
};
