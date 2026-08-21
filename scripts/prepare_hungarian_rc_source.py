from pathlib import Path


def replace_required(path: str, old: str, new: str) -> None:
    p = Path(path)
    text = p.read_text()
    if old not in text:
        if new in text:
            return
        raise SystemExit(f"marker not found in {path}: {old[:120]!r}")
    p.write_text(text.replace(old, new, 1))


def remove_if_present(path: str, block: str) -> None:
    p = Path(path)
    text = p.read_text()
    if block in text:
        p.write_text(text.replace(block, "", 1))


# Keep the RC version and the already-approved Hungarian SD update wording.
replace_required("platformio.ini", "version = 1.5.0", "version = 1.6.0")
replace_required(
    "lib/I18n/translations/hungarian.yaml",
    'STR_SD_FIRMWARE_UPDATE: "Firmware-frissítés SD-kártya"',
    'STR_SD_FIRMWARE_UPDATE: "Firmware frissítés SD-kártyáról"',
)

# Remove all Hungarian Edition menu extensions that were rejected after device testing.
# The upstream/base settings list remains unchanged. Also normalize a previously saved
# extended cover-filter value back to None so old RC settings cannot leave value 3/4 active.
Path("src/SettingsList.h").write_text(
    '''#pragma once\n\n#define getSettingsList getSettingsListBase\n#include "SettingsListBase.h"\n#undef getSettingsList\n\ninline std::vector<SettingInfo> getSettingsList(const SdCardFontRegistry* registry = nullptr,\n                                                const std::vector<DictionaryEntry>* dictionaries = nullptr) {\n  if (SETTINGS.sleepScreenCoverFilter > 2) {\n    SETTINGS.sleepScreenCoverFilter = 0;\n  }\n  return getSettingsListBase(registry, dictionaries);\n}\n'''
)

# Remove the long-lower-button screenshot hook completely, not merely its menu row.
remove_if_present("src/main.cpp", '#include "HungarianEditionFeatures.h"\n')
remove_if_present(
    "src/main.cpp",
    '''  static unsigned long longDownScreenshotStartedAt = 0;\n  static bool longDownScreenshotCaptured = false;\n  static bool longDownScreenshotConsumeRelease = false;\n  constexpr unsigned long LONG_DOWN_SCREENSHOT_MS = 600;\n\n  if (HungarianEditionFeatures::longDownScreenshot() && !gpio.isPressed(HalGPIO::BTN_POWER)) {\n    if (gpio.isPressed(HalGPIO::BTN_DOWN)) {\n      if (longDownScreenshotStartedAt == 0) longDownScreenshotStartedAt = millis();\n      if (!longDownScreenshotCaptured && millis() - longDownScreenshotStartedAt >= LONG_DOWN_SCREENSHOT_MS) {\n        {\n          RenderLock lock;\n          ScreenshotUtil::takeScreenshot(renderer);\n        }\n        longDownScreenshotCaptured = true;\n        longDownScreenshotConsumeRelease = true;\n      }\n      if (longDownScreenshotCaptured) return;\n    } else {\n      longDownScreenshotStartedAt = 0;\n      longDownScreenshotCaptured = false;\n      if (longDownScreenshotConsumeRelease && gpio.wasReleased(HalGPIO::BTN_DOWN)) {\n        longDownScreenshotConsumeRelease = false;\n        return;\n      }\n      longDownScreenshotConsumeRelease = false;\n    }\n  } else if (!gpio.isPressed(HalGPIO::BTN_DOWN)) {\n    longDownScreenshotStartedAt = 0;\n    longDownScreenshotCaptured = false;\n    longDownScreenshotConsumeRelease = false;\n  }\n\n''',
)

# Remove the rejected line-grid brightness processing from Home covers.
remove_if_present("src/components/themes/roundedraff/RoundedRaffTheme.cpp", '#include "HungarianEditionFeatures.h"\n')
remove_if_present("src/components/themes/roundedraff/RoundedRaffTheme.cpp", '#include "HungarianImageBrightness.h"\n')
replace_required(
    "src/components/themes/roundedraff/RoundedRaffTheme.cpp",
    '''            const int coverX = tileX + (tileWidth - coverWidth) / 2;\n            renderer.drawBitmap(bitmap, coverX, imgY, coverWidth, RoundedRaffMetrics::values.homeCoverHeight);\n            HungarianImageBrightness::apply(renderer, coverX, imgY, coverWidth,\n                                             RoundedRaffMetrics::values.homeCoverHeight,\n                                             HungarianEditionFeatures::brightnessPercentForCover());\n            renderer.maskRoundedRectOutsideCorners''',
    '''            const int coverX = tileX + (tileWidth - coverWidth) / 2;\n            renderer.drawBitmap(bitmap, coverX, imgY, coverWidth, RoundedRaffMetrics::values.homeCoverHeight);\n            renderer.maskRoundedRectOutsideCorners''',
)

# Remove Picture filter processing from EPUB images.
remove_if_present("lib/Epub/Epub/blocks/ImageBlock.cpp", '#include <HungarianEditionFeatures.h>\n')
remove_if_present("lib/Epub/Epub/blocks/ImageBlock.cpp", '#include <HungarianImageBrightness.h>\n')
remove_if_present(
    "lib/Epub/Epub/blocks/ImageBlock.cpp",
    '''    HungarianImageBrightness::apply(renderer, x, y, width, height,\n                                     HungarianEditionFeatures::brightnessPercentForPicture());\n''',
)
remove_if_present(
    "lib/Epub/Epub/blocks/ImageBlock.cpp",
    '''  HungarianImageBrightness::apply(renderer, x, y, width, height,\n                                   HungarianEditionFeatures::brightnessPercentForPicture());\n''',
)

# Remove Cover filter brightness processing from sleep-cover rendering.
remove_if_present("src/activities/boot_sleep/SleepActivity.cpp", '#include "HungarianEditionFeatures.h"\n')
remove_if_present("src/activities/boot_sleep/SleepActivity.cpp", '#include "HungarianImageBrightness.h"\n')
remove_if_present(
    "src/activities/boot_sleep/SleepActivity.cpp",
    '''  if (!preserveBackground) {\n    HungarianImageBrightness::apply(renderer, 0, 0, pageWidth, pageHeight,\n                                     HungarianEditionFeatures::brightnessPercentForCover());\n  }\n\n''',
)
remove_if_present(
    "src/activities/boot_sleep/SleepActivity.cpp",
    '''    if (!preserveBackground) {\n      HungarianImageBrightness::apply(renderer, 0, 0, pageWidth, pageHeight,\n                                       HungarianEditionFeatures::brightnessPercentForCover());\n    }\n''',
)

# Battery icon removal is global. Keep percentage text only.
replace_required(
    "src/components/themes/BaseTheme.cpp",
    '''void BaseTheme::drawBatteryLeft(const GfxRenderer& renderer, Rect rect, const bool showPercentage) const {\n  // Left aligned: icon on left, percentage on right (reader mode)\n  const uint16_t percentage = powerManager.getBatteryPercentage();\n  const int y = rect.y + 6;\n\n  if (showPercentage) {\n    const auto percentageText = std::to_string(percentage) + "%";\n    renderer.drawText(SMALL_FONT_ID, rect.x + batteryPercentSpacing + rect.width, rect.y, percentageText.c_str());\n  }\n\n  const Rect iconRect{rect.x, y, rect.width, rect.height};\n  drawBatteryOutline(renderer, rect.x, y, rect.width, rect.height);\n  fillBatteryIcon(renderer, iconRect, percentage);\n}\n''',
    '''void BaseTheme::drawBatteryLeft(const GfxRenderer& renderer, Rect rect, const bool showPercentage) const {\n  if (!showPercentage) return;\n  const uint16_t percentage = powerManager.getBatteryPercentage();\n  const auto percentageText = std::to_string(percentage) + "%";\n  renderer.drawText(SMALL_FONT_ID, rect.x, rect.y, percentageText.c_str());\n}\n''',
)
replace_required(
    "src/components/themes/BaseTheme.cpp",
    '''  // The icon glyph extends 2px past glyphWidth (terminal nub); reserve it or\n  // the percent label's rect comes up short and the text truncates.\n  constexpr int16_t batteryNubWidth = 2;\n  int16_t batteryReserve = static_cast<int16_t>(metrics.batteryWidth + batteryNubWidth);\n  if (showBatteryPercentage) {\n    batteryReserve = static_cast<int16_t>(\n        batteryReserve + batteryPercentSpacing +\n        ui.target.measureText(fui::GfxRendererTarget::FONT_SMALL, percentText, tokens.smallText).width);\n  }\n''',
    '''  int16_t batteryReserve = 0;\n  if (showBatteryPercentage) {\n    batteryReserve = static_cast<int16_t>(\n        ui.target.measureText(fui::GfxRendererTarget::FONT_SMALL, percentText, tokens.smallText).width);\n  }\n''',
)
replace_required(
    "src/components/themes/BaseTheme.cpp",
    '''  const int16_t batteryH = static_cast<int16_t>(metrics.batteryBarHeight);\n  const bool roundedRaffSettingsHeader =\n      static_cast<CrossPointSettings::UI_THEME>(SETTINGS.uiTheme) == CrossPointSettings::UI_THEME::ROUNDEDRAFF &&\n      title != nullptr && strcmp(title, tr(STR_SETTINGS_TITLE)) == 0;\n  const int16_t batteryY = static_cast<int16_t>(band.y + (roundedRaffSettingsHeader ? 8 : 0));\n  fui::batteryIndicator(ui.frame, fui::Rect{batteryX, batteryY, batteryReserve, batteryH}, battery);\n''',
    '''  const bool roundedRaffSettingsHeader =\n      static_cast<CrossPointSettings::UI_THEME>(SETTINGS.uiTheme) == CrossPointSettings::UI_THEME::ROUNDEDRAFF &&\n      title != nullptr && strcmp(title, tr(STR_SETTINGS_TITLE)) == 0;\n  const int16_t batteryY = static_cast<int16_t>(band.y + (roundedRaffSettingsHeader ? 8 : 0));\n  if (showBatteryPercentage) {\n    renderer.drawText(SMALL_FONT_ID, batteryX, batteryY, percentText);\n  }\n''',
)

print("Hungarian RC cleanup preparation complete")
