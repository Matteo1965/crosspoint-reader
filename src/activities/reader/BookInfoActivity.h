#pragma once

#include <Epub.h>

#include <memory>
#include <string>
#include <vector>

#include "activities/UiTabListActivity.h"

class BookInfoActivity final : public UiTabListActivity {
 public:
  enum class Page : uint8_t { Description = 0, Metadata = 1 };

  BookInfoActivity(GfxRenderer& renderer, MappedInputManager& mappedInput, std::shared_ptr<Epub> epub, Page page);
  void onEnter() override;

 private:
  int tabCount() const override { return 1; }
  int activeTab() const override { return 0; }
  const char* tabLabel(int) const override { return ""; }
  int tabWidthPercent(int) const override { return 100; }
  void onTabAction(int) override {}
  void stepTab(int) override {}
  int listCount() const override { return static_cast<int>(rows_.size()); }
  void activateIndex(int) override {}
  bool handleButtons() override;
  void buildScreen(UiScreen& screen) override;
  void drawChrome() override;

  void rebuildRows();
  void addDescriptionRows(const std::string& text);
  void addMetadataRow(const char* label, const std::string& value);

  std::shared_ptr<Epub> epub_;
  Epub::BookInfo info_;
  Page page_;
  std::vector<std::string> rowText_;
  std::vector<freeink::ui::ListItem> rows_;
};
