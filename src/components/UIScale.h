#pragma once
#include "fontIds.h"
#include "CrossPointSettings.h"

// FreeInkUI font slots. Row heights, header height, and touch sizes are not
// chosen here: FreeInkApp derives all metric tokens from the body font's line
// height (themeTokensForLineHeight). One fixed tier for every board — the
// user-facing UI-scale setting was removed.
struct UIScaleSpec {
  int smallFontId;
  int bodyFontId;
  int titleFontId;
};

inline UIScaleSpec uiScaleSpec() {
  UIScaleSpec spec{};
#if FREEINK_DEVICE_PICCO
  if (SETTINGS.uiSize == CrossPointSettings::UI_SIZE_NORMAL) {
    spec.smallFontId = UI_12_FONT_ID;
    spec.bodyFontId = UI_14_FONT_ID;
    spec.titleFontId = UI_14_FONT_ID;
    return spec;
  }
#endif
  spec.smallFontId = UI_10_FONT_ID;
  spec.bodyFontId = UI_12_FONT_ID;
  // Titles use the UI font, not a reader font: fui headers draw book and
  // directory titles, and the built-in Ubuntu UI fonts cover Hebrew (plus the
  // size-matched SD CJK fallback) where the NotoSans reader subsets do not.
  spec.titleFontId = UI_12_FONT_ID;
  return spec;
}
