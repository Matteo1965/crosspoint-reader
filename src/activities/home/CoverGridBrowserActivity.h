#pragma once

#include <LibraryIndexFile.h>

#include <cstdint>
#include <memory>
#include <string>
#include <vector>

#include "activities/Activity.h"
#include "components/OptionPopup.h"

class Epub;
struct Rect;

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
  bool buildReadingShelves();
  uint16_t ordinalForActiveRow(int row);
  bool ensurePageThumbs();
  bool reopenAfterChild();
  void loadSelectedDetails();
  void clearSelectedDetails();

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
  void renderGrayscaleCovers();
  int hitGridCover(int x, int y) const;
  bool hitFeaturedCover(int x, int y) const;
  bool hitSortTab(int x, int y, int& tab) const;

  library::LibraryIndexFile index_;
  std::vector<GridBook> books_;
  int totalBooks_ = 0;
  int pageStart_ = 0;
  int selected_ = 0;
  int previewSelected_ = 0;
  int activeSortTab_ = 0;
  uint8_t descendingTabs_ = 3u;  // Recent/New start newest-first; Title/Author ascending.
  bool thumbnailsReady_ = false;
  bool thumbnailsLoading_ = false;
  int previousSelected_ = -1;
  bool selectionFastRefresh_ = false;
  int sidePageHoldAction_ = 0;  // -1=PageBack, +1=PageForward; consume release after long hold.
  int frontTabHoldAction_ = 0;  // -1=previous tab, +1=next tab; consume front-button release.
  bool backSortHoldActive_ = false;  // Consume Back release after long-hold sort reversal.
  std::vector<uint16_t> recentOrdinals_;
  std::vector<uint16_t> newOrdinals_;
  OptionPopup optionPopup_;
  int featuredProgressTenths_ = -1;
  int featuredCurrentPage_ = 0;
  int featuredTotalPages_ = 0;
  std::string featuredSeries_;
  std::string featuredChapterTitle_;
};
