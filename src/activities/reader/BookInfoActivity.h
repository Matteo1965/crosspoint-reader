#pragma once

#include <Epub.h>

#include <memory>
#include <string>
#include <vector>

#include "activities/UiTabListActivity.h"

class BookInfoActivity final : public UiTabListActivity {
 public:
  BookInfoActivity(GfxRenderer& renderer, MappedInputManager& mappedInput, std::shared_ptr<Epub> epub);
  void onEnter() override;

 private:
  enum class Tab : uint8_t { Description = 0, Metadata = 1, Cover = 2, Count = 3 };

  int tabCount() const override { return static_cast<int>(Tab::Count); }
  int activeTab() const override { return static_cast<int>(tab_); }
  const char* tabLabel(int index) const override;
  int tabWidthPercent(int index) const override;
  void onTabAction(int index) override;
  void stepTab(int direction) override;
  int listCount() const override { return static_cast<int>(rows_.size()); }
  void activateIndex(int index) override;
  bool handleButtons() override;
  void buildScreen(UiScreen& screen) override;
  void drawChrome() override;

  void rebuildRows();
  void addDescriptionRows(const std::string& text);
  void addMetadataRow(const char* label, const std::string& value);
  void openCover();

  std::shared_ptr<Epub> epub_;
  Epub::BookInfo info_;
  Tab tab_ = Tab::Description;
  std::vector<std::string> rowText_;
  std::vector<freeink::ui::ListItem> rows_;
  std::string coverPath_;
};
