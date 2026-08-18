#pragma once

#include "activities/Activity.h"

class CrossPointVersionActivity final : public Activity {
 public:
  explicit CrossPointVersionActivity(GfxRenderer& renderer, MappedInputManager& mappedInput)
      : Activity("CrossPointVersion", renderer, mappedInput) {}

  void onEnter() override;
  void loop() override;
  void render(RenderLock&&) override;
};
