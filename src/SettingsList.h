#pragma once

#define getSettingsList getSettingsListBase
#include "SettingsListBase.h"
#undef getSettingsList

inline std::vector<SettingInfo> getSettingsList(const SdCardFontRegistry* registry = nullptr,
                                                const std::vector<DictionaryEntry>* dictionaries = nullptr) {
  if (SETTINGS.sleepScreenCoverFilter > 2) {
    SETTINGS.sleepScreenCoverFilter = 0;
  }
  return getSettingsListBase(registry, dictionaries);
}
