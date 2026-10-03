#pragma once

#include <LibraryIndexFile.h>

#include <cstdint>
#include <memory>
#include <string>
#include <vector>

#include "activities/Activity.h"
#include "components/OptionPopup.h"

class Epub;

class CoverGridBrowserActivity final : public Activity {
 public:
  CoverGridBrowserActivity(GfxRenderer& renderer, MappedInputManager& mappedInput);

  void onEnter() override;
  void onExit() override;
  void loop() override;
  void render(RenderLock&&) override;

 private:
  struct GridBook {
    std::string path;
    std::string title;
    std::string author;
    std::string thumbPath;
  };

  static constexpr int PAGE_SIZE = 6;

  bool openIndex();
  bool rebuildIndex();
  bool loadPage();
  bool ensurePageThumbs();
  bool reopenAfterChild();

  library::SortOrder sortOrder() const;
  void selectSortTab(int tab, bool toggleIfActive);
  void toggleSortDirection();
  void stepSortTab(int delta);

  int totalBooks() const;
  int globalSelection() const;
  void moveSelection(int delta);
  void stepPage(int delta);

  void showSelectedOptions();
  void openSelectedBook();
  void openSelectedInfo(bool metadata);
  void openSelectedCover();
  std::shared_ptr<Epub> loadSelectedEpub();

  int thumbHeight() const;
  void paintCover(const GridBook& book, Rect rect, bool selectedFrame);
  int hitGridCover(int x, int y) const;
  bool hitFeaturedCover(int x, int y) const;
  bool hitSortTab(int x, int y, int& tab) const;

  library::LibraryIndexFile index_;
  std::vector<GridBook> books_;
  int pageStart_ = 0;
  int selected_ = 0;
  int activeSortTab_ = 0;
  uint8_t descendingTabs_ = 1u;  // Recent starts newest-first.
  bool thumbnailsReady_ = false;
  bool thumbnailsLoading_ = false;
  OptionPopup optionPopup_;
};
