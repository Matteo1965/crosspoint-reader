#include "CrossPointVersionActivity.h"

#include <GfxRenderer.h>
#include <I18n.h>

#include <string>

#include "MappedInputManager.h"
#include "components/UITheme.h"
#include "fontIds.h"

void CrossPointVersionActivity::onEnter() {
  Activity::onEnter();
  requestUpdate();
}

void CrossPointVersionActivity::loop() {
  int x = 0;
  int y = 0;
  if (mappedInput.wasPressed(MappedInputManager::Button::Back) || mappedInput.wasScreenTapped(x, y)) {
    finish();
  }
}

void CrossPointVersionActivity::render(RenderLock&&) {
  renderer.clearScreen();

  const auto& metrics = UITheme::getInstance().getMetrics();
  const int pageWidth = renderer.getScreenWidth();
  GUI.drawHeader(renderer, Rect{0, metrics.topPadding, pageWidth, metrics.headerHeight}, tr(STR_CROSSPOINT_VERSION));

  const int x = metrics.horizontalMargin;
  int y = metrics.topPadding + metrics.headerHeight + metrics.verticalSpacing;
  const int lineHeight = renderer.getLineHeight(UI_10_FONT_ID);

  const auto drawLabelValue = [&](const char* label, const char* value) {
    const std::string line = std::string(label) + ": " + value;
    renderer.drawText(UI_10_FONT_ID, x, y, line.c_str());
    y += lineHeight;
  };

  drawLabelValue(tr(STR_CROSSPOINT_VERSION), CROSSPOINT_VERSION);
  drawLabelValue(tr(STR_BASE_VERSION), "1.5.0");
  drawLabelValue(tr(STR_EDITION), "Hungarian Edition");
  const std::string buildDate = std::string(__DATE__) + " " + __TIME__;
  drawLabelValue(tr(STR_BUILD_DATE), buildDate.c_str());

  y += lineHeight;
  renderer.drawText(UI_10_FONT_ID, x, y, tr(STR_DIFFERENCES_FROM_BASE), true, EpdFontFamily::BOLD);
  y += lineHeight;

  const StrId features[] = {STR_FEATURE_HUNGARIAN_UI, STR_FEATURE_HUNGARIAN_HYPHENATION,
                            STR_FEATURE_HUNGARIAN_STEMMING, STR_FEATURE_DICTIONARY_DISPLAY};
  for (const StrId feature : features) {
    const std::string line = std::string("- ") + tr(feature);
    renderer.drawText(UI_10_FONT_ID, x, y, line.c_str());
    y += lineHeight;
  }

  const auto labels = mappedInput.mapLabels(tr(STR_BACK), "", "", "");
  GUI.drawButtonHints(renderer, labels.btn1, labels.btn2, labels.btn3, labels.btn4);
  renderer.displayBuffer();
}
