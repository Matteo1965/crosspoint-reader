#pragma once

#include "activities/Activity.h"
#include "util/ButtonNavigator.h"

class CrossPointVersionActivity final : public Activity {
 public:
  explicit CrossPointVersionActivity(GfxRenderer& renderer, MappedInputManager& mappedInput)
      : Activity("CrossPointVersion", renderer, mappedInput) {}

  void onEnter() override;
  void loop() override;
  void render(RenderLock&&) override;

 private:
  int currentPage = 0;
  ButtonNavigator buttonNavigator;
};
