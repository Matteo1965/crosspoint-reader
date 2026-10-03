#pragma once

#include <string>

#include "activities/Activity.h"
#include "activities/ActivityResult.h"

class DictionaryHighlightPromptActivity final : public Activity {
 public:
  DictionaryHighlightPromptActivity(GfxRenderer& renderer, MappedInputManager& mappedInput,
                                    std::string firstLine, HighlightResult highlight)
      : Activity("DictionaryHighlightPrompt", renderer, mappedInput),
        firstLine(std::move(firstLine)),
        highlight(std::move(highlight)) {}

  void onEnter() override;
  void loop() override;
  void render(RenderLock&&) override;
  bool appliesNightMode() const override { return true; }

 private:
  std::string firstLine;
  HighlightResult highlight;
};
