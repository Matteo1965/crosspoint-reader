#include "TextSettingsActivity.h"

#include <GfxRenderer.h>
#include <I18n.h>

#include <algorithm>
#include <cstdio>
#include <cstring>
#include <iterator>
#include <string>
#include <vector>

#include "CrossPointSettings.h"
#include "MappedInputManager.h"
#include "ReaderFontSizes.h"
#include "ReaderLineSpacing.h"
#include "SdCardFontSystem.h"
#include "TextSettingsPreview.h"
#include "components/UITheme.h"
#include "fontIds.h"

namespace fui = freeink::ui;

namespace {
// Tab labels for Font | Size | Layout | Style.
constexpr StrId TAB_NAME_IDS[] = {StrId::STR_FONT, StrId::STR_SIZE, StrId::STR_LAYOUT, StrId::STR_STYLE};

constexpr StrId LAYOUT_ROW_NAME_IDS[] = {
    StrId::STR_LINE_SPACING, StrId::STR_WORD_SPACING, StrId::STR_CHARACTER_SPACING,
    StrId::STR_CHARACTER_SPACING,
    StrId::STR_EXTRA_SPACING, StrId::STR_EXTRA_SPACING, StrId::STR_PARAGRAPH_INDENTATION,
    StrId::STR_ALIGNMENT, StrId::STR_SCREEN_MARGIN, StrId::STR_HYPHENATION};
constexpr StrId STYLE_ROW_NAME_IDS[] = {StrId::STR_FOCUS_READING, StrId::STR_HYPHENATION_NO_PREVIEW,
                                        StrId::STR_EMBEDDED_STYLE_NO_PREVIEW, StrId::STR_TEXT_AA_NO_PREVIEW};

int findCurrentFontIndex(const SdCardFontRegistry* registry, const char* sdFontFamilyName, uint8_t fontFamily) {
  if (sdFontFamilyName[0] != '\0' && registry) {
    const auto& families = registry->getFamilies();
    const auto family = std::find_if(families.begin(), families.end(), [sdFontFamilyName](const auto& candidate) {
      return candidate.name == sdFontFamilyName;
    });
    if (family != families.end()) {
      return CrossPointSettings::BUILTIN_FONT_COUNT + static_cast<int>(family - families.begin());
    }
  }

  return fontFamily < CrossPointSettings::BUILTIN_FONT_COUNT ? fontFamily : 0;
}

constexpr uint8_t WORD_SPACING_VALUES[] = {50, 60, 70, 80, 90, 100};
constexpr uint8_t MARGIN_VALUES[] = {5, 10, 12, 14, 16, 18, 20, 25};

int nearestChoice(const uint8_t value, const uint8_t* values, const size_t count) {
  int best = 0;
  int distance = 256;
  for (size_t i = 0; i < count; ++i) {
    const int difference = std::abs(static_cast<int>(value) - static_cast<int>(values[i]));
    if (difference < distance) {
      distance = difference;
      best = static_cast<int>(i);
    }
  }
  return best;
}
constexpr StrId ALIGNMENT_IDS[] = {StrId::STR_JUSTIFY, StrId::STR_ALIGN_LEFT, StrId::STR_CENTER, StrId::STR_ALIGN_RIGHT,
                                   StrId::STR_BOOK_S_STYLE};
}  // namespace

TextSettingsActivity::TextSettingsActivity(GfxRenderer& renderer, MappedInputManager& mappedInput,
                                           const SdCardFontRegistry* registry, Tab initialTab)
    : UiTabListActivity("TextSettings", renderer, mappedInput), registry_(registry), tab_(initialTab) {}

const char* TextSettingsActivity::tabLabel(const int index) const { return I18N.get(TAB_NAME_IDS[index]); }

void TextSettingsActivity::onEnter() {
  UiTabListActivity::onEnter();

  metrics_ = UITheme::getInstance().getMetrics();
  const Rect safeArea = UITheme::getInstance().getScreenSafeArea(renderer, true, false);
  const int safeBottom = safeArea.y + safeArea.height;
  afterHeader = safeArea.y + metrics_.topPadding + metrics_.headerHeight + metrics_.verticalSpacing;
  const int usableHeight = safeBottom - afterHeader - metrics_.verticalSpacing;
  previewHeight = usableHeight * metrics_.previewHeightPercent / 100;

  fonts_.clear();
  fonts_.reserve(CrossPointSettings::BUILTIN_FONT_COUNT + (registry_ ? registry_->getFamilyCount() : 0));
  fonts_.push_back({I18N.get(StrId::STR_NOTO_SANS), true, static_cast<uint8_t>(CrossPointSettings::NOTOSANS)});
  if (registry_) {
    const auto& families = registry_->getFamilies();
    for (int i = 0; i < static_cast<int>(families.size()); i++) {
      fonts_.push_back({families[i].name, false, static_cast<uint8_t>(CrossPointSettings::BUILTIN_FONT_COUNT + i)});
    }
  }

  rebuildSizeList();

  currentFamilyIndex_ = findCurrentFontIndex(registry_, SETTINGS.sdFontFamilyName, SETTINGS.fontFamily);
  // Per-tab ring positions (0 = tab bar, 1..N = row). The base reset each
  // tab's nav with followOnBuild armed, so each tab's first build shows its
  // remembered selection (Family/Size open on the current item).
  for (auto& n : tabNavs) n.selected = 1;  // default to the first list row
  tabNavs[static_cast<int>(Tab::Family)].selected = currentFamilyIndex_ + 1;
  tabNavs[static_cast<int>(Tab::Size)].selected = currentSizeIndex_ + 1;
  tabNavs[static_cast<int>(tab_)].selected = 0;  // screen opens with the tab bar focused, not a list row

  rebuildRowItems();
}

// Rebuilds rowItems_ (label + actionValue) for the active tab. Structural —
// call only when tab_ or its backing data (fonts_/sizes_) changes, never from
// buildScreen(), which just refreshes rowValues_/rowItems_[].value in place.
void TextSettingsActivity::rebuildRowItems() {
  const int count = listCount();
  rowValues_.assign(count, std::string());
  rowItems_.clear();
  rowItems_.reserve(count);
  for (int i = 0; i < count; i++) {
    fui::ListItem item;
    switch (tab_) {
      case Tab::Family:
        item.label = fonts_[i].name.c_str();
        break;
      case Tab::Size:
        item.label = sizes_[i].name.c_str();
        break;
      case Tab::Layout:
        item.label = (i == static_cast<int>(LayoutRow::OpticalMargin))
                         ? (I18N.getLanguage() == Language::HU ? "Optikai margó" : "Optical margin")
                         : (i == static_cast<int>(LayoutRow::FixedDialogueSpacing))
                               ? (I18N.getLanguage() == Language::HU ? "Fix párbeszédköz"
                                                                    : "Fixed dialogue spacing")
                         : (i == static_cast<int>(LayoutRow::WordSpacing))
                               ? (I18N.getLanguage() == Language::HU ? "Saját Szóköz" : "Custom word spacing")
                         : (i == static_cast<int>(LayoutRow::LetterSpacingCorrection))
                               ? (I18N.getLanguage() == Language::HU ? "Betűköz korrekció" : "Letter spacing correction")
                         : (i == static_cast<int>(LayoutRow::LetterSpacingOptimization))
                               ? (I18N.getLanguage() == Language::HU ? "Betűköz optimalizálás" : "Letter spacing optimization")
                         : (i == static_cast<int>(LayoutRow::ScreenMargin))
                               ? (I18N.getLanguage() == Language::HU ? "Saját Margó" : "Custom margin")
                               : I18N.get(LAYOUT_ROW_NAME_IDS[i]);
        break;
      case Tab::Style:
        item.label = I18N.get(STYLE_ROW_NAME_IDS[i]);
        break;
      default:
        break;
    }
    item.actionValue = static_cast<int16_t>(i);
    rowItems_.push_back(item);
  }
}

// The selectable sizes belong to the active family, so this runs on entry and
// again after every family change. A family change goes through ensureLoaded(),
// which snaps SETTINGS.fontPointSize into the new family's set — but entry does
// not, so the highlight is resolved by snapping rather than by exact match.
void TextSettingsActivity::rebuildSizeList() {
  const std::vector<uint8_t> points = readerFontPointSizes(registry_, SETTINGS.sdFontFamilyName);

  // The stored size can still sit outside this family's set — e.g. the family
  // was deleted while selected, or the card was swapped. Highlight the size the
  // reader actually renders, which getReaderFontId() resolves the same way.
  const uint8_t selectedPt = snapToNearestPointSize(points, SETTINGS.fontPointSize);

  sizes_.clear();
  sizes_.reserve(points.size());
  currentSizeIndex_ = 0;
  for (const uint8_t pt : points) {
    // "pt" is deliberately not translated: it is the typographic unit symbol,
    // written the same way in every language CrossPoint ships.
    char label[12];
    snprintf(label, sizeof(label), "%u pt", pt);
    if (pt == selectedPt) currentSizeIndex_ = static_cast<int>(sizes_.size());
    sizes_.push_back({label, pt});
  }
}

void TextSettingsActivity::onTabAction(const int index) {
  if (optionPopup_.isActive()) return;
  if (tab_ != static_cast<Tab>(index)) {
    tab_ = static_cast<Tab>(index);
    rebuildRowItems();
    auto& n = activeNav();
    n.selected = 0;          // tab taps land with the tab bar focused (legacy tap behavior)
    n.followOnBuild = true;  // pull the new tab's viewport to its remembered selection
    requestUpdate();
  }
  // The switched-to tab repaints as the selected pill; a flash overlay on top
  // of it just repaints the pill in the focused style.
  app.clearTapFlash();
}

void TextSettingsActivity::activateIndex(const int index) {
  if (optionPopup_.isActive()) return;
  // Most rows repaint a different surface (popup, preview, new value);
  // a lingering tap flash would gray an unrelated element.
  app.clearTapFlash();
  activateRow(index);
}

bool TextSettingsActivity::handleCustomInput() {
  return optionPopup_.handleInput(mappedInput, [this] { requestUpdate(); });
}

bool TextSettingsActivity::handleButtons() {
  if (mappedInput.wasReleased(MappedInputManager::Button::Back)) {
    finish();
    return true;
  }

  if (mappedInput.wasReleased(MappedInputManager::Button::Confirm)) {
    if (ringPos() == 0) {
      switchTab();
    } else {
      activateRow(ringPos() - 1);
    }
    return true;
  }

  return false;
}

void TextSettingsActivity::buildScreen(UiScreen& screen) {
  const Rect safeArea = UITheme::getInstance().getScreenSafeArea(renderer, true, false);
  const int tabTop = afterHeader + previewHeight;
  const int rightInset = renderer.getScreenWidth() - (safeArea.x + safeArea.width);
  const int bottomInset = renderer.getScreenHeight() - (safeArea.y + safeArea.height);
  screen.setContentMarginFromScreen(fui::Insets{static_cast<int16_t>(tabTop), static_cast<int16_t>(rightInset),
                                                static_cast<int16_t>(bottomInset), static_cast<int16_t>(safeArea.x)});

  buildTabBar(screen);

  // rowItems_ (label/actionValue) was built by rebuildRowItems() when the tab
  // was last switched; only the live value text needs refreshing here, by
  // assigning into the existing rowValues_ strings (no vector growth) rather
  // than building a new items/values vector on every render.
  const int count = listCount();
  for (int i = 0; i < count; i++) {
    switch (tab_) {
      case Tab::Family:
        rowValues_[i] = (i == currentFamilyIndex_) ? tr(STR_SELECTED) : "";
        break;
      case Tab::Size:
        rowValues_[i] = (i == currentSizeIndex_) ? tr(STR_SELECTED) : "";
        break;
      case Tab::Layout:
        rowValues_[i] = layoutValueText(i);
        break;
      case Tab::Style:
        if (i == static_cast<int>(StyleRow::Hyphenation)) {
          if (!SETTINGS.hyphenationEnabled) {
            rowValues_[i] = tr(STR_STATE_OFF);
          } else {
            rowValues_[i] = SETTINGS.hungarianHyphenationExtended
                                ? (I18N.getLanguage() == Language::HU ? "Kiterjesztett magyar" : "Extended Hungarian")
                                : (I18N.getLanguage() == Language::HU ? "Alap" : "Basic");
          }
        }
        break;
      default:
        break;
    }
    rowItems_[i].toggle = false;
    if (tab_ == Tab::Style && i != static_cast<int>(StyleRow::Hyphenation)) {
      rowValues_[i] = styleRowChecked(i) ? tr(STR_STATE_ON) : tr(STR_STATE_OFF);
    } else if (tab_ == Tab::Layout && i == static_cast<int>(LayoutRow::FixedDialogueSpacing)) {
      rowValues_[i] = SETTINGS.fixedDialogueSpacing ? tr(STR_STATE_ON) : tr(STR_STATE_OFF);
    } else if (tab_ == Tab::Layout && i == static_cast<int>(LayoutRow::OpticalMargin)) {
      rowValues_[i] = SETTINGS.opticalMargin ? tr(STR_STATE_ON) : tr(STR_STATE_OFF);
    }
    rowItems_[i].value = rowValues_[i].empty() ? nullptr : rowValues_[i].c_str();
  }

  fui::ListProps props;
  props.items = rowItems_.data();
  props.count = static_cast<uint16_t>(rowItems_.size());
  props.action = ACTION_ROW;
  props.inputMask = fui::InputTouch;  // physical buttons stay in loop()
  props.valueInset = 8;               // air between the value and the row edge
  // Titles match the value's font size (smallText) so both sides of a row
  // read as one unit; labels that still don't fit wrap onto a second line.
  // maxLines=2 also marks the style explicitly set (see SettingsActivity).
#if FREEINK_DEVICE_PICCO
  props.labelText = SETTINGS.uiSize == CrossPointSettings::UI_SIZE_NORMAL ? screen.theme().bodyText
                                                                          : screen.theme().smallText;
#else
  props.labelText = screen.theme().smallText;
#endif
  props.labelText.maxLines = 2;
#if FREEINK_DEVICE_PICCO
  if (tab_ == Tab::Layout || tab_ == Tab::Style) {
    props.rowHeight = 48;
  }
#endif
  syncTabListViewport(screen, props);
  screen.list(props);
}

const char* TextSettingsActivity::confirmLabelText() const {
  if (ringPos() == 0) {
    // Confirm on the tab bar advances to the next tab.
    return I18N.get(TAB_NAME_IDS[(static_cast<int>(tab_) + 1) % static_cast<int>(Tab::Count)]);
  }
  switch (tab_) {
    case Tab::Layout:
      return (ringPos() - 1 == static_cast<int>(LayoutRow::FixedDialogueSpacing) ||
              ringPos() - 1 == static_cast<int>(LayoutRow::OpticalMargin))
                 ? tr(STR_TOGGLE)
                 : tr(STR_SELECT);
    case Tab::Style:
      return tr(STR_TOGGLE);
    default:
      return tr(STR_SELECT);
  }
}

void TextSettingsActivity::drawChrome() {
  GUI.drawHeader(renderer, UITheme::getInstance().getHeaderRect(renderer, true, false), tr(STR_TEXT_SETTINGS));

  const char* familyName = (currentFamilyIndex_ >= 0 && currentFamilyIndex_ < static_cast<int>(fonts_.size()))
                               ? fonts_[currentFamilyIndex_].name.c_str()
                               : "";
  const char* sizeName = (currentSizeIndex_ >= 0 && currentSizeIndex_ < static_cast<int>(sizes_.size()))
                             ? sizes_[currentSizeIndex_].name.c_str()
                             : "";
  char labelBuf[128];
  snprintf(labelBuf, sizeof(labelBuf), "%s \"%s, %s\"", tr(STR_PREVIEW), familyName, sizeName);
  const Rect safeArea = UITheme::getInstance().getScreenSafeArea(renderer, true, false);
  const Rect previewBounds{safeArea.x, afterHeader, safeArea.width, previewHeight};
  const auto [savedX, savedY, savedWidth, savedHeight] = renderer.getClipRect();
  const int clipLeft = std::max(previewBounds.x, savedX);
  const int clipTop = std::max(previewBounds.y, savedY);
  const int clipRight = std::min(previewBounds.x + previewBounds.width, savedX + savedWidth);
  const int clipBottom = std::min(previewBounds.y + previewBounds.height, savedY + savedHeight);
  renderer.setClipRect(clipLeft, clipTop, std::max(0, clipRight - clipLeft), std::max(0, clipBottom - clipTop));
  textsettings::renderPreview(renderer, previewLayout_, metrics_.previewPadding, metrics_.verticalSpacing,
                              previewBounds, labelBuf);
  renderer.setClipRect(savedX, savedY, savedWidth, savedHeight);
}

void TextSettingsActivity::drawFooter() {
  const auto labels = mappedInput.mapLabels(tr(STR_BACK), confirmLabelText(), tr(STR_DIR_UP), tr(STR_DIR_DOWN));
  GUI.drawButtonHints(renderer, labels.btn1, labels.btn2, labels.btn3, labels.btn4);
}

void TextSettingsActivity::render(RenderLock&& lock) {
  if (optionPopup_.processRender(renderer, mappedInput)) return;  // picker draws over everything
  UiListActivity::render(std::move(lock));
}

// Font switching runs on the main task from loop(), which deliberately holds no
// RenderLock. ensureLoaded() deletes the resident SdCardFont before loading the
// next one, and the render task walks that same object inside the preview's
// prewarmCache() — so without this lock a font switch can free the mini glyph
// arrays out from under prewarmStyle() (crash: null s.miniGlyphs mid-read/sort).
void TextSettingsActivity::applyFamily(int listIndex) {
  RenderLock lock;
  const auto& font = fonts_[listIndex];
  if (font.isBuiltin) {
    SETTINGS.fontFamily = font.settingIndex;
    SETTINGS.sdFontFamilyName[0] = '\0';
    sdFontSystem.ensureLoaded(renderer);  // unloads the previously resident SD font
    currentFamilyIndex_ = listIndex;
  } else if (registry_) {
    const int sdIdx = font.settingIndex - CrossPointSettings::BUILTIN_FONT_COUNT;
    const auto& families = registry_->getFamilies();
    if (sdIdx < static_cast<int>(families.size())) {
      strncpy(SETTINGS.sdFontFamilyName, families[sdIdx].name.c_str(), sizeof(SETTINGS.sdFontFamilyName) - 1);
      SETTINGS.sdFontFamilyName[sizeof(SETTINGS.sdFontFamilyName) - 1] = '\0';
      sdFontSystem.ensureLoaded(renderer);
      currentFamilyIndex_ = listIndex;
    }
  }

  if (currentFamilyIndex_ != listIndex) return;  // switch failed — keep the old size list

  // The new family ships its own set of point sizes, and ensureLoaded() may have
  // snapped the selection into it, so the Size tab's list and its nav position
  // both have to be rebuilt.
  rebuildSizeList();
  tabNavs[static_cast<int>(Tab::Size)].selected = currentSizeIndex_ + 1;
}

void TextSettingsActivity::activateRow(int row) {
  switch (tab_) {
    case Tab::Family:
      if (row != currentFamilyIndex_) {
        applyFamily(row);
        // Persist immediately (like SettingsActivity's per-change saves): the
        // parent's result callback only runs on a normal finish(), so relying
        // on it loses the change when this screen is left via the home
        // gesture/key or a sleep. Saved here, not inside applyFamily, so the
        // SD write happens outside its RenderLock.
        if (currentFamilyIndex_ == row) {
          SETTINGS.saveToFile();
        }
        requestUpdate();
      }
      break;
    case Tab::Size:
      if (row != currentSizeIndex_) {
        applySize(row);
        SETTINGS.saveToFile();
        requestUpdate();
      }
      break;
    case Tab::Layout:
      confirmLayoutRow(row);
      break;
    case Tab::Style:
      confirmStyleRow(row);
      break;
    default:
      break;
  }
}

// Same RenderLock rationale as applyFamily(): a size change reloads the SD font
// file, which frees and replaces the SdCardFont the render task may be reading.
void TextSettingsActivity::applySize(int listIndex) {
  RenderLock lock;

  currentSizeIndex_ = listIndex;
  SETTINGS.fontPointSize = sizes_[listIndex].pointSize;
  sdFontSystem.ensureLoaded(renderer);
}

void TextSettingsActivity::confirmLayoutRow(int row) {
  switch (static_cast<LayoutRow>(row)) {
    case LayoutRow::OpticalMargin:
      SETTINGS.opticalMargin = SETTINGS.opticalMargin ? 0 : 1;
      SETTINGS.saveToFile();
      requestUpdate();
      break;
    case LayoutRow::ParaSpacing: {
      const std::vector<std::string> options = {tr(STR_STATE_OFF), "0%", "25%", "50%", "75%", "100%"};
      const int selected = !SETTINGS.extraParagraphSpacing
                               ? 0
                               : std::clamp<int>(SETTINGS.extraParagraphSpacingPercent / 25 + 1, 1, 5);
      optionPopup_.show(StrId::STR_EXTRA_SPACING, options, selected, [](int idx) {
        if (idx < 0 || idx > 5) return;
        SETTINGS.extraParagraphSpacing = idx != 0;
        SETTINGS.extraParagraphSpacingPercent = idx <= 1 ? 0 : static_cast<uint8_t>((idx - 1) * 25);
        SETTINGS.saveToFile();
      });
      requestUpdate();
      break;
    }
    case LayoutRow::FixedDialogueSpacing:
      SETTINGS.fixedDialogueSpacing = SETTINGS.fixedDialogueSpacing ? 0 : 1;
      SETTINGS.saveToFile();
      requestUpdate();
      break;
    case LayoutRow::ParaIndentation: {
      std::vector<std::string> options;
      options.reserve(6);
      options.push_back(tr(STR_STATE_OFF));
      for (int spaces = 1; spaces <= 5; ++spaces) options.push_back(std::to_string(spaces));
      optionPopup_.show(StrId::STR_PARAGRAPH_INDENTATION, options, SETTINGS.paragraphIndentSpaces, [](int idx) {
        SETTINGS.paragraphIndentSpaces = static_cast<uint8_t>(idx);
        SETTINGS.saveToFile();
      });
      requestUpdate();
      break;
    }
    case LayoutRow::LineSpacing:
      optionPopup_.show(StrId::STR_LINE_SPACING, LINE_SPACING_IDS, static_cast<int>(std::size(LINE_SPACING_IDS)),
                        SETTINGS.lineSpacing, [](int idx) {
                          SETTINGS.lineSpacing = static_cast<uint8_t>(idx);
                          SETTINGS.saveToFile();
                        });
      requestUpdate();
      break;
    case LayoutRow::Alignment:
      optionPopup_.show(StrId::STR_ALIGNMENT, ALIGNMENT_IDS, static_cast<int>(std::size(ALIGNMENT_IDS)),
                        SETTINGS.paragraphAlignment, [](int idx) {
                          SETTINGS.paragraphAlignment = static_cast<uint8_t>(idx);
                          SETTINGS.saveToFile();
                        });
      requestUpdate();
      break;
    case LayoutRow::WordSpacing: {
      std::vector<std::string> options;
      options.reserve(std::size(WORD_SPACING_VALUES));
      for (const uint8_t v : WORD_SPACING_VALUES) options.push_back(std::to_string(v) + "%");
      const int selected = nearestChoice(SETTINGS.wordSpacing, WORD_SPACING_VALUES, std::size(WORD_SPACING_VALUES));
      optionPopup_.show(StrId::STR_WORD_SPACING, options, selected, [](int idx) {
        if (idx >= 0 && idx < static_cast<int>(std::size(WORD_SPACING_VALUES))) {
          SETTINGS.wordSpacing = WORD_SPACING_VALUES[idx];
          SETTINGS.saveToFile();
        }
      });
      requestUpdate();
      break;
    }
    case LayoutRow::LetterSpacingCorrection: {
      const bool hu = I18N.getLanguage() == Language::HU;
      const char* options[] = {hu ? "KI" : "OFF", hu ? "Gyenge" : "Weak",
                               hu ? "Közepes" : "Medium", hu ? "Erős" : "Strong"};
      int cur = SETTINGS.letterSpacingLimitPercent == 10 ? 1 :
                SETTINGS.letterSpacingLimitPercent == 40 ? 2 :
                SETTINGS.letterSpacingLimitPercent == 70 ? 3 : 0;
      optionPopup_.show(hu ? "Betűköz korrekció" : "Letter spacing correction",
                        options, 4, cur, [](int idx) {
        static constexpr uint16_t values[] = {0, 10, 40, 70};
        if (idx >= 0 && idx < 4) {
          SETTINGS.letterSpacingLimitPercent = values[idx];
          if (idx == 0) SETTINGS.letterSpacingOptimization = 0;
          SETTINGS.saveToFile();
        }
      });
      requestUpdate();
      break;
    }
    case LayoutRow::LetterSpacingOptimization:
      if (SETTINGS.letterSpacingLimitPercent != 0) {
        SETTINGS.letterSpacingOptimization = SETTINGS.letterSpacingOptimization ? 0 : 4;
        SETTINGS.saveToFile();
      }
      requestUpdate();
      break;
    case LayoutRow::ScreenMargin: {
      std::vector<std::string> options;
      options.reserve(std::size(MARGIN_VALUES));
      for (const uint8_t v : MARGIN_VALUES) options.push_back(std::to_string(v));
      const int selected = nearestChoice(SETTINGS.screenMargin, MARGIN_VALUES, std::size(MARGIN_VALUES));
      optionPopup_.show(StrId::STR_SCREEN_MARGIN, options, selected, [](int idx) {
        if (idx >= 0 && idx < static_cast<int>(std::size(MARGIN_VALUES))) {
          SETTINGS.screenMargin = MARGIN_VALUES[idx];
          SETTINGS.saveToFile();
        }
      });
      requestUpdate();
      break;
    }

    default:
      break;
  }
}

std::string TextSettingsActivity::layoutValueText(int row) const {
  switch (static_cast<LayoutRow>(row)) {
    case LayoutRow::OpticalMargin:
      return SETTINGS.opticalMargin ? tr(STR_STATE_ON) : tr(STR_STATE_OFF);
    case LayoutRow::LineSpacing: {
      const uint8_t v = SETTINGS.lineSpacing;
      return I18N.get(LINE_SPACING_IDS[v < std::size(LINE_SPACING_IDS) ? v : CrossPointSettings::LINE_SPACING_120]);
    }
    case LayoutRow::ParaSpacing:
      return !SETTINGS.extraParagraphSpacing ? tr(STR_STATE_OFF)
                                            : std::to_string(SETTINGS.extraParagraphSpacingPercent) + "%";
    case LayoutRow::FixedDialogueSpacing:
      return SETTINGS.fixedDialogueSpacing ? tr(STR_STATE_ON) : tr(STR_STATE_OFF);
    case LayoutRow::ParaIndentation: {
      const int spaces = std::clamp<int>(SETTINGS.paragraphIndentSpaces, 0, 5);
      return spaces == 0 ? tr(STR_STATE_OFF) : std::to_string(spaces);
    }
    case LayoutRow::Alignment: {
      const uint8_t v = SETTINGS.paragraphAlignment;
      return v < std::size(ALIGNMENT_IDS) ? I18N.get(ALIGNMENT_IDS[v]) : I18N.get(StrId::STR_JUSTIFY);
    }
    case LayoutRow::WordSpacing:
      return std::to_string(SETTINGS.wordSpacing) + "%";
    case LayoutRow::LetterSpacingCorrection:
      return SETTINGS.letterSpacingLimitPercent == 10 ? (I18N.getLanguage() == Language::HU ? "Gyenge" : "Weak") :
             SETTINGS.letterSpacingLimitPercent == 40 ? (I18N.getLanguage() == Language::HU ? "Közepes" : "Medium") :
             SETTINGS.letterSpacingLimitPercent == 70 ? (I18N.getLanguage() == Language::HU ? "Erős" : "Strong") :
                                                        (I18N.getLanguage() == Language::HU ? "KI" : "OFF");
    case LayoutRow::LetterSpacingOptimization:
      return SETTINGS.letterSpacingOptimization ? tr(STR_STATE_ON) : tr(STR_STATE_OFF);
    case LayoutRow::ScreenMargin:
      return std::to_string(SETTINGS.screenMargin);

    default:
      return "";
  }
}

void TextSettingsActivity::confirmStyleRow(int row) {
  switch (static_cast<StyleRow>(row)) {
    case StyleRow::FocusReading:
      SETTINGS.focusReadingEnabled = !SETTINGS.focusReadingEnabled;
      break;
    case StyleRow::Hyphenation: {
      std::vector<std::string> options;
      options.reserve(3);
      options.push_back(tr(STR_STATE_OFF));
      options.push_back(I18N.getLanguage() == Language::HU ? "Alap" : "Basic");
      options.push_back(I18N.getLanguage() == Language::HU ? "Kiterjesztett magyar" : "Extended Hungarian");
      const int selected = !SETTINGS.hyphenationEnabled ? 0 : (SETTINGS.hungarianHyphenationExtended ? 2 : 1);
      optionPopup_.show(StrId::STR_HYPHENATION, options, selected, [](int idx) {
        if (idx < 0 || idx > 2) return;
        SETTINGS.hyphenationEnabled = idx == 0 ? 0 : 1;
        SETTINGS.hungarianHyphenationExtended = idx == 2 ? 1 : 0;
        SETTINGS.saveToFile();
      });
      requestUpdate();
      return;
    }
    case StyleRow::EmbeddedStyle:
      SETTINGS.embeddedStyle = !SETTINGS.embeddedStyle;
      break;
    case StyleRow::AntiAliasing:
      SETTINGS.textAntiAliasing = !SETTINGS.textAntiAliasing;
      break;

    default:
      return;
  }
  SETTINGS.saveToFile();
  requestUpdate();
}

bool TextSettingsActivity::styleRowChecked(int row) const {
  switch (static_cast<StyleRow>(row)) {
    case StyleRow::FocusReading:
      return SETTINGS.focusReadingEnabled;
    case StyleRow::Hyphenation:
      return SETTINGS.hyphenationEnabled;
    case StyleRow::EmbeddedStyle:
      return SETTINGS.embeddedStyle;
    case StyleRow::AntiAliasing:
      return SETTINGS.textAntiAliasing;

    default:
      return false;
  }
}

void TextSettingsActivity::switchTab(const int direction) {
  const bool onTabBar = ringPos() == 0;
  constexpr int count = static_cast<int>(Tab::Count);
  tab_ = static_cast<Tab>((static_cast<int>(tab_) + direction + count) % count);
  rebuildRowItems();
  auto& n = activeNav();
  if (onTabBar) n.selected = 0;
  n.followOnBuild = true;  // pull the new tab's viewport to its remembered selection
  requestUpdate();
}

int TextSettingsActivity::listCount() const {
  switch (tab_) {
    case Tab::Family:
      return static_cast<int>(fonts_.size());
    case Tab::Size:
      return static_cast<int>(sizes_.size());
    case Tab::Layout:
      return static_cast<int>(LayoutRow::Count);
    case Tab::Style:
      return static_cast<int>(StyleRow::Count);

    default:
      return 0;
  }
}
