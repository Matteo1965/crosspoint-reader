#include "ButtonFunctionsActivity.h"

#include <I18n.h>

#include "ReaderButtonProfileStore.h"
#include "components/UITheme.h"
#include "fontIds.h"

namespace fui = freeink::ui;

namespace {
constexpr ReaderAction READING_ACTIONS[] = {
    ReaderAction::None,
    ReaderAction::PreviousPage,
    ReaderAction::NextPage,
    ReaderAction::ReaderBack,
    ReaderAction::OpenReaderMenu,
    ReaderAction::OpenBookmarks,
    ReaderAction::ToggleBookmark,
    ReaderAction::OpenChapterSelection,
    ReaderAction::OpenDictionary,
    ReaderAction::OpenManualDictionarySearch,
    ReaderAction::OpenHighlight,
};

constexpr ReaderAction TEXT_ACTIONS[] = {
    ReaderAction::OpenTextSettings,
    ReaderAction::FontSizeDown,
    ReaderAction::FontSizeUp,
    ReaderAction::LineSpacingPrevious,
    ReaderAction::LineSpacingNext,
    ReaderAction::LetterSpacingCorrectionDown,
    ReaderAction::LetterSpacingCorrectionUp,
    ReaderAction::LetterSpacingOptimizationDown,
    ReaderAction::LetterSpacingOptimizationUp,
};

constexpr ReaderAction LAYOUT_ACTIONS[] = {
    ReaderAction::ExtraParagraphSpacingDown,
    ReaderAction::ExtraParagraphSpacingUp,
    ReaderAction::MinimumSpaceDown,
    ReaderAction::MinimumSpaceUp,
    ReaderAction::ScreenMarginDown,
    ReaderAction::ScreenMarginUp,
};

constexpr ReaderAction TEST_ACTIONS[] = {
    ReaderAction::TestLetterSpacingCorrectionMinMax,
    ReaderAction::TestLetterSpacingOptimizationOff100,
    ReaderAction::TestLineSpacingMinMax,
    ReaderAction::TestExtraParagraphSpacingOffMax,
    ReaderAction::TestMinimumSpaceMinMax,
};

constexpr ReaderAction SYSTEM_ACTIONS[] = {
    ReaderAction::ToggleNightMode,
    ReaderAction::Screenshot,
    ReaderAction::GoHome,
    ReaderAction::OpenSettings,
};

struct ActionCategory {
  const char* hu;
  const char* en;
  const ReaderAction* actions;
  size_t count;
};

constexpr ActionCategory ACTION_CATEGORIES[] = {
    {"Olvasás", "Reading", READING_ACTIONS, std::size(READING_ACTIONS)},
    {"Szöveg", "Text", TEXT_ACTIONS, std::size(TEXT_ACTIONS)},
    {"Elrendezés", "Layout", LAYOUT_ACTIONS, std::size(LAYOUT_ACTIONS)},
    {"Teszt funkciók", "Test functions", TEST_ACTIONS, std::size(TEST_ACTIONS)},
    {"Rendszer", "System", SYSTEM_ACTIONS, std::size(SYSTEM_ACTIONS)},
};

static_assert(std::size(READING_ACTIONS) <= 16);
static_assert(std::size(TEXT_ACTIONS) <= 16);
static_assert(std::size(LAYOUT_ACTIONS) <= 16);
static_assert(std::size(TEST_ACTIONS) <= 16);
static_assert(std::size(SYSTEM_ACTIONS) <= 16);

constexpr int kMappingCount = 12;
constexpr int kReferenceWidth = 480;
constexpr int kGestureX = 40;
constexpr int kButtonX = 135;
constexpr int kActionX = 248;

int scaledX(const int x, const int width) { return x * width / kReferenceWidth; }
}  // namespace

ButtonFunctionsActivity::ButtonFunctionsActivity(GfxRenderer& renderer, MappedInputManager& mappedInput)
    : UiListActivity("ButtonFunctions", renderer, mappedInput) {}

void ButtonFunctionsActivity::onEnter() {
  UiListActivity::onEnter();
  rebuildRows();
}

const char* ButtonFunctionsActivity::headerTitle() const {
  return I18N.getLanguage() == Language::HU ? "Alsó gombkiosztás" : "Bottom button mapping";
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
    case ReaderAction::OpenDictionary: return hu ? "Szótár" : "Search / Dictionary";
    case ReaderAction::OpenBookmarks: return hu ? "Könyvjelzők" : "Bookmarks";
    case ReaderAction::ToggleBookmark: return hu ? "Könyvjelző jelölés" : "Add bookmark";
    case ReaderAction::OpenChapterSelection: return hu ? "Fejezetválasztás" : "Chapter selection";
    case ReaderAction::OpenGoToPercent: return hu ? "Ugrás %-ra" : "Go to %";
    case ReaderAction::OpenTextSettings: return hu ? "Szövegbeállítások" : "Text settings";
    case ReaderAction::OpenFontMenu: return hu ? "Betű" : "Font";
    case ReaderAction::OpenFontSizeMenu: return hu ? "Méret" : "Size";
    case ReaderAction::OpenLayoutMenu: return hu ? "Képernyőelrendezés" : "Screen layout";
    case ReaderAction::OpenStyleMenu: return hu ? "Stílus" : "Style";
    case ReaderAction::FontNext: return hu ? "Következő betű" : "Next font";
    case ReaderAction::FontPrevious: return hu ? "Előző betű" : "Previous font";
    case ReaderAction::FontSizeUp: return hu ? "Betűméret +" : "Font size +";
    case ReaderAction::FontSizeDown: return hu ? "Betűméret −" : "Font size -";
    case ReaderAction::LineSpacingNext: return hu ? "Sorköz +" : "Line spacing +";
    case ReaderAction::LineSpacingPrevious: return hu ? "Sorköz −" : "Line spacing -";
    case ReaderAction::ScreenMarginUp: return hu ? "Margó növelése" : "Increase margin";
    case ReaderAction::ScreenMarginDown: return hu ? "Margó csökkentése" : "Decrease margin";
    case ReaderAction::ToggleNightMode: return hu ? "Sötét mód KI/BE" : "Night mode on/off";
    case ReaderAction::ToggleHyphenation: return hu ? "Elválasztás KI/BE" : "Hyphenation on/off";
    case ReaderAction::ToggleSoftHyphen: return hu ? "Kiterjesztett elválasztás KI/BE" : "Extended hyphenation on/off";
    case ReaderAction::ToggleParagraphAlignment: return hu ? "Igazítás váltás" : "Toggle alignment";
    case ReaderAction::RotateOrientation: return hu ? "Képernyő forgatás" : "Rotate screen";
    case ReaderAction::ForceRefresh: return hu ? "Képernyőfrissítés" : "Screen refresh";
    case ReaderAction::Screenshot: return hu ? "Képernyőkép" : "Screenshot";
    case ReaderAction::GoHome: return hu ? "Főoldal" : "Home";
    case ReaderAction::OpenSettings: return hu ? "Beállítások" : "Settings";
    case ReaderAction::LetterSpacingCorrectionUp: return hu ? "Betűköz korrekció növelése" : "Letter spacing correction +";
    case ReaderAction::LetterSpacingCorrectionDown: return hu ? "Betűköz korrekció csökkentése" : "Letter spacing correction -";
    case ReaderAction::LetterSpacingOptimizationUp: return hu ? "Betűköz optimalizálás növelése" : "Letter spacing optimization +";
    case ReaderAction::LetterSpacingOptimizationDown: return hu ? "Betűköz optimalizálás csökkentése" : "Letter spacing optimization -";
    case ReaderAction::ExtraParagraphSpacingUp: return hu ? "Extra bekezdésköz növelése" : "Extra paragraph spacing +";
    case ReaderAction::ExtraParagraphSpacingDown: return hu ? "Extra bekezdésköz csökkentése" : "Extra paragraph spacing -";
    case ReaderAction::MinimumSpaceUp: return hu ? "Min. szóköz növelése" : "Minimum word spacing +";
    case ReaderAction::MinimumSpaceDown: return hu ? "Min. szóköz csökkentése" : "Minimum word spacing -";
    case ReaderAction::OpenHighlight: return hu ? "Megjelölés" : "Mark word";
    case ReaderAction::OpenManualDictionarySearch: return hu ? "Kézi keresés" : "Manual search";
    case ReaderAction::TestLetterSpacingCorrectionMinMax: return hu ? "Betűköz korr. MIN/MAX" : "Letter correction MIN/MAX";
    case ReaderAction::TestLetterSpacingOptimizationOff100: return hu ? "Betűköz opt. KI/100%" : "Letter optimization OFF/100%";
    case ReaderAction::TestLineSpacingMinMax: return hu ? "Sorköz MIN/MAX" : "Line spacing MIN/MAX";
    case ReaderAction::TestExtraParagraphSpacingOffMax: return hu ? "Extra bekezdésköz KI/MAX" : "Paragraph spacing OFF/MAX";
    case ReaderAction::TestMinimumSpaceMinMax: return hu ? "Min. szóköz MIN/MAX" : "Word spacing MIN/MAX";
    default: return hu ? "Nincs" : "None";
  }
}

void ButtonFunctionsActivity::rebuildRows() {
  labels_.resize(kMappingCount);
  values_.resize(kMappingCount);
  rows_.resize(kMappingCount);

  for (int row = 0; row < kMappingCount; ++row) {
    labels_[row] = std::to_string(row % 4 + 1) + ". gomb";
    values_[row] = actionLabel(READER_BUTTONS.get(buttonForRow(row), gestureForRow(row)));

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
  const int rowGap = metrics.listRowGap;
  const int rowStep = rowHeight + rowGap;
  const int listTop = metrics.topPadding + metrics.headerHeight + rowHeight;
  const int textHeight = renderer.getTextHeight(UI_12_FONT_ID);
  const int firstVisible = activeNav().top;
  const int selected = activeNav().selected;

  const int gestureX = scaledX(kGestureX, width);
  const int buttonX = scaledX(kButtonX, width);
  const int actionX = scaledX(kActionX, width);

  for (int row = firstVisible; row < kMappingCount; ++row) {
    const int visualRow = row - firstVisible;
    // Use the exact same vertical stride as FreeInk's List: row height + theme gap.
    // Using rowHeight alone caused cumulative drift of the selection pill on RoundedRaff
    // (42 px row + 6 px gap): the pill moved 48 px while custom text moved only 42 px.
    const int rowTop = listTop + visualRow * rowStep;
    if (rowTop + rowHeight > renderer.getScreenHeight() - metrics.buttonHintsHeight) break;

    // Centre custom text inside the same row rectangle used by the FreeInk selection pill.
    const int textY = rowTop + std::max(0, (rowHeight - textHeight) / 2);
    const bool black = row != selected;

    if (row % 4 == 0) {
      const int group = row / 4;
      const char* gesture = group == 0 ? "1×:" : (group == 1 ? "2×:" : (I18N.getLanguage() == Language::HU ? "Hosszú:" : "Hold:"));
      renderer.drawText(UI_12_FONT_ID, gestureX, textY, gesture, black);
    }
    renderer.drawText(UI_12_FONT_ID, buttonX, textY, labels_[row].c_str(), black);
    renderer.drawText(UI_12_FONT_ID, actionX, textY, values_[row].c_str(), black);
  }

  UiListActivity::drawFooter();
  if (optionPopup_.isActive()) optionPopup_.render(renderer);
}

bool ButtonFunctionsActivity::handleCustomInput() {
  return optionPopup_.handleInput(mappedInput, [this] {
    rebuildRows();
    requestUpdate();
  });
}

void ButtonFunctionsActivity::activateIndex(const int index) {
  if (index < 0 || index >= kMappingCount) return;
  openCategoryPicker(index);
}

void ButtonFunctionsActivity::openCategoryPicker(const int row) {
  const bool hu = I18N.getLanguage() == Language::HU;
  std::vector<std::string> options;
  options.reserve(std::size(ACTION_CATEGORIES));
  for (const auto& category : ACTION_CATEGORIES) options.emplace_back(hu ? category.hu : category.en);

  std::vector<const char*> optionPtrs;
  optionPtrs.reserve(options.size());
  for (const auto& option : options) optionPtrs.push_back(option.c_str());

  const std::string title = labels_[row];
  optionPopup_.show(title.c_str(), optionPtrs.data(), static_cast<int>(optionPtrs.size()), 0,
                    [this, row, hu](int idx) {
                      if (idx < 0 || idx >= static_cast<int>(std::size(ACTION_CATEGORIES))) return;
                      const auto& category = ACTION_CATEGORIES[idx];
                      openActionPicker(row, category.actions, category.count, hu ? category.hu : category.en);
                    });
  requestUpdate();
}

void ButtonFunctionsActivity::openActionPicker(const int row, const ReaderAction* actions, const size_t actionCount,
                                               const char* categoryTitle) {
  const ReaderAction selected = READER_BUTTONS.get(buttonForRow(row), gestureForRow(row));
  int current = 0;
  std::vector<std::string> options;
  options.reserve(actionCount);
  for (size_t i = 0; i < actionCount; ++i) {
    options.emplace_back(actionLabel(actions[i]));
    if (actions[i] == selected) current = static_cast<int>(i);
  }

  std::vector<const char*> optionPtrs;
  optionPtrs.reserve(options.size());
  for (const auto& option : options) optionPtrs.push_back(option.c_str());

  const std::string title = labels_[row] + " - " + categoryTitle;
  optionPopup_.show(title.c_str(), optionPtrs.data(), static_cast<int>(optionPtrs.size()), current,
                    [this, row, actions, actionCount](int idx) {
                      if (idx < 0 || idx >= static_cast<int>(actionCount)) return;
                      READER_BUTTONS.set(buttonForRow(row), gestureForRow(row), actions[idx]);
                      READER_BUTTONS.saveToFile();
                      rebuildRows();
                    });
  requestUpdate();
}
