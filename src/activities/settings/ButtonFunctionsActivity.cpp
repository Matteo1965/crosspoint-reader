#include "ButtonFunctionsActivity.h"

#include <I18n.h>

#include "ReaderButtonProfileStore.h"
#include "components/UITheme.h"

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
}

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
    case ReaderAction::ToggleSoftHyphen: return hu ? "Soft Hyphen" : "Soft Hyphen";
    case ReaderAction::ToggleParagraphAlignment: return hu ? "Igazítás váltás" : "Toggle alignment";
    case ReaderAction::RotateOrientation: return hu ? "Képernyő forgatás" : "Rotate screen";
    case ReaderAction::ForceRefresh: return hu ? "Képernyőfrissítés" : "Screen refresh";
    case ReaderAction::Screenshot: return hu ? "Képernyőkép" : "Screenshot";
    case ReaderAction::GoHome: return hu ? "Főoldal" : "Home";
    default: return hu ? "Nincs" : "None";
  }
}

void ButtonFunctionsActivity::rebuildRows() {
  labels_.resize(12);
  values_.resize(12);
  rows_.resize(12);
  for (int row = 0; row < 12; ++row) {
    const int button = row % 4 + 1;
    const int group = row / 4;
    const char* prefix = "";
    if (row % 4 == 0) {
      if (group == 0) prefix = "1×:   ";
      else if (group == 1) prefix = "2×:   ";
      else prefix = I18N.getLanguage() == Language::HU ? "Tart:  " : "Hold:  ";
    } else {
      prefix = "      ";
    }
    labels_[row] = std::string(prefix) + std::to_string(button) + ". gomb";
    values_[row] = std::string("[") + actionLabel(READER_BUTTONS.get(buttonForRow(row), gestureForRow(row))) + "]";
    rows_[row].label = labels_[row].c_str();
    rows_[row].value = values_[row].c_str();
    rows_[row].actionValue = static_cast<int16_t>(row);
  }
}

void ButtonFunctionsActivity::buildScreen(UiScreen& screen) {
  const auto& metrics = UITheme::getInstance().getMetrics();
  screen.setContentMargin(fui::Insets{static_cast<int16_t>(metrics.topPadding + metrics.headerHeight), 0,
                                      static_cast<int16_t>(metrics.buttonHintsHeight), 0});
  rebuildRows();
  fui::ListProps props;
  props.items = rows_.data();
  props.count = static_cast<uint16_t>(rows_.size());
  props.action = ACTION_ROW;
  props.inputMask = fui::InputTouch;
  props.valueInset = 4;
  props.labelText = screen.theme().smallText;
  props.valueText = screen.theme().smallText;
  syncListViewport(screen, props);
  screen.list(props);
}

bool ButtonFunctionsActivity::handleCustomInput() {
  return optionPopup_.handleInput(mappedInput, [this] {
    rebuildRows();
    requestUpdate();
  });
}

void ButtonFunctionsActivity::activateIndex(const int index) { openActionPicker(index); }

void ButtonFunctionsActivity::openActionPicker(const int row) {
  std::vector<std::string> options;
  options.reserve(std::size(ACTIONS));
  int current = 0;
  const ReaderAction selected = READER_BUTTONS.get(buttonForRow(row), gestureForRow(row));
  for (int i = 0; i < static_cast<int>(std::size(ACTIONS)); ++i) {
    options.emplace_back(actionLabel(ACTIONS[i]));
    if (ACTIONS[i] == selected) current = i;
  }
  const std::string title = labels_[row];
  optionPopup_.show(title.c_str(), options, current, [this, row](int idx) {
    READER_BUTTONS.set(buttonForRow(row), gestureForRow(row), ACTIONS[idx]);
    READER_BUTTONS.saveToFile();
    rebuildRows();
  });
  requestUpdate();
}
