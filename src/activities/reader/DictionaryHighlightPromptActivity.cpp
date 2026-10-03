#include "DictionaryHighlightPromptActivity.h"

#include <GfxRenderer.h>

#include "MappedInputManager.h"
#include "components/UITheme.h"
#include "fontIds.h"

void DictionaryHighlightPromptActivity::onEnter() {
  Activity::onEnter();
  requestUpdate();
}

void DictionaryHighlightPromptActivity::loop() {
  if (mappedInput.wasReleased(MappedInputManager::Button::Back)) {
    ActivityResult result;
    result.isCancelled = true;
    setResult(std::move(result));
    finish();
    return;
  }
  if (mappedInput.wasReleased(MappedInputManager::Button::Confirm)) {
    setResult(highlight);
    finish();
  }
}

void DictionaryHighlightPromptActivity::render(RenderLock&&) {
  renderer.clearScreen();
  const int centerY = renderer.getScreenHeight() / 2 - 25;
  renderer.drawCenteredText(NOTOSANS_14_FONT_ID, centerY, firstLine.c_str(), true, EpdFontFamily::REGULAR);
  renderer.drawCenteredText(NOTOSANS_14_FONT_ID, centerY + 34, "A választott szó megjelölhető.", true,
                            EpdFontFamily::REGULAR);
  const auto labels = mappedInput.mapLabels("Vissza", "Megjelölés", "", "");
  GUI.drawButtonHints(renderer, labels.btn1, labels.btn2, labels.btn3, labels.btn4);
  renderer.displayBuffer(HalDisplay::FAST_REFRESH);
}
