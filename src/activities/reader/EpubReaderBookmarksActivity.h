#pragma once
#include <Epub.h>

#include <memory>
#include <string>
#include <vector>

#include "../../BookmarkEntry.h"
#include "activities/UiListActivity.h"
#include "components/OptionPopup.h"
#include "highlights/HighlightStore.h"

class EpubReaderBookmarksActivity final : public UiListActivity {
  enum class RowKind : uint8_t { Bookmark, Highlight };
  struct RowRef {
    RowKind kind;
    size_t index;
  };

  std::shared_ptr<Epub> epub;
  std::string epubPath;
  std::vector<BookmarkEntry> bookmarks;
  std::unique_ptr<HighlightStore> highlightStore;
  std::vector<RowRef> rows;
  std::vector<std::string> rowLabels;
  std::vector<std::string> rowSubtitles;
  std::vector<freeink::ui::ListItem> rowItems;
  void rebuildRows();
  bool confirmingDelete = false;
  OptionPopup confirmPopup;

 public:
  explicit EpubReaderBookmarksActivity(GfxRenderer& renderer, MappedInputManager& mappedInput,
                                       const std::shared_ptr<Epub>& epub, const std::string& epubPath);
  void onEnter() override;
  void render(RenderLock&&) override;

 private:
  int listCount() const override { return static_cast<int>(rows.size()); }
  void buildScreen(UiScreen& screen) override;
  void activateIndex(int index) override;
  void onRowLongPress(int index) override;
  bool handleCustomInput() override;
  bool handleButtons() override;
  void openSelectedItem();
  void showDeleteConfirmation();
  void deleteSelectedItem();
};
