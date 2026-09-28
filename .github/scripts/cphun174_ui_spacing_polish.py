#!/usr/bin/env python3
from pathlib import Path

def replace_once(path, old, new):
    p = Path(path)
    s = p.read_text(encoding="utf-8")
    if old not in s:
        raise SystemExit(f"CPHUN-174 anchor missing in {path}: {old[:100]!r}")
    if s.count(old) != 1:
        raise SystemExit(f"CPHUN-174 anchor not unique in {path}: {old[:100]!r}")
    p.write_text(s.replace(old, new, 1), encoding="utf-8")

# FreeInkUI: exact per-row trailing value x correction.
sdk_list = "freeink-sdk/libs/ui/FreeInkUI/include/components/lists/list.h"
replace_once(
    sdk_list,
    """  const char *sectionHeading = nullptr;
};
""",
    """  const char *sectionHeading = nullptr;
  // Optional optical x correction for the trailing value (positive = outward
  // in LTR, mirrored in RTL). Kept per-item so short state labels can be
  // aligned without shifting every value in the list.
  int16_t valueOffsetX = 0;
};
"""
)
replace_once(
    sdk_list,
    """      const int16_t valueX = props.rtl
          ? static_cast<int16_t>(band.x + props.valueInset)
          : static_cast<int16_t>(band.x + availW - valueW - props.valueInset);
      Rect valueRect{valueX, band.y, valueW, band.height};
""",
    """      int16_t valueX = props.rtl
          ? static_cast<int16_t>(band.x + props.valueInset)
          : static_cast<int16_t>(band.x + availW - valueW - props.valueInset);
      valueX = static_cast<int16_t>(valueX + (props.rtl ? -item.valueOffsetX : item.valueOffsetX));
      Rect valueRect{valueX, band.y, valueW, band.height};
"""
)

# Shared tab screen hooks: per-screen RoundedRaff pill inset and post-tab spacing.
replace_once(
    "src/activities/UiTabListActivity.h",
    """  virtual int tabSideMarginPx() const { return 0; }
  virtual int tabGapPx() const { return 0; }
""",
    """  virtual int tabSideMarginPx() const { return 0; }
  virtual int tabGapPx() const { return 0; }
  virtual int tabHorizontalInsetPx() const { return -1; }
  virtual int tabBottomSpacingPx() const { return -1; }
"""
)
replace_once(
    "src/activities/UiTabListActivity.cpp",
    """  if (metrics.tabPillFullSlot) {
    tabProps.text = screen.theme().bodyText;
    tabProps.tabInset = fui::Insets{4, 4, 7, 4};
    tabProps.contentInset = fui::Insets{2, 0, 2, 0};
""",
    """  if (metrics.tabPillFullSlot) {
    tabProps.text = screen.theme().bodyText;
    const int customHorizontalInset = tabHorizontalInsetPx();
    const int16_t horizontalInset =
        static_cast<int16_t>(customHorizontalInset >= 0 ? customHorizontalInset : 4);
    tabProps.tabInset = fui::Insets{4, horizontalInset, 7, horizontalInset};
    tabProps.contentInset = fui::Insets{2, 0, 2, 0};
"""
)
replace_once(
    "src/activities/UiTabListActivity.cpp",
    """  screen.spacer(static_cast<int16_t>(metrics.verticalSpacing));
}
""",
    """  const int customBottomSpacing = tabBottomSpacingPx();
  screen.spacer(static_cast<int16_t>(customBottomSpacing >= 0 ? customBottomSpacing : metrics.verticalSpacing));
}
"""
)

# Settings / RoundedRaff: 4px tab gap, 4px list gap, 6px spacing below tabs,
# full-width selected pill (0px horizontal tab inset), and BE +2px.
replace_once(
    "src/activities/settings/SettingsActivity.h",
    """  int tabGapPx() const override {
    return SETTINGS.uiTheme == CrossPointSettings::ROUNDEDRAFF ? 6 : 0;
  }
  void buildScreen(UiScreen& screen) override;
""",
    """  int tabGapPx() const override {
    return SETTINGS.uiTheme == CrossPointSettings::ROUNDEDRAFF ? 4 : 0;
  }
  int tabHorizontalInsetPx() const override {
    return SETTINGS.uiTheme == CrossPointSettings::ROUNDEDRAFF ? 0 : -1;
  }
  int tabBottomSpacingPx() const override {
    return SETTINGS.uiTheme == CrossPointSettings::ROUNDEDRAFF ? 6 : -1;
  }
  void buildScreen(UiScreen& screen) override;
"""
)
replace_once(
    "src/activities/settings/SettingsActivity.cpp",
    """    rowValues_[i] = settingValueText(settings[i]);
    rowItems_[i].value = rowValues_[i].empty() ? nullptr : rowValues_[i].c_str();
""",
    """    rowValues_[i] = settingValueText(settings[i]);
    rowItems_[i].value = rowValues_[i].empty() ? nullptr : rowValues_[i].c_str();
    rowItems_[i].valueOffsetX =
        (I18N.getLanguage() == Language::HU && rowValues_[i] == tr(STR_STATE_ON)) ? 2 : 0;
"""
)
replace_once(
    "src/activities/settings/SettingsActivity.cpp",
    """  if (SETTINGS.uiTheme == CrossPointSettings::ROUNDEDRAFF) props.rowGap = 5;
""",
    """  if (SETTINGS.uiTheme == CrossPointSettings::ROUNDEDRAFF) props.rowGap = 4;
"""
)

# Reader menu / RoundedRaff: move progress band up 2px via tab bottom spacing,
# move the list another 2px up, and use a 4px row gap.
p = Path("src/activities/reader/EpubReaderMenuActivity.h")
s = p.read_text(encoding="utf-8")
if '#include "CrossPointSettings.h"' not in s:
    s = s.replace('#include "activities/UiTabListActivity.h"\n',
                  '#include "CrossPointSettings.h"\n#include "activities/UiTabListActivity.h"\n', 1)
p.write_text(s, encoding="utf-8")
replace_once(
    "src/activities/reader/EpubReaderMenuActivity.h",
    """  int tabWidthPercent(int index) const override;
  void onTabAction(int index) override;
""",
    """  int tabWidthPercent(int index) const override;
  int tabBottomSpacingPx() const override {
    return SETTINGS.uiTheme == CrossPointSettings::ROUNDEDRAFF ? 8 : -1;
  }
  void onTabAction(int index) override;
"""
)
replace_once(
    "src/activities/reader/EpubReaderMenuActivity.cpp",
    """  screen.target().text(band.inset(fui::Insets{0, pad, 0, pad}), progressLine.c_str(), screen.theme().smallText);
  screen.spacer(static_cast<int16_t>(metrics.verticalSpacing));
""",
    """  screen.target().text(band.inset(fui::Insets{0, pad, 0, pad}), progressLine.c_str(), screen.theme().smallText);
  const int16_t progressGap = static_cast<int16_t>(
      SETTINGS.uiTheme == CrossPointSettings::ROUNDEDRAFF ? metrics.verticalSpacing - 2 : metrics.verticalSpacing);
  screen.spacer(progressGap);
"""
)
replace_once(
    "src/activities/reader/EpubReaderMenuActivity.cpp",
    """  props.valueInset = 8;
  props.labelText = screen.theme().bodyText;
""",
    """  props.valueInset = 8;
  if (SETTINGS.uiTheme == CrossPointSettings::ROUNDEDRAFF) props.rowGap = 4;
  props.labelText = screen.theme().bodyText;
"""
)

# Text Settings / Layout + Style: Hungarian KI +4px only.
replace_once(
    "src/activities/settings/TextSettingsActivity.cpp",
    """    rowItems_[i].value = rowValues_[i].empty() ? nullptr : rowValues_[i].c_str();
  }

  fui::ListProps props;
""",
    """    rowItems_[i].value = rowValues_[i].empty() ? nullptr : rowValues_[i].c_str();
    const bool nudgeOffRight =
        I18N.getLanguage() == Language::HU &&
        (tab_ == Tab::Layout || tab_ == Tab::Style) &&
        rowValues_[i] == tr(STR_STATE_OFF);
    rowItems_[i].valueOffsetX = nudgeOffRight ? 4 : 0;
  }

  fui::ListProps props;
"""
)

print("CPHUN-174 UI spacing and optical value alignment applied")
