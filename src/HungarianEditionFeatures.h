#pragma once

#include <cstdint>

#include "CrossPointSettings.h"

namespace HungarianEditionFeatures {
constexpr uint8_t PICTURE_FILTER_MASK = 0x03;
constexpr uint8_t SCREENSHOT_MASK = 0x04;
constexpr uint8_t COVER_FILTER_BRIGHTER_10 = 3;
constexpr uint8_t COVER_FILTER_BRIGHTER_20 = 4;

enum PictureFilter : uint8_t { NONE = 0, BRIGHTER_10 = 1, BRIGHTER_20 = 2 };

inline uint8_t pictureFilter() { return SETTINGS.frontButtonLayout & PICTURE_FILTER_MASK; }
inline void setPictureFilter(uint8_t value) {
  SETTINGS.frontButtonLayout =
      static_cast<uint8_t>((SETTINGS.frontButtonLayout & ~PICTURE_FILTER_MASK) | (value & PICTURE_FILTER_MASK));
}
inline bool longDownScreenshot() { return (SETTINGS.frontButtonLayout & SCREENSHOT_MASK) != 0; }
inline void setLongDownScreenshot(bool enabled) {
  if (enabled) {
    SETTINGS.frontButtonLayout |= SCREENSHOT_MASK;
  } else {
    SETTINGS.frontButtonLayout &= static_cast<uint8_t>(~SCREENSHOT_MASK);
  }
}

inline uint8_t brightnessPercentForPicture() {
  return pictureFilter() == BRIGHTER_10 ? 10 : pictureFilter() == BRIGHTER_20 ? 20 : 0;
}
inline uint8_t brightnessPercentForCover() {
  return SETTINGS.sleepScreenCoverFilter == COVER_FILTER_BRIGHTER_10
             ? 10
             : SETTINGS.sleepScreenCoverFilter == COVER_FILTER_BRIGHTER_20 ? 20 : 0;
}
}  // namespace HungarianEditionFeatures
