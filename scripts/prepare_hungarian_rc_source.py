from pathlib import Path


def replace_if_present(path: str, old: str, new: str) -> None:
    p = Path(path)
    text = p.read_text()
    if new in text:
        return
    if old not in text:
        raise SystemExit(f"marker not found in {path}: {old[:100]!r}")
    p.write_text(text.replace(old, new, 1))


def append_keys(path: str, keys: str) -> None:
    p = Path(path)
    text = p.read_text()
    first_key = keys.strip().splitlines()[0].split(':', 1)[0]
    if first_key in text:
        return
    p.write_text(text.rstrip() + "\n" + keys.strip() + "\n")


replace_if_present("platformio.ini", "version = 1.5.0", "version = 1.6.0")

replace_if_present(
    "lib/I18n/translations/hungarian.yaml",
    'STR_SD_FIRMWARE_UPDATE: "Firmware-frissítés SD-kártya"',
    'STR_SD_FIRMWARE_UPDATE: "Firmware frissítés SD-kártyáról"',
)
append_keys(
    "lib/I18n/translations/english.yaml",
    '''
STR_PICTURE_FILTER: "Picture filter"
STR_BRIGHTER_10: "10% Brighter"
STR_BRIGHTER_20: "20% Brighter"
STR_LONG_DOWN_SCREENSHOT: "Long lower button: Screenshot"
''',
)
append_keys(
    "lib/I18n/translations/hungarian.yaml",
    '''
STR_PICTURE_FILTER: "Képszűrő"
STR_BRIGHTER_10: "10% Világosabb"
STR_BRIGHTER_20: "20% Világosabb"
STR_LONG_DOWN_SCREENSHOT: "Hosszú alsó gomb: Képernyőkép"
''',
)

# Global long lower-button screenshot. ButtonNavigator switches to release-based
# navigation while enabled, so menus do not auto-repeat before the long hold fires.
replace_if_present(
    "src/main.cpp",
    '#include "CrossPointSettings.h"',
    '#include "CrossPointSettings.h"\n#include "HungarianEditionFeatures.h"',
)
replace_if_present(
    "src/main.cpp",
    """  // Consume the second X4 Pro power-button release so it does not also run a\n  // configured short-power action after toggling the frontlight.\n  if (handleX4ProFrontlightDoubleClick()) {""",
    """  static unsigned long longDownScreenshotStartedAt = 0;\n  static bool longDownScreenshotCaptured = false;\n  static bool longDownScreenshotConsumeRelease = false;\n  constexpr unsigned long LONG_DOWN_SCREENSHOT_MS = 600;\n\n  if (HungarianEditionFeatures::longDownScreenshot() && !gpio.isPressed(HalGPIO::BTN_POWER)) {\n    if (gpio.isPressed(HalGPIO::BTN_DOWN)) {\n      if (longDownScreenshotStartedAt == 0) longDownScreenshotStartedAt = millis();\n      if (!longDownScreenshotCaptured && millis() - longDownScreenshotStartedAt >= LONG_DOWN_SCREENSHOT_MS) {\n        {\n          RenderLock lock;\n          ScreenshotUtil::takeScreenshot(renderer);\n        }\n        longDownScreenshotCaptured = true;\n        longDownScreenshotConsumeRelease = true;\n      }\n      if (longDownScreenshotCaptured) return;\n    } else {\n      longDownScreenshotStartedAt = 0;\n      longDownScreenshotCaptured = false;\n      if (longDownScreenshotConsumeRelease && gpio.wasReleased(HalGPIO::BTN_DOWN)) {\n        longDownScreenshotConsumeRelease = false;\n        return;\n      }\n      longDownScreenshotConsumeRelease = false;\n    }\n  } else if (!gpio.isPressed(HalGPIO::BTN_DOWN)) {\n    longDownScreenshotStartedAt = 0;\n    longDownScreenshotCaptured = false;\n    longDownScreenshotConsumeRelease = false;\n  }\n\n  // Consume the second X4 Pro power-button release so it does not also run a\n  // configured short-power action after toggling the frontlight.\n  if (handleX4ProFrontlightDoubleClick()) {""",
)

# RoundedRaff Home: no battery in header and brightness-aware cover.
replace_if_present(
    "src/components/themes/roundedraff/RoundedRaffTheme.cpp",
    '#include "RoundedRaffTheme.h"',
    '#include "RoundedRaffTheme.h"\n\n#include "HungarianEditionFeatures.h"\n#include "HungarianImageBrightness.h"',
)
replace_if_present(
    "src/components/themes/roundedraff/RoundedRaffTheme.cpp",
    """  // Home screen header is custom-rendered in drawRecentBookCover.\n  if (title == nullptr) {\n    return;\n  }\n  BaseTheme::drawHeader(renderer, rect, title, subtitle);""",
    """  if (title == nullptr) return;\n  if (rect.height == RoundedRaffMetrics::values.homeTopPadding - RoundedRaffMetrics::values.topPadding) {\n    const int maxWidth = rect.width - 2 * RoundedRaffMetrics::values.headerSidePadding;\n    const std::string homeTitle = renderer.truncatedText(kTitleFontId, title, maxWidth, EpdFontFamily::BOLD);\n    renderer.drawText(kTitleFontId, rect.x + RoundedRaffMetrics::values.headerSidePadding, rect.y, homeTitle.c_str(),\n                      true, EpdFontFamily::BOLD);\n    return;\n  }\n  BaseTheme::drawHeader(renderer, rect, title, subtitle);""",
)
replace_if_present(
    "src/components/themes/roundedraff/RoundedRaffTheme.cpp",
    """            renderer.drawBitmap(bitmap, tileX + (tileWidth - coverWidth) / 2, imgY, coverWidth,\n                                RoundedRaffMetrics::values.homeCoverHeight);\n            renderer.maskRoundedRectOutsideCorners""",
    """            const int coverX = tileX + (tileWidth - coverWidth) / 2;\n            renderer.drawBitmap(bitmap, coverX, imgY, coverWidth, RoundedRaffMetrics::values.homeCoverHeight);\n            HungarianImageBrightness::apply(renderer, coverX, imgY, coverWidth,\n                                             RoundedRaffMetrics::values.homeCoverHeight,\n                                             HungarianEditionFeatures::brightnessPercentForCover());\n            renderer.maskRoundedRectOutsideCorners""",
)

replace_if_present(
    "src/activities/home/HomeActivity.cpp",
    """bool HomeActivity::storeCoverBuffer() {\n  // render() must have already set the cover rect; without it we'd be back to\n  // cloning the whole framebuffer.""",
    """bool HomeActivity::storeCoverBuffer() {\n  if (static_cast<CrossPointSettings::UI_THEME>(SETTINGS.uiTheme) ==\n          CrossPointSettings::UI_THEME::ROUNDEDRAFF &&\n      !recentsLoaded) {\n    return false;\n  }\n\n  // render() must have already set the cover rect; without it we'd be back to\n  // cloning the whole framebuffer.""",
)

replace_if_present(
    "src/activities/settings/SettingsActivity.cpp",
    """  GUI.drawHeader(renderer, Rect{0, metrics.topPadding, pageWidth, metrics.headerHeight}, tr(STR_SETTINGS_TITLE),\n                 CROSSPOINT_VERSION);""",
    """  const char* settingsVersion =\n      static_cast<CrossPointSettings::UI_THEME>(SETTINGS.uiTheme) == CrossPointSettings::UI_THEME::ROUNDEDRAFF\n          ? nullptr\n          : CROSSPOINT_VERSION;\n  GUI.drawHeader(renderer, Rect{0, metrics.topPadding, pageWidth, metrics.headerHeight}, tr(STR_SETTINGS_TITLE),\n                 settingsVersion);""",
)
replace_if_present(
    "src/components/themes/BaseTheme.cpp",
    """  const int16_t batteryH = static_cast<int16_t>(metrics.batteryBarHeight);\n  fui::batteryIndicator(ui.frame, fui::Rect{batteryX, band.y, batteryReserve, batteryH}, battery);""",
    """  const int16_t batteryH = static_cast<int16_t>(metrics.batteryBarHeight);\n  const bool roundedRaffSettingsHeader =\n      static_cast<CrossPointSettings::UI_THEME>(SETTINGS.uiTheme) == CrossPointSettings::UI_THEME::ROUNDEDRAFF &&\n      title != nullptr && strcmp(title, tr(STR_SETTINGS_TITLE)) == 0;\n  const int16_t batteryY = static_cast<int16_t>(band.y + (roundedRaffSettingsHeader ? 8 : 0));\n  fui::batteryIndicator(ui.frame, fui::Rect{batteryX, batteryY, batteryReserve, batteryH}, battery);""",
)

# EPUB image brightness.
replace_if_present(
    "lib/Epub/Epub/blocks/ImageBlock.cpp",
    '#include "Epub/converters/DirectPixelWriter.h"',
    '#include "Epub/converters/DirectPixelWriter.h"\n#include <HungarianEditionFeatures.h>\n#include <HungarianImageBrightness.h>',
)
replace_if_present(
    "lib/Epub/Epub/blocks/ImageBlock.cpp",
    """  if (renderFromCache(renderer, cachePath, x, y, width, height)) {\n    renderer.preserveImagePolarity(x, y, width, height);""",
    """  if (renderFromCache(renderer, cachePath, x, y, width, height)) {\n    HungarianImageBrightness::apply(renderer, x, y, width, height,\n                                     HungarianEditionFeatures::brightnessPercentForPicture());\n    renderer.preserveImagePolarity(x, y, width, height);""",
)
replace_if_present(
    "lib/Epub/Epub/blocks/ImageBlock.cpp",
    """  renderer.preserveImagePolarity(x, y, width, height);\n  LOG_DBG("IMG", "Decode successful");""",
    """  HungarianImageBrightness::apply(renderer, x, y, width, height,\n                                   HungarianEditionFeatures::brightnessPercentForPicture());\n  renderer.preserveImagePolarity(x, y, width, height);\n  LOG_DBG("IMG", "Decode successful");""",
)

# Sleep cover brightness on all three grayscale passes.
replace_if_present(
    "src/activities/boot_sleep/SleepActivity.cpp",
    '#include "CrossPointSettings.h"',
    '#include "CrossPointSettings.h"\n#include "HungarianEditionFeatures.h"\n#include "HungarianImageBrightness.h"',
)
replace_if_present(
    "src/activities/boot_sleep/SleepActivity.cpp",
    """  renderer.drawBitmap(bitmap, x, y, pageWidth, pageHeight, cropX, cropY);\n\n  if (!preserveBackground &&""",
    """  renderer.drawBitmap(bitmap, x, y, pageWidth, pageHeight, cropX, cropY);\n  if (!preserveBackground) {\n    HungarianImageBrightness::apply(renderer, 0, 0, pageWidth, pageHeight,\n                                     HungarianEditionFeatures::brightnessPercentForCover());\n  }\n\n  if (!preserveBackground &&""",
)
replace_if_present(
    "src/activities/boot_sleep/SleepActivity.cpp",
    """    renderer.drawBitmap(bitmap, x, y, pageWidth, pageHeight, cropX, cropY);\n    renderer.copyGrayscaleLsbBuffers();""",
    """    renderer.drawBitmap(bitmap, x, y, pageWidth, pageHeight, cropX, cropY);\n    if (!preserveBackground) {\n      HungarianImageBrightness::apply(renderer, 0, 0, pageWidth, pageHeight,\n                                       HungarianEditionFeatures::brightnessPercentForCover());\n    }\n    renderer.copyGrayscaleLsbBuffers();""",
)
replace_if_present(
    "src/activities/boot_sleep/SleepActivity.cpp",
    """    renderer.drawBitmap(bitmap, x, y, pageWidth, pageHeight, cropX, cropY);\n    renderer.copyGrayscaleMsbBuffers();""",
    """    renderer.drawBitmap(bitmap, x, y, pageWidth, pageHeight, cropX, cropY);\n    if (!preserveBackground) {\n      HungarianImageBrightness::apply(renderer, 0, 0, pageWidth, pageHeight,\n                                       HungarianEditionFeatures::brightnessPercentForCover());\n    }\n    renderer.copyGrayscaleMsbBuffers();""",
)

brightness = Path("src/HungarianImageBrightness.h")
b = brightness.read_text()
if "#include <algorithm>" not in b:
    brightness.write_text(b.replace("#include <GfxRenderer.h>\n", "#include <GfxRenderer.h>\n\n#include <algorithm>\n"))

print("Hungarian RC source preparation complete")
