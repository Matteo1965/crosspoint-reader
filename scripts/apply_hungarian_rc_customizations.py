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

# RoundedRaff Hungarian Edition home geometry only.
replace_once(
    "src/components/themes/roundedraff/RoundedRaffTheme.h",
    "// Hungarian Edition home cover: 368px, tile remains 392px.\n                                 .homeCoverHeight = 368,\n                                 .homeCoverTileHeight = 392,",
    "// Hungarian Edition home cover: 384px, tile remains 400px.\n                                 .homeCoverHeight = 384,\n                                 .homeCoverTileHeight = 400,",
)

# RoundedRaff home header: title only, no battery indicator. Other screens and
# other themes retain the normal BaseTheme header.
replace_once(
    "src/components/themes/roundedraff/RoundedRaffTheme.cpp",
    """  // Home screen header is custom-rendered in drawRecentBookCover.\n  if (title == nullptr) {\n    return;\n  }\n  BaseTheme::drawHeader(renderer, rect, title, subtitle);""",
    """  // RoundedRaff home header: keep the book title, but omit the battery\n  // indicator so it cannot collide with long titles. Other RoundedRaff\n  // screens, and all other themes, retain the normal header battery.\n  if (title == nullptr) {\n    return;\n  }\n  if (rect.height == RoundedRaffMetrics::values.homeTopPadding - RoundedRaffMetrics::values.topPadding) {\n    const int maxWidth = rect.width - 2 * RoundedRaffMetrics::values.headerSidePadding;\n    const std::string homeTitle = renderer.truncatedText(kTitleFontId, title, maxWidth, EpdFontFamily::BOLD);\n    renderer.drawText(kTitleFontId, rect.x + RoundedRaffMetrics::values.headerSidePadding, rect.y, homeTitle.c_str(),\n                      true, EpdFontFamily::BOLD);\n    return;\n  }\n  BaseTheme::drawHeader(renderer, rect, title, subtitle);""",
)

# Do not reserve the 400px RoundedRaff cover framebuffer before the requested
# 384px thumbnail has been checked/generated. This leaves heap available for
# JPEG/PNG conversion. Once recentsLoaded becomes true, the next render stores
# the completed card normally. Other themes are untouched.
replace_once(
    "src/activities/home/HomeActivity.cpp",
    """bool HomeActivity::storeCoverBuffer() {\n  // render() must have already set the cover rect; without it we'd be back to\n  // cloning the whole framebuffer.""",
    """bool HomeActivity::storeCoverBuffer() {\n  if (static_cast<CrossPointSettings::UI_THEME>(SETTINGS.uiTheme) ==\n          CrossPointSettings::UI_THEME::ROUNDEDRAFF &&\n      !recentsLoaded) {\n    return false;\n  }\n\n  // render() must have already set the cover rect; without it we'd be back to\n  // cloning the whole framebuffer.""",
)

# The Settings header version label collides with other text in RoundedRaff.
# Hide it only for RoundedRaff; Classic/Lyra and other themes keep it.
replace_once(
    "src/activities/settings/SettingsActivity.cpp",
    """  GUI.drawHeader(renderer, Rect{0, metrics.topPadding, pageWidth, metrics.headerHeight}, tr(STR_SETTINGS_TITLE),\n                 CROSSPOINT_VERSION);""",
    """  const char* settingsVersion =\n      static_cast<CrossPointSettings::UI_THEME>(SETTINGS.uiTheme) == CrossPointSettings::UI_THEME::ROUNDEDRAFF\n          ? nullptr\n          : CROSSPOINT_VERSION;\n  GUI.drawHeader(renderer, Rect{0, metrics.topPadding, pageWidth, metrics.headerHeight}, tr(STR_SETTINGS_TITLE),\n                 settingsVersion);""",
)

# On the RoundedRaff Settings page only, move the battery icon and percentage
# down by 8px. Other RoundedRaff headers and all other themes keep their normal
# battery position.
replace_once(
    "src/components/themes/BaseTheme.cpp",
    """  const int16_t batteryH = static_cast<int16_t>(metrics.batteryBarHeight);\n  fui::batteryIndicator(ui.frame, fui::Rect{batteryX, band.y, batteryReserve, batteryH}, battery);""",
    """  const int16_t batteryH = static_cast<int16_t>(metrics.batteryBarHeight);\n  const bool roundedRaffSettingsHeader =\n      static_cast<CrossPointSettings::UI_THEME>(SETTINGS.uiTheme) == CrossPointSettings::UI_THEME::ROUNDEDRAFF &&\n      title != nullptr && strcmp(title, tr(STR_SETTINGS_TITLE)) == 0;\n  const int16_t batteryY = static_cast<int16_t>(band.y + (roundedRaffSettingsHeader ? 8 : 0));\n  fui::batteryIndicator(ui.frame, fui::Rect{batteryX, batteryY, batteryReserve, batteryH}, battery);""",
)

print("Hungarian RC customizations applied")
