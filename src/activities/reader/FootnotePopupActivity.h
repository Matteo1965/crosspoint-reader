#pragma once

#include <string>
#include <vector>

#include "activities/Activity.h"

class FootnotePopupActivity final : public Activity {
 public:
  FootnotePopupActivity(GfxRenderer& renderer, MappedInputManager& mappedInput, std::string label, std::string text);

  void onEnter() override;
  void onExit() override;
  void loop() override;
  void render(RenderLock&&) override;
  bool appliesNightMode() const override { return true; }

 private:
  void wrapText();

  std::string label_;
  std::string text_;
  std::vector<std::string> lines_;
  int firstLine_ = 0;
};
