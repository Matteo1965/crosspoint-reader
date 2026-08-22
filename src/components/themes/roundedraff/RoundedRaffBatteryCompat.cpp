#include "RoundedRaffTheme.h"

#include <GfxRenderer.h>
#include <HalPowerManager.h>

#include <string>

#include "fontIds.h"

void drawBatteryRight(const GfxRenderer& renderer, const Rect rect, const bool showPercentage) {
  const uint16_t percentage = powerManager.getBatteryPercentage();

  BaseTheme::drawBatteryOutline(renderer, rect.x, rect.y, rect.width, rect.height);
  BaseTheme baseTheme;
  baseTheme.fillBatteryIcon(renderer, rect, percentage);

  if (showPercentage) {
    const std::string percentageText = std::to_string(percentage) + "%";
    const int textWidth = renderer.getTextWidth(SMALL_FONT_ID, percentageText.c_str());
    renderer.drawText(SMALL_FONT_ID, rect.x - BaseTheme::batteryPercentSpacing - textWidth, rect.y,
                      percentageText.c_str());
  }
}
