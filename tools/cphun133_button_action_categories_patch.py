from pathlib import Path


def replace_once(path, old, new):
    p = Path(path)
    text = p.read_text(encoding="utf-8")
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"CPHUN-133: {path}: expected one match, found {count}: {old[:160]!r}")
    p.write_text(text.replace(old, new, 1), encoding="utf-8")


# -----------------------------------------------------------------------------
# ReaderAction: append only, preserving persisted numeric values 0..33.
# -----------------------------------------------------------------------------
replace_once(
    "src/ReaderAction.h",
    '''  GoHome = 32,
  OpenSettings = 33,

  COUNT''',
    '''  GoHome = 32,
  OpenSettings = 33,

  // CPHUN-133: direct reader controls. Append-only: values are persisted.
  LetterSpacingCorrectionUp = 34,
  LetterSpacingCorrectionDown = 35,
  LetterSpacingOptimizationUp = 36,
  LetterSpacingOptimizationDown = 37,
  ExtraParagraphSpacingUp = 38,
  ExtraParagraphSpacingDown = 39,
  MinimumSpaceUp = 40,
  MinimumSpaceDown = 41,
  OpenHighlight = 42,
  OpenManualDictionarySearch = 43,

  // Fast A/B test actions kept in their own picker category.
  TestLetterSpacingCorrectionMinMax = 44,
  TestLetterSpacingOptimizationOff100 = 45,
  TestLineSpacingMinMax = 46,
  TestExtraParagraphSpacingOffMax = 47,
  TestMinimumSpaceMinMax = 48,

  COUNT''',
)

# Menu-like actions should be classified as menu actions; direct/test actions remain Immediate.
replace_once(
    "src/ReaderAction.h",
    '''    case ReaderAction::OpenDictionary:
    case ReaderAction::OpenBookmarks:''',
    '''    case ReaderAction::OpenDictionary:
    case ReaderAction::OpenHighlight:
    case ReaderAction::OpenManualDictionarySearch:
    case ReaderAction::OpenBookmarks:''',
)

# -----------------------------------------------------------------------------
# Button picker: two-stage Category -> Action, every leaf remains <= 16 entries.
# -----------------------------------------------------------------------------
replace_once(
    "src/activities/settings/ButtonFunctionsActivity.h",
    '''  void rebuildRows();
  void openActionPicker(int row);
''',
    '''  void rebuildRows();
  void openCategoryPicker(int row);
  void openActionPicker(int row, const ReaderAction* actions, size_t actionCount, const char* categoryTitle);
''',
)

cpp = Path("src/activities/settings/ButtonFunctionsActivity.cpp")
text = cpp.read_text(encoding="utf-8")
start = text.index("constexpr ReaderAction ACTIONS[] = {")
end = text.index("constexpr int kMappingCount = 12;", start)
new_arrays = r'''constexpr ReaderAction READING_ACTIONS[] = {
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

'''
text = text[:start] + new_arrays + text[end:]
cpp.write_text(text, encoding="utf-8")

# Add labels for all new actions, using the requested Hungarian wording.
replace_once(
    "src/activities/settings/ButtonFunctionsActivity.cpp",
    '''    case ReaderAction::OpenSettings: return hu ? "Beállítások" : "Settings";
    default: return hu ? "Nincs" : "None";''',
    '''    case ReaderAction::OpenSettings: return hu ? "Beállítások" : "Settings";
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
    default: return hu ? "Nincs" : "None";''',
)

# Replace single huge action popup with category -> leaf popup.
replace_once(
    "src/activities/settings/ButtonFunctionsActivity.cpp",
    '''void ButtonFunctionsActivity::activateIndex(const int index) {
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
''',
    '''void ButtonFunctionsActivity::activateIndex(const int index) {
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
''',
)

# -----------------------------------------------------------------------------
# Reader behavior for new direct and test actions.
# This patch runs after CPHUN-132r4, so highlight/manual-search entry points exist.
# -----------------------------------------------------------------------------
replace_once(
    "src/activities/reader/EpubReaderActivity.cpp",
    '''    if (configured == ReaderAction::OpenDictionary) { openDictionaryWordSelect(); return true; }
    if (configured == ReaderAction::OpenSettings) { cphun36OpenSettings(); return true; }''',
    '''    if (configured == ReaderAction::OpenDictionary) { openDictionaryWordSelect(); return true; }
    if (configured == ReaderAction::OpenHighlight) { openDictionaryWordSelect(WordSelectionMode::Highlight); return true; }
    if (configured == ReaderAction::OpenManualDictionarySearch) {
      onReaderMenuConfirm(EpubReaderMenuActivity::MenuAction::MANUAL_DICTIONARY_SEARCH);
      return true;
    }
    if (configured == ReaderAction::OpenSettings) { cphun36OpenSettings(); return true; }''',
)

# Fix the old four-state shortcut and use the real six-state line-spacing order.
replace_once(
    "src/activities/reader/EpubReaderActivity.cpp",
    '''    if (configured == ReaderAction::LineSpacingNext || configured == ReaderAction::LineSpacingPrevious) {
      constexpr uint8_t kLineSpacingCount = 4;
      const uint8_t current = SETTINGS.lineSpacing < kLineSpacingCount ? SETTINGS.lineSpacing : 1;
      SETTINGS.lineSpacing = configured == ReaderAction::LineSpacingNext
                                 ? static_cast<uint8_t>((current + 1) % kLineSpacingCount)
                                 : static_cast<uint8_t>((current + kLineSpacingCount - 1) % kLineSpacingCount);
      SETTINGS.saveToFile();
      cphun36RebuildReader();
      return true;
    }''',
    '''    if (configured == ReaderAction::LineSpacingNext || configured == ReaderAction::LineSpacingPrevious) {
      constexpr uint8_t kLineSpacingValues[] = {
          CrossPointSettings::TIGHT, CrossPointSettings::NORMAL, CrossPointSettings::NORMAL_PLUS,
          CrossPointSettings::WIDE, CrossPointSettings::WIDE_PLUS, CrossPointSettings::EXTRA_WIDE};
      int idx = 1;
      for (int i = 0; i < static_cast<int>(std::size(kLineSpacingValues)); ++i) {
        if (kLineSpacingValues[i] == SETTINGS.lineSpacing) { idx = i; break; }
      }
      if (configured == ReaderAction::LineSpacingNext && idx + 1 < static_cast<int>(std::size(kLineSpacingValues))) ++idx;
      if (configured == ReaderAction::LineSpacingPrevious && idx > 0) --idx;
      SETTINGS.lineSpacing = kLineSpacingValues[idx];
      SETTINGS.saveToFile();
      cphun36RebuildReader();
      return true;
    }''',
)

# Insert the CPHUN-133 numeric controls before the bookmark action block.
replace_once(
    "src/activities/reader/EpubReaderActivity.cpp",
    '''    if (configured == ReaderAction::ToggleBookmark) { addBookmark(); return true; }''',
    '''    if (configured == ReaderAction::LetterSpacingCorrectionUp ||
        configured == ReaderAction::LetterSpacingCorrectionDown) {
      // CPHUN-113/128 UI order: KI,10,20,...70% maps to 0,360,340,...240.
      constexpr uint16_t values[] = {0, 360, 340, 320, 300, 280, 260, 240};
      int idx = 0;
      for (int i = 0; i < static_cast<int>(std::size(values)); ++i) {
        if (values[i] == SETTINGS.letterSpacingLimitPercent) { idx = i; break; }
      }
      if (configured == ReaderAction::LetterSpacingCorrectionUp && idx + 1 < static_cast<int>(std::size(values))) ++idx;
      if (configured == ReaderAction::LetterSpacingCorrectionDown && idx > 0) --idx;
      SETTINGS.letterSpacingLimitPercent = values[idx];
      SETTINGS.saveToFile(); cphun36RebuildReader(); return true;
    }
    if (configured == ReaderAction::LetterSpacingOptimizationUp ||
        configured == ReaderAction::LetterSpacingOptimizationDown) {
      int value = std::clamp<int>(SETTINGS.letterSpacingOptimization, 0, 4);
      if (configured == ReaderAction::LetterSpacingOptimizationUp && value < 4) ++value;
      if (configured == ReaderAction::LetterSpacingOptimizationDown && value > 0) --value;
      SETTINGS.letterSpacingOptimization = static_cast<uint8_t>(value);
      SETTINGS.saveToFile(); cphun36RebuildReader(); return true;
    }
    if (configured == ReaderAction::ExtraParagraphSpacingUp ||
        configured == ReaderAction::ExtraParagraphSpacingDown) {
      // Six UI states: KI, 0, 25, 50, 75, 100%.
      int idx = !SETTINGS.extraParagraphSpacingEnabled
                    ? 0
                    : (SETTINGS.extraParagraphSpacing == 0
                           ? 1
                           : std::clamp<int>(SETTINGS.extraParagraphSpacing / 25 + 1, 2, 5));
      if (configured == ReaderAction::ExtraParagraphSpacingUp && idx < 5) ++idx;
      if (configured == ReaderAction::ExtraParagraphSpacingDown && idx > 0) --idx;
      SETTINGS.extraParagraphSpacingEnabled = idx == 0 ? 0 : 1;
      SETTINGS.extraParagraphSpacing = idx <= 1 ? 0 : static_cast<uint8_t>((idx - 1) * 25);
      SETTINGS.saveToFile(); cphun36RebuildReader(); return true;
    }
    if (configured == ReaderAction::MinimumSpaceUp || configured == ReaderAction::MinimumSpaceDown) {
      int value = std::clamp<int>(SETTINGS.minimumSpacePercent, 50, 100);
      value = ((value - 50) / 10) * 10 + 50;
      if (configured == ReaderAction::MinimumSpaceUp && value < 100) value += 10;
      if (configured == ReaderAction::MinimumSpaceDown && value > 50) value -= 10;
      SETTINGS.minimumSpacePercent = static_cast<uint8_t>(value);
      SETTINGS.saveToFile(); cphun36RebuildReader(); return true;
    }
    if (configured == ReaderAction::TestLetterSpacingCorrectionMinMax) {
      // 10% <-> 70%; any non-minimum state returns to minimum for deterministic A/B tests.
      SETTINGS.letterSpacingLimitPercent = SETTINGS.letterSpacingLimitPercent == 360 ? 240 : 360;
      SETTINGS.saveToFile(); cphun36RebuildReader(); return true;
    }
    if (configured == ReaderAction::TestLetterSpacingOptimizationOff100) {
      SETTINGS.letterSpacingOptimization = SETTINGS.letterSpacingOptimization == 0 ? 4 : 0;
      SETTINGS.saveToFile(); cphun36RebuildReader(); return true;
    }
    if (configured == ReaderAction::TestLineSpacingMinMax) {
      SETTINGS.lineSpacing = SETTINGS.lineSpacing == CrossPointSettings::TIGHT
                                 ? CrossPointSettings::EXTRA_WIDE
                                 : CrossPointSettings::TIGHT;
      SETTINGS.saveToFile(); cphun36RebuildReader(); return true;
    }
    if (configured == ReaderAction::TestExtraParagraphSpacingOffMax) {
      if (!SETTINGS.extraParagraphSpacingEnabled) {
        SETTINGS.extraParagraphSpacingEnabled = 1;
        SETTINGS.extraParagraphSpacing = 100;
      } else {
        SETTINGS.extraParagraphSpacingEnabled = 0;
      }
      SETTINGS.saveToFile(); cphun36RebuildReader(); return true;
    }
    if (configured == ReaderAction::TestMinimumSpaceMinMax) {
      SETTINGS.minimumSpacePercent = SETTINGS.minimumSpacePercent == 50 ? 100 : 50;
      SETTINGS.saveToFile(); cphun36RebuildReader(); return true;
    }

    if (configured == ReaderAction::ToggleBookmark) { addBookmark(); return true; }''',
)

print("CPHUN-133 categorized button actions patch applied")
