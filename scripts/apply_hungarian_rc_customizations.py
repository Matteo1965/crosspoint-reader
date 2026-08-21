from pathlib import Path


def replace_once(path: str, old: str, new: str) -> None:
    p = Path(path)
    text = p.read_text()
    if old not in text:
        raise SystemExit(f"Customization marker not found in {path}: {old[:80]!r}")
    p.write_text(text.replace(old, new, 1))


# RC base version. The gh_release_rc environment appends only "-rc".
replace_once("platformio.ini", "version = 1.5.0", "version = 1.6.0")

# Hungarian Edition version-page text.
replace_once(
    "src/activities/settings/CrossPointVersionActivity.cpp",
    "Magyar szótövezés: 300 egyedi szóalak",
    "Magyar szótövezés: 357 új szóalak",
)

# Hungarian SD-card firmware-update label.
replace_once(
    "lib/I18n/translations/hungarian.yaml",
    "Firmware-frissítés SD-kártya",
    "Firmware frissítés SD-kártyáról",
)

# Add the long lower-button screenshot setting label to the English master and Hungarian translation.
replace_once(
    "lib/I18n/translations/english.yaml",
    'STR_LONG_PRESS_MENU: "Long press: Menu"',
    'STR_LONG_PRESS_MENU: "Long press: Menu"\nSTR_LONG_DOWN_SCREENSHOT: "Long lower button: Screenshot"',
)
replace_once(
    "lib/I18n/translations/hungarian.yaml",
    'STR_LONG_PRESS_MENU: "Hosszan: Menü"',
    'STR_LONG_PRESS_MENU: "Hosszan: Menü"\nSTR_LONG_DOWN_SCREENSHOT: "Hosszú alsó gomb: Képernyőkép"',
)

# Persisted toggle, default OFF.
replace_once(
    "src/CrossPointSettings.h",
    """  uint8_t longPressMenuFunction = LP_MENU_DISABLED;\n  // UI Theme""",
    """  uint8_t longPressMenuFunction = LP_MENU_DISABLED;\n  // Global screenshot shortcut: long press of the physical lower side button.\n  uint8_t longDownScreenshot = 0;\n  // UI Theme""",
)

# Put the new toggle at the very bottom of Settings > Controls.
replace_once(
    "src/SettingsList.h",
    """        SettingInfo::Toggle(StrId::STR_BACK_SHORT_TO_FILE_BROWSER, &CrossPointSettings::backShortToFileBrowser,\n                            \"backShortToFileBrowser\", StrId::STR_CAT_CONTROLS),\n\n        // --- System ---""",
    """        SettingInfo::Toggle(StrId::STR_BACK_SHORT_TO_FILE_BROWSER, &CrossPointSettings::backShortToFileBrowser,\n                            \"backShortToFileBrowser\", StrId::STR_CAT_CONTROLS),\n        SettingInfo::Toggle(StrId::STR_LONG_DOWN_SCREENSHOT, &CrossPointSettings::longDownScreenshot,\n                            \"longDownScreenshot\", StrId::STR_CAT_CONTROLS),\n\n        // --- System ---""",
)

# Global physical lower-side-button long press screenshot. Consume the held
# button and its release after capture so the same gesture cannot also page-turn.
replace_once(
    "src/main.cpp",
    """  // Consume the second X4 Pro power-button release so it does not also run a\n  // configured short-power action after toggling the frontlight.\n  if (handleX4ProFrontlightDoubleClick()) {""",
    """  static unsigned long longDownScreenshotStartedAt = 0;\n  static bool longDownScreenshotCaptured = false;\n  static bool longDownScreenshotConsumeRelease = false;\n  constexpr unsigned long LONG_DOWN_SCREENSHOT_MS = 600;\n\n  if (SETTINGS.longDownScreenshot && !gpio.isPressed(HalGPIO::BTN_POWER)) {\n    if (gpio.isPressed(HalGPIO::BTN_DOWN)) {\n      if (longDownScreenshotStartedAt == 0) longDownScreenshotStartedAt = millis();\n      if (!longDownScreenshotCaptured && millis() - longDownScreenshotStartedAt >= LONG_DOWN_SCREENSHOT_MS) {\n        {\n          RenderLock lock;\n          ScreenshotUtil::takeScreenshot(renderer);\n        }\n        longDownScreenshotCaptured = true;\n        longDownScreenshotConsumeRelease = true;\n      }\n      if (longDownScreenshotCaptured) return;\n    } else {\n      longDownScreenshotStartedAt = 0;\n      longDownScreenshotCaptured = false;\n      if (longDownScreenshotConsumeRelease && gpio.wasReleased(HalGPIO::BTN_DOWN)) {\n        longDownScreenshotConsumeRelease = false;\n        return;\n      }\n      longDownScreenshotConsumeRelease = false;\n    }\n  } else if (!gpio.isPressed(HalGPIO::BTN_DOWN)) {\n    longDownScreenshotStartedAt = 0;\n    longDownScreenshotCaptured = false;\n    longDownScreenshotConsumeRelease = false;\n  }\n\n  // Consume the second X4 Pro power-button release so it does not also run a\n  // configured short-power action after toggling the frontlight.\n  if (handleX4ProFrontlightDoubleClick()) {""",
)

# RoundedRaff Hungarian Edition home geometry only.
replace_once(
    "src/components/themes/roundedraff/RoundedRaffTheme.h",
    "// Hungarian Edition home cover: 368px, tile remains 392px.\n                                 .homeCoverHeight = 368,\n                                 .homeCoverTileHeight = 392,",
    "// Hungarian Edition home cover: 384px, tile remains 400px.\n                                 .homeCoverHeight = 384,\n                                 .homeCoverTileHeight = 400,",
)

# RoundedRaff home header: title only, no battery indicator. Other screens and other themes retain normal header.
replace_once(
    "src/components/themes/roundedraff/RoundedRaffTheme.cpp",
    """  // Home screen header is custom-rendered in drawRecentBookCover.\n  if (title == nullptr) {\n    return;\n  }\n  BaseTheme::drawHeader(renderer, rect, title, subtitle);""",
    """  // RoundedRaff home header: keep the book title, but omit the battery\n  // indicator so it cannot collide with long titles. Other RoundedRaff\n  // screens, and all other themes, retain the normal header battery.\n  if (title == nullptr) {\n    return;\n  }\n  if (rect.height == RoundedRaffMetrics::values.homeTopPadding - RoundedRaffMetrics::values.topPadding) {\n    const int maxWidth = rect.width - 2 * RoundedRaffMetrics::values.headerSidePadding;\n    const std::string homeTitle = renderer.truncatedText(kTitleFontId, title, maxWidth, EpdFontFamily::BOLD);\n    renderer.drawText(kTitleFontId, rect.x + RoundedRaffMetrics::values.headerSidePadding, rect.y, homeTitle.c_str(),\n                      true, EpdFontFamily::BOLD);\n    return;\n  }\n  BaseTheme::drawHeader(renderer, rect, title, subtitle);""",
)

# Leave heap free for the 384px thumbnail before caching the 400px RoundedRaff card.
replace_once(
    "src/activities/home/HomeActivity.cpp",
    """bool HomeActivity::storeCoverBuffer() {\n  // render() must have already set the cover rect; without it we'd be back to\n  // cloning the whole framebuffer.""",
    """bool HomeActivity::storeCoverBuffer() {\n  if (static_cast<CrossPointSettings::UI_THEME>(SETTINGS.uiTheme) ==\n          CrossPointSettings::UI_THEME::ROUNDEDRAFF &&\n      !recentsLoaded) {\n    return false;\n  }\n\n  // render() must have already set the cover rect; without it we'd be back to\n  // cloning the whole framebuffer.""",
)

# Hide Settings header version only for RoundedRaff.
replace_once(
    "src/activities/settings/SettingsActivity.cpp",
    """  GUI.drawHeader(renderer, Rect{0, metrics.topPadding, pageWidth, metrics.headerHeight}, tr(STR_SETTINGS_TITLE),\n                 CROSSPOINT_VERSION);""",
    """  const char* settingsVersion =\n      static_cast<CrossPointSettings::UI_THEME>(SETTINGS.uiTheme) == CrossPointSettings::UI_THEME::ROUNDEDRAFF\n          ? nullptr\n          : CROSSPOINT_VERSION;\n  GUI.drawHeader(renderer, Rect{0, metrics.topPadding, pageWidth, metrics.headerHeight}, tr(STR_SETTINGS_TITLE),\n                 settingsVersion);""",
)

# On RoundedRaff Settings only, move battery icon/percentage down by 8px.
replace_once(
    "src/components/themes/BaseTheme.cpp",
    """  const int16_t batteryH = static_cast<int16_t>(metrics.batteryBarHeight);\n  fui::batteryIndicator(ui.frame, fui::Rect{batteryX, band.y, batteryReserve, batteryH}, battery);""",
    """  const int16_t batteryH = static_cast<int16_t>(metrics.batteryBarHeight);\n  const bool roundedRaffSettingsHeader =\n      static_cast<CrossPointSettings::UI_THEME>(SETTINGS.uiTheme) == CrossPointSettings::UI_THEME::ROUNDEDRAFF &&\n      title != nullptr && strcmp(title, tr(STR_SETTINGS_TITLE)) == 0;\n  const int16_t batteryY = static_cast<int16_t>(band.y + (roundedRaffSettingsHeader ? 8 : 0));\n  fui::batteryIndicator(ui.frame, fui::Rect{batteryX, batteryY, batteryReserve, batteryH}, battery);""",
)

print("Hungarian RC customizations applied")
