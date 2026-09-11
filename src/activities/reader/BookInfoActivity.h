#pragma once

#include <Epub.h>

#include <cstdint>
#include <memory>
#include <string>
#include <vector>

#include "activities/Activity.h"
#include "util/ButtonNavigator.h"

class BookInfoActivity final : public Activity {
 public:
  enum class Page : uint8_t { Description = 0, Metadata = 1 };

  BookInfoActivity(GfxRenderer& renderer, MappedInputManager& mappedInput, std::shared_ptr<Epub> epub, Page page);

  void onEnter() override;
  void onExit() override;
  void loop() override;
  void render(RenderLock&&) override;
  bool appliesNightMode() const override { return true; }

 private:
  struct Line {
    uint32_t start = 0;
    uint16_t len = 0;
    bool appendHyphen = false;
    bool justify = false;
    bool metadataFieldEnd = false;
  };

  void buildText();
  void wrapText();
  int measureSpan(const char* text, size_t len) const;
  void drawBody(int x, int startY, int maxWidth) const;

  std::shared_ptr<Epub> epub_;
  Epub::BookInfo info_;
  Page page_;
  std::string text_;
  std::vector<Line> lines_;
  int currentPage_ = 0;
  int totalPages_ = 1;
  std::vector<int> pageStarts_;
  ButtonNavigator buttonNavigator_;
};
