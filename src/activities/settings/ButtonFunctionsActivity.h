#pragma once

#include <string>
#include <vector>

#include "ReaderAction.h"
#include "ReaderButtonProfile.h"
#include "activities/UiListActivity.h"
#include "components/OptionPopup.h"

class ButtonFunctionsActivity final : public UiListActivity {
 public:
  ButtonFunctionsActivity(GfxRenderer& renderer, MappedInputManager& mappedInput);
  void onEnter() override;

 protected:
  int listCount() const override { return 12; }
  void buildScreen(UiScreen& screen) override;
  void activateIndex(int index) override;
  bool handleCustomInput() override;
  const char* headerTitle() const override;
  void drawFooter() override;

 private:
  static ReaderPhysicalButton buttonForRow(int row);
  static ReaderButtonGesture gestureForRow(int row);
  static const char* actionLabel(ReaderAction action);
  void rebuildRows();
  void openActionPicker(int row);

  OptionPopup optionPopup_;
  std::vector<std::string> labels_;
  std::vector<std::string> values_;
  std::vector<freeink::ui::ListItem> rows_;
};
