#!/usr/bin/env python3
from pathlib import Path
import re

def replace_once(path, old, new):
    p = Path(path)
    s = p.read_text(encoding="utf-8")
    if old not in s:
        raise SystemExit(f"CPHUN-173 anchor missing in {path}: {old[:80]!r}")
    if s.count(old) != 1:
        raise SystemExit(f"CPHUN-173 anchor not unique in {path}: {old[:80]!r}")
    p.write_text(s.replace(old, new, 1), encoding="utf-8")

# Shared tab screens: allow individual screens to opt into weighted-tab margins,
# gaps, and a denser row gap without changing the RoundedRaff theme globally.
replace_once(
    "src/activities/UiTabListActivity.h",
    """  virtual int tabWidthPercent(int index) const {
    (void)index;
    return 0;
  }
""",
    """  virtual int tabWidthPercent(int index) const {
    (void)index;
    return 0;
  }
  virtual int tabSideMarginPx() const { return 0; }
  virtual int tabGapPx() const { return 0; }
  virtual int listRowGapPx() const { return -1; }
"""
)

p = Path("src/activities/UiTabListActivity.cpp")
ts = p.read_text(encoding="utf-8")
pattern = re.compile(
    r"(?m)^(?P<indent>\s*)const uint16_t rows = fui::listVisibleRows\(screen\.body\(\),\s*rowHeight,\s*[^;]+\);$"
)
m = pattern.search(ts)
if not m:
    raise SystemExit("CPHUN-173 row-gap listVisibleRows declaration not found in src/activities/UiTabListActivity.cpp")
indent = m.group("indent")
replacement = (
    f"{indent}const int customRowGap = listRowGapPx();\n"
    f"{indent}const int rowGap = customRowGap >= 0 ? customRowGap : screen.theme().listRowGap;\n"
    f"{indent}const uint16_t rows = fui::listVisibleRows(screen.body(), rowHeight, rowGap);"
)
ts = ts[:m.start()] + replacement + ts[m.end():]
p.write_text(ts, encoding="utf-8")

replace_once(
    "src/activities/UiTabListActivity.cpp",
    """  if (weightedTabs) {
    int cumulative = 0;
    for (int i = 0; i < count; ++i) {
      const int width = tabWidthPercent(i);
      const int slotX = tabRect.x + (static_cast<int>(tabRect.width) * cumulative) / 100;
      cumulative += width;
      const int slotRight = tabRect.x + (static_cast<int>(tabRect.width) * cumulative) / 100;
      fui::TabBarProps singleProps = tabProps;
      singleProps.tabs = &tabs[i];
      singleProps.count = 1;
      fui::tabBar(screen.frame(), fui::Rect{static_cast<int16_t>(slotX), tabRect.y,
                  static_cast<int16_t>(slotRight - slotX), tabRect.height}, singleProps);
    }
""",
    """  if (weightedTabs) {
    const int sideMargin = tabSideMarginPx() > 0 ? tabSideMarginPx() : 0;
    const int gap = tabGapPx() > 0 ? tabGapPx() : 0;
    const int innerWidth =
        static_cast<int>(tabRect.width) - sideMargin * 2 - gap * (count > 0 ? count - 1 : 0);
    const int innerX = static_cast<int>(tabRect.x) + sideMargin;
    int cumulative = 0;
    for (int i = 0; i < count; ++i) {
      const int width = tabWidthPercent(i);
      const int slotX = innerX + (innerWidth * cumulative) / 100 + gap * i;
      cumulative += width;
      const int slotRight = innerX + (innerWidth * cumulative) / 100 + gap * i;
      fui::TabBarProps singleProps = tabProps;
      singleProps.tabs = &tabs[i];
      singleProps.count = 1;
      fui::tabBar(screen.frame(), fui::Rect{static_cast<int16_t>(slotX), tabRect.y,
                  static_cast<int16_t>(slotRight - slotX), tabRect.height}, singleProps);
    }
"""
)

# Settings / RoundedRaff: 23/23/24/30 tabs, 16px side margins, 6px gaps,
# and 5px vertical gaps so Keyboard Layouts remains visible.
replace_once(
    "src/activities/settings/SettingsActivity.h",
    """  const char* tabLabel(int index) const override { return I18N.get(categoryNames[index]); }
  void buildScreen(UiScreen& screen) override;
""",
    """  const char* tabLabel(int index) const override { return I18N.get(categoryNames[index]); }
  int tabWidthPercent(int index) const override {
    if (SETTINGS.uiTheme != CrossPointSettings::ROUNDEDRAFF) return 0;
    static constexpr int widths[categoryCount] = {23, 23, 24, 30};
    return index >= 0 && index < categoryCount ? widths[index] : 0;
  }
  int tabSideMarginPx() const override {
    return SETTINGS.uiTheme == CrossPointSettings::ROUNDEDRAFF ? 16 : 0;
  }
  int tabGapPx() const override {
    return SETTINGS.uiTheme == CrossPointSettings::ROUNDEDRAFF ? 6 : 0;
  }
  int listRowGapPx() const override {
    return SETTINGS.uiTheme == CrossPointSettings::ROUNDEDRAFF ? 5 : -1;
  }
  void buildScreen(UiScreen& screen) override;
"""
)

# Library / RoundedRaff: 41/25/34 tabs with the same 16px/6px geometry.
p = Path("src/activities/library/LibraryListActivity.h")
hs = p.read_text(encoding="utf-8")
if '#include "CrossPointSettings.h"' not in hs:
    hs = hs.replace('#include "RecentBooksStore.h"\n', '#include "CrossPointSettings.h"\n#include "RecentBooksStore.h"\n', 1)
p.write_text(hs, encoding="utf-8")

replace_once(
    "src/activities/library/LibraryListActivity.h",
    """  const char* tabLabel(int index) const override;
  freeink::ui::TabIndicator tabIndicator(int index) const override;
""",
    """  const char* tabLabel(int index) const override;
  int tabWidthPercent(int index) const override {
    if (SETTINGS.uiTheme != CrossPointSettings::ROUNDEDRAFF) return 0;
    static constexpr int widths[3] = {41, 25, 34};
    return index >= 0 && index < 3 ? widths[index] : 0;
  }
  int tabSideMarginPx() const override {
    return SETTINGS.uiTheme == CrossPointSettings::ROUNDEDRAFF ? 16 : 0;
  }
  int tabGapPx() const override {
    return SETTINGS.uiTheme == CrossPointSettings::ROUNDEDRAFF ? 6 : 0;
  }
  freeink::ui::TabIndicator tabIndicator(int index) const override;
"""
)

replace_once(
    "src/activities/library/LibraryListActivity.cpp",
    """  const int y = renderer.getScreenHeight() - metrics.buttonHintsHeight - renderer.getLineHeight(SMALL_FONT_ID);
""",
    """  const int y = renderer.getScreenHeight() - metrics.buttonHintsHeight - renderer.getLineHeight(SMALL_FONT_ID) - 2;
"""
)

replace_once(
    "src/activities/library/LibraryListActivity.cpp",
    """  const int y = renderer.getScreenHeight() - metrics.buttonHintsHeight - lineHeight;
  GUI.drawHelpText(renderer, Rect{SIDE_PADDING, y, renderer.getScreenWidth() / 2 - SIDE_PADDING, lineHeight}, help);
""",
    """  const int y = renderer.getScreenHeight() - metrics.buttonHintsHeight - lineHeight - 2;
  constexpr int kHoldHelpWidth = 320;
  GUI.drawHelpText(renderer, Rect{SIDE_PADDING, y, kHoldHelpWidth, lineHeight}, help);
"""
)

# Hungarian wording requested for the Library tab hold hint.
p = Path("lib/I18n/translations/hungarian.yaml")
s = p.read_text(encoding="utf-8")
old = 'STR_LIBRARY_HOLD_SORT: "Hosszú nyomás: Fordított rendezés"'
new = 'STR_LIBRARY_HOLD_SORT: "Hosszan: Fordított rendezés"'
if old in s:
    s = s.replace(old, new, 1)
elif new not in s:
    raise SystemExit("CPHUN-173 Hungarian Library hold-sort label anchor missing")
p.write_text(s, encoding="utf-8")

print("CPHUN-173 RoundedRaff Settings and Library UI tuning applied")
