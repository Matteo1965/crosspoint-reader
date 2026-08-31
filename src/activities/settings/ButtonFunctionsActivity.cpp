#include "ButtonFunctionsActivity.h"

#include <I18n.h>

#include "ReaderButtonProfileStore.h"
#include "components/UITheme.h"
#include "fontIds.h"

namespace fui = freeink::ui;

namespace {
constexpr ReaderAction ACTIONS[] = {
    ReaderAction::None,          ReaderAction::ReaderBack,          ReaderAction::PreviousPage,
    ReaderAction::NextPage,      ReaderAction::PreviousChapter,     ReaderAction::NextChapter,
    ReaderAction::OpenReaderMenu, ReaderAction::OpenDictionary,      ReaderAction::OpenBookmarks,
    ReaderAction::ToggleBookmark, ReaderAction::OpenChapterSelection, ReaderAction::OpenGoToPercent,
    ReaderAction::OpenTextSettings, ReaderAction::OpenFontMenu,       ReaderAction::OpenFontSizeMenu,
    ReaderAction::OpenLayoutMenu, ReaderAction::OpenStyleMenu,       ReaderAction::FontNext,
    ReaderAction::FontPrevious,  ReaderAction::FontSizeUp,           ReaderAction::FontSizeDown,
    ReaderAction::LineSpacingNext, ReaderAction::LineSpacingPrevious, ReaderAction::ScreenMarginUp,
    ReaderAction::ScreenMarginDown, ReaderAction::ToggleNightMode,    ReaderAction::ToggleHyphenation,
    ReaderAction::ToggleSoftHyphen, ReaderAction::ToggleParagraphAlignment, ReaderAction::RotateOrientation,
    ReaderAction::ForceRefresh, ReaderAction::Screenshot, ReaderAction::GoHome,
};

constexpr int kMappingCount = 12;
constexpr int kReferenceWidth = 480;
constexpr int kGestureX = 40;
constexpr int kButtonX = 145;
constexpr int kActionX = 285;

int scaledX(const int x, const int width) { return x * width / kReferenceWidth; }
}  // namespace

ButtonFunctionsActivity::ButtonFunctionsActivity(GfxRenderer& renderer, MappedInputManager& mappedInput)
    : UiListActivity("ButtonFunctions", renderer, mappedInput) {}

void ButtonFunctionsActivity::onEnter() {
  UiListActivity::onEnter();
  rebuildRows();
}

const char* ButtonFunctionsActivity::headerTitle() const {
  return I18N.getLanguage() == Language::HU ? "Alsó gombok" : "Bottom buttons";
}

ReaderPhysicalButton ButtonFunctionsActivity::buttonForRow(const int row) {
  return static_cast<ReaderPhysicalButton>(row % 4);
}

ReaderButtonGesture ButtonFunctionsActivity::gestureForRow(const int row) {
  return static_cast<ReaderButtonGesture>(row / 4);
}

const char* ButtonFunctionsActivity::actionLabel(const ReaderAction action) {
  const bool hu = I18N.getLanguage() == Language::HU;
  switch (action) {
    case ReaderAction::None: return hu ? "Nincs" : "None";
    case ReaderAction::ReaderBack: return hu ? "Vissza" : "Back";
    case ReaderAction::PreviousPage: return hu ? "Előző oldal" : "Previous page";
    case ReaderAction::NextPage: return hu ? "Következő oldal" : "Next page";
    case ReaderAction::PreviousChapter: return hu ? "Előző fejezet" : "Previous chapter";
    case ReaderAction::NextChapter: return hu ? "Következő fejezet" : "Next chapter";
    case ReaderAction::OpenReaderMenu: return hu ? "Olvasómenü" : "Reader menu";
    case ReaderAction::OpenDictionary: return hu ? "Szótár" : "Dictionary";
    case ReaderAction::OpenBookmarks: return hu ? "Könyvjelzők" : "Bookmarks";
    case ReaderAction::ToggleBookmark: return hu ? "Könyvjelző váltás" : "Toggle bookmark";
    case ReaderAction::OpenChapterSelection: return hu ? "Fejezetválasztás" : "Chapter selection";
    case ReaderAction::OpenGoToPercent: return hu ? "Ugrás %-ra" : "Go to %";
    case ReaderAction::OpenTextSettings: return hu ? "Szövegbeállítások" : "Text settings";
    case ReaderAction::OpenFontMenu: return hu ? "Betű" : "Font";
    case ReaderAction::OpenFontSizeMenu: return hu ? "Méret" : "Size";
    case ReaderAction::OpenLayoutMenu: return hu ? "Rendez." : "Layout";
    case ReaderAction::OpenStyleMenu: return hu ? "Stílus" : "Style";
    case ReaderAction::FontNext: return hu ? "Következő betű" : "Next font";
    case ReaderAction::FontPrevious: return hu ? "Előző betű" : "Previous font";
    case ReaderAction::FontSizeUp: return hu ? "Betűméret +" : "Font size +";
    case ReaderAction::FontSizeDown: return hu ? "Betűméret −" : "Font size -";
    case ReaderAction::LineSpacingNext: return hu ? "Sorköz +" : "Line spacing +";
    case ReaderAction::LineSpacingPrevious: return hu ? "Sorköz −" : "Line spacing -";
    case ReaderAction::ScreenMarginUp: return hu ? "Margó +" : "Margin +";
    case ReaderAction::ScreenMarginDown: return hu ? "Margó −" : "Margin -";
    case ReaderAction::ToggleNightMode: return hu ? "Éjszakai mód" : "Night mode";
    case ReaderAction::ToggleHyphenation: return hu ? "Elválasztás" : "Hyphenation";
    case ReaderAction::ToggleSoftHyphen: return "Soft Hyphen";
    case ReaderAction::ToggleParagraphAlignment: return hu ? "Igazítás váltás" : "Toggle alignment";
    case ReaderAction::RotateOrientation: return hu ? "Képernyő forgatás" : "Rotate screen";
    case ReaderAction::ForceRefresh: return hu ? "Képernyőfrissítés" : "Screen refresh";
    case ReaderAction::Screenshot: return hu ? "Képernyőkép" : "Screenshot";
    case ReaderAction::GoHome: return hu ? "Főoldal" : "Home";
    default: return hu ? "Nincs" : "None";
  }
}

void ButtonFunctionsActivity::rebuildRows() {
  labels_.resize(kMappingCount);
  values_.resize(kMappingCount);
  rows_.resize(kMappingCount);

  for (int row = 0; row < kMappingCount; ++row) {
    labels_[row] = std::to_string(row % 4 + 1) + ". gomb";
    values_[row] = std::string("[") + actionLabel(READER_BUTTONS.get(buttonForRow(row), gestureForRow(row))) + "]";

    // The FreeInk list owns navigation, selection highlighting and hit boxes,
    // but text is drawn below in fixed columns. Empty item strings prevent the
    // proportional list layout from moving columns according to text width.
    rows_[row].label = "";
    rows_[row].value = "";
    rows_[row].actionValue = static_cast<int16_t>(row);
  }
}

void ButtonFunctionsActivity::buildScreen(UiScreen& screen) {
  const auto& metrics = UITheme::getInstance().getMetrics();
  // Keep one full blank row below the title. There is deliberately no prompt
  // row: all available vertical space belongs to the 12 mappings.
  screen.setContentMargin(
      fui::Insets{static_cast<int16_t>(metrics.topPadding + metrics.headerHeight + metrics.listRowHeight), 0,
                  static_cast<int16_t>(metrics.buttonHintsHeight), 0});

  rebuildRows();
  fui::ListProps props;
  props.items = rows_.data();
  props.count = static_cast<uint16_t>(rows_.size());
  props.action = ACTION_ROW;
  props.inputMask = fui::InputTouch;
  props.labelText = screen.theme().smallText;
  props.valueText = screen.theme().smallText;
  syncListViewport(screen, props);
  screen.list(props);
}

void ButtonFunctionsActivity::drawFooter() {
  const auto& metrics = UITheme::getInstance().getMetrics();
  const int width = renderer.getScreenWidth();
  const int rowHeight = metrics.listRowHeight;
  const int listTop = metrics.topPadding + metrics.headerHeight + rowHeight;
  const int textHeight = renderer.getTextHeight(SMALL_FONT_ID);
  const int firstVisible = activeNav().top;
  const int selected = activeNav().selected;

  const int gestureX = scaledX(kGestureX, width);
  const int buttonX = scaledX(kButtonX, width);
  const int actionX = scaledX(kActionX, width);

  for (int row = firstVisible; row < kMappingCount; ++row) {
    const int visualRow = row - firstVisible;
    const int rowTop = listTop + visualRow * rowHeight;
    if (rowTop + rowHeight > renderer.getScreenHeight() - metrics.buttonHintsHeight) break;

    const int textY = rowTop + std::max(0, (rowHeight - textHeight) / 2);
    const bool black = row != selected;

    if (row % 4 == 0) {
      const int group = row / 4;
      const char* gesture = group == 0 ? "1×:" : (group == 1 ? "2×:" : (I18N.getLanguage() == Language::HU ? "Tart:" : "Hold:"));
      renderer.drawText(SMALL_FONT_ID, gestureX, textY, gesture, black);
    }
    renderer.drawText(SMALL_FONT_ID, buttonX, textY, labels_[row].c_str(), black);
    renderer.drawText(SMALL_FONT_ID, actionX, textY, values_[row].c_str(), black);
  }

  UiListActivity::drawFooter();
}

bool ButtonFunctionsActivity::handleCustomInput() {
  return optionPopup_.handleInput(mappedInput, [this] {
    rebuildRows();
    requestUpdate();
  });
}

void ButtonFunctionsActivity::activateIndex(const int index) {
  if (index < 0 || index >= kMappingCount) return;
  openActionPicker(index);
}

void ButtonFunctionsActivity::openActionPicker(const int row) {
  const ReaderAction selected = READER_BUTTONS.get(buttonForRow(row), gestureForRow(row));
  int current = 0;
  std::vector<std::string> options;
  options.reserve(std::size(ACTIONS));
  for (int i = 0; i < static_cast<int>(std::size(ACTIONS)); ++i) {
    options.emplace_back(actionLabel(ACTIONS[i]));
    if (ACTIONS[i] == selected) current = i;
  }

  std::vector<const char*> optionPtrs;
  optionPtrs.reserve(options.size());
  for (const auto& option : options) optionPtrs.push_back(option.c_str());

  const std::string title = labels_[row];
  optionPopup_.show(title.c_str(), optionPtrs.data(), static_cast<int>(optionPtrs.size()), current,
                    [this, row](int idx) {
                      READER_BUTTONS.set(buttonForRow(row), gestureForRow(row), ACTIONS[idx]);
                      READER_BUTTONS.saveToFile();
                      rebuildRows();
                    });
  requestUpdate();
}
