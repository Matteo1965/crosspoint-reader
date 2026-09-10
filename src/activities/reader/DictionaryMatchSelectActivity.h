#pragma once

#include <string>
#include <vector>

#include "activities/UiListActivity.h"

class DictionaryMatchSelectActivity final : public UiListActivity {
 public:
  DictionaryMatchSelectActivity(GfxRenderer& renderer, MappedInputManager& mappedInput,
                                std::vector<std::string> headwords);

 private:
  int listCount() const override { return static_cast<int>(headwords.size()); }
  void buildScreen(UiScreen& screen) override;
  void activateIndex(int index) override;
  const char* headerTitle() const override { return "Szótári találatok"; }

  std::vector<std::string> headwords;
  std::vector<freeink::ui::ListItem> rows;
};
