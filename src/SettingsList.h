#pragma once

#define getSettingsList getSettingsListBase
#include "SettingsListBase.h"
#undef getSettingsList

#include "HungarianEditionFeatures.h"

inline std::vector<SettingInfo> getSettingsList(const SdCardFontRegistry* registry = nullptr,
                                                const std::vector<DictionaryEntry>* dictionaries = nullptr) {
  auto settings = getSettingsListBase(registry, dictionaries);

  // Extend the existing cover filter with two brightness modes. Values 0..2
  // keep their upstream meaning; 3 and 4 are Hungarian Edition extensions.
  for (auto& setting : settings) {
    if (setting.key && strcmp(setting.key, "sleepScreenCoverFilter") == 0) {
      setting.enumValues.push_back(StrId::STR_BRIGHTER_10);
      setting.enumValues.push_back(StrId::STR_BRIGHTER_20);
      break;
    }
  }

  // Picture filter is independent from the cover filter. The migration-only
  // frontButtonLayout byte stores the new RC feature bits, while the hidden raw
  // entry below makes the combined byte persist through the existing settings
  // serializer without enlarging CrossPointSettings.
  SettingInfo pictureFilter = SettingInfo::DynamicEnum(
      StrId::STR_PICTURE_FILTER,
      {StrId::STR_NONE_OPT, StrId::STR_BRIGHTER_10, StrId::STR_BRIGHTER_20},
      [] { return HungarianEditionFeatures::pictureFilter(); },
      [](uint8_t value) { HungarianEditionFeatures::setPictureFilter(value); }, "pictureFilter",
      StrId::STR_CAT_DISPLAY);

  auto displayEnd = std::find_if(settings.begin(), settings.end(), [](const SettingInfo& setting) {
    return setting.category != StrId::STR_CAT_DISPLAY;
  });
  settings.insert(displayEnd, std::move(pictureFilter));

  SettingInfo screenshot;
  screenshot.nameId = StrId::STR_LONG_DOWN_SCREENSHOT;
  screenshot.type = SettingType::TOGGLE;
  screenshot.key = "longDownScreenshot";
  screenshot.category = StrId::STR_CAT_CONTROLS;
  screenshot.valueGetter = [] { return HungarianEditionFeatures::longDownScreenshot() ? 1 : 0; };
  screenshot.valueSetter = [](uint8_t value) { HungarianEditionFeatures::setLongDownScreenshot(value != 0); };

  auto controlsEnd = settings.end();
  for (auto it = settings.begin(); it != settings.end(); ++it) {
    if (it->category == StrId::STR_CAT_CONTROLS) controlsEnd = std::next(it);
  }
  settings.insert(controlsEnd, std::move(screenshot));

  // Hidden raw persistence slot for the packed feature byte. Category NONE keeps
  // it out of the device UI while CrossPointSettings::toJson/fromJson sees it.
  settings.push_back(SettingInfo::Value(StrId::STR_NONE_OPT, &CrossPointSettings::frontButtonLayout, {0, 255, 1},
                                        "huFeatureBits", StrId::STR_NONE_OPT));
  return settings;
}
