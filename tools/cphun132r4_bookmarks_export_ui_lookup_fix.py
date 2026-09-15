from pathlib import Path


def replace_once(path, old, new):
    p = Path(path)
    text = p.read_text(encoding="utf-8")
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"CPHUN-132r4: {path}: expected one match, found {count}: {old[:160]!r}")
    p.write_text(text.replace(old, new, 1), encoding="utf-8")


def replace_visible_text(root, old, new):
    count = 0
    for p in Path(root).rglob("*"):
        if p.suffix not in {".cpp", ".h", ".yaml", ".yml"} or not p.is_file():
            continue
        text = p.read_text(encoding="utf-8")
        if old in text:
            occurrences = text.count(old)
            p.write_text(text.replace(old, new), encoding="utf-8")
            count += occurrences
    return count


# -----------------------------------------------------------------------------
# 1) Hungarian UI terminology and Reader menu layout
# -----------------------------------------------------------------------------
# The no-result prompt gets the approved wording first, before the shorter label replacement.
replace_visible_text("src", "A kijelölt szó kiemelhető.", "A választott szó megjelölhető.")
replaced_highlight = replace_visible_text("src", "Kiemelés", "Megjelölés")
if replaced_highlight < 3:
    raise SystemExit(f"CPHUN-132r4: expected generated Kiemelés UI strings, replaced only {replaced_highlight}")

# Keep internal Highlight* identifiers; only visible text changes.
# Move Megjelölés directly under Könyvjelző jelölés, before dictionary search.
replace_once(
    "src/activities/reader/EpubReaderMenuActivity.cpp",
    '''  items.push_back({MenuAction::TOGGLE_BOOKMARK, StrId::STR_TOGGLE_BOOKMARK});
  items.push_back({MenuAction::DICTIONARY, StrId::STR_LOOKUP, "Szótári keresés"});
  items.push_back({MenuAction::HIGHLIGHT, StrId::STR_LOOKUP, "Megjelölés"});
  items.push_back({MenuAction::MANUAL_DICTIONARY_SEARCH, StrId::STR_LOOKUP, "Kézi keresés"});''',
    '''  items.push_back({MenuAction::TOGGLE_BOOKMARK, StrId::STR_TOGGLE_BOOKMARK});
  items.push_back({MenuAction::HIGHLIGHT, StrId::STR_LOOKUP, "Megjelölés"});
  items.push_back({MenuAction::DICTIONARY, StrId::STR_LOOKUP, "Szótári keresés"});
  items.push_back({MenuAction::MANUAL_DICTIONARY_SEARCH, StrId::STR_LOOKUP, "Kézi keresés"});''',
)

# Move Képernyő nézet from Olvasás to Könyv, immediately after Borító megjelenítése.
replace_once(
    "src/activities/reader/EpubReaderMenuActivity.cpp",
    '  items.push_back({MenuAction::ROTATE_SCREEN, StrId::STR_ORIENTATION});\n',
    '',
)
replace_once(
    "src/activities/reader/EpubReaderMenuActivity.cpp",
    '      {MenuAction::BOOK_COVER, StrId::STR_TEXT_SETTINGS, "Borító megjelenítése"},\n',
    '      {MenuAction::BOOK_COVER, StrId::STR_TEXT_SETTINGS, "Borító megjelenítése"},\n'
    '      {MenuAction::ROTATE_SCREEN, StrId::STR_ORIENTATION},\n',
)

# Make both Reader tabs 2 px denser without changing global list metrics.
replace_once(
    "src/activities/reader/EpubReaderMenuActivity.cpp",
    "  syncTabListViewport(screen, props);\n",
    '''  const int16_t compactRowHeight = static_cast<int16_t>(metrics.listRowHeight - 2);
  syncTabListViewport(screen, props, false, compactRowHeight);
''',
)

# Shorten the visible Hungarian settings label wherever the patch chain generated it.
shortened = replace_visible_text("src", "Szótár beállítása", "Szótár:")
shortened += replace_visible_text("lib/I18n", "Szótár beállítása", "Szótár:")
if shortened == 0:
    print("CPHUN-132r4: note: no literal 'Szótár beállítása' generated in src/lib; label may already be shortened")

# -----------------------------------------------------------------------------
# 2) Merge marked words into Bookmarks list and add simple numbered TXT export
# -----------------------------------------------------------------------------
Path("src/activities/reader/EpubReaderBookmarksActivity.h").write_text(r'''#pragma once
#include <Epub.h>

#include <memory>
#include <string>
#include <vector>

#include "../../BookmarkEntry.h"
#include "activities/UiListActivity.h"
#include "components/OptionPopup.h"
#include "highlights/HighlightStore.h"

class EpubReaderBookmarksActivity final : public UiListActivity {
  enum class RowKind : uint8_t { Bookmark, Highlight, Export };
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
  std::string exportStatus;
  void rebuildRows();
  bool exportMarkedWords();
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
''', encoding="utf-8")

Path("src/activities/reader/EpubReaderBookmarksActivity.cpp").write_text(r'''#include "EpubReaderBookmarksActivity.h"

#include <FsHelpers.h>
#include <GfxRenderer.h>
#include <HalStorage.h>
#include <I18n.h>
#include <Logging.h>

#include <algorithm>
#include <cstdio>

#include "../../util/BookmarkFile.h"
#include "MappedInputManager.h"
#include "components/UITheme.h"
#include "components/UiAppHelpers.h"
#include "fontIds.h"

namespace fui = freeink::ui;

namespace {
constexpr int ENTER_DELETE_MODE_MS = 700;
constexpr char EXPORT_ROOT[] = "/exports";
}

EpubReaderBookmarksActivity::EpubReaderBookmarksActivity(GfxRenderer& renderer, MappedInputManager& mappedInput,
                                                         const std::shared_ptr<Epub>& epub, const std::string& epubPath)
    : UiListActivity("EpubReaderBookmarks", renderer, mappedInput, /*wantsTouchLongPress=*/true),
      epub(epub), epubPath(epubPath) {}

void EpubReaderBookmarksActivity::onEnter() {
  UiListActivity::onEnter();
  if (!epub) return;
  if (!BookmarkFile::load(epubPath, bookmarks)) bookmarks.shrink_to_fit();
  highlightStore = std::make_unique<HighlightStore>(epubPath);
  if (!highlightStore->load()) LOG_ERR("EPB", "Failed to load marked words for %s", epubPath.c_str());
  rebuildRows();
}

void EpubReaderBookmarksActivity::rebuildRows() {
  rows.clear(); rowLabels.clear(); rowSubtitles.clear(); rowItems.clear();
  if (!epub) return;
  const size_t highlightCount = highlightStore ? highlightStore->items().size() : 0;
  const size_t total = bookmarks.size() + highlightCount + (highlightCount ? 1 : 0);
  rows.reserve(total); rowLabels.reserve(total); rowSubtitles.reserve(total); rowItems.reserve(total);

  for (size_t i = 0; i < bookmarks.size(); ++i) {
    const auto& bookmark = bookmarks[i];
    rows.push_back({RowKind::Bookmark, i});
    rowLabels.push_back(bookmark.summary);
    const auto tocIndex = epub->getTocIndexForSpineIndex(bookmark.computedSpineIndex);
    const auto tocTitle = (tocIndex >= 0) ? epub->getTocItem(tocIndex).title : tr(STR_UNNAMED);
    std::string subtitle = std::to_string((int)(std::clamp(bookmark.percentage, 0.0f, 1.0f) * 100.0f + 0.5f)) + "% - ";
    if (bookmark.computedChapterPageCount > 0) {
      subtitle += std::to_string(bookmark.computedChapterProgress + 1) + "/" +
                  std::to_string(bookmark.computedChapterPageCount) + " - ";
    }
    subtitle += tocTitle;
    rowSubtitles.push_back(std::move(subtitle));
  }

  if (highlightStore) {
    const auto& highlights = highlightStore->items();
    for (size_t i = 0; i < highlights.size(); ++i) {
      rows.push_back({RowKind::Highlight, i});
      rowLabels.push_back(highlights[i].text);
      const auto tocIndex = epub->getTocIndexForSpineIndex(highlights[i].spineIndex);
      const std::string tocTitle = (tocIndex >= 0) ? epub->getTocItem(tocIndex).title : tr(STR_UNNAMED);
      rowSubtitles.push_back(std::string("Megjelölés - ") + tocTitle);
    }
    if (!highlights.empty()) {
      rows.push_back({RowKind::Export, 0});
      rowLabels.push_back("Megjelölt szavak mentése");
      rowSubtitles.push_back(exportStatus.empty() ? "TXT" : exportStatus);
    }
  }

  for (size_t i = 0; i < rows.size(); ++i) {
    fui::ListItem item;
    item.label = rowLabels[i].c_str();
    item.subtitle = rowSubtitles[i].c_str();
    item.icon = listIconFor(UIIcon::Bookmark, 32);
    item.actionValue = static_cast<int16_t>(i);
    rowItems.push_back(item);
  }
}

bool EpubReaderBookmarksActivity::exportMarkedWords() {
  if (!epub || !highlightStore || highlightStore->items().empty()) return false;
  char title[64];
  FsHelpers::sanitizePathComponentForFat32(epub->getTitle().c_str(), title, sizeof(title));
  if (title[0] == '\0') snprintf(title, sizeof(title), "konyv");
  if (!Storage.exists(EXPORT_ROOT) && !Storage.mkdir(EXPORT_ROOT)) return false;
  const std::string dir = std::string(EXPORT_ROOT) + "/" + title;
  if (!Storage.exists(dir.c_str()) && !Storage.mkdir(dir.c_str())) return false;

  char path[256];
  int seq = 1;
  for (; seq <= 999; ++seq) {
    snprintf(path, sizeof(path), "%s/megjelolt_szavak_%03d.txt", dir.c_str(), seq);
    if (!Storage.exists(path)) break;
  }
  if (seq > 999) return false;

  HalFile out;
  if (!Storage.openFileForWrite("EPB", path, out)) return false;
  bool ok = true;
  for (const auto& mark : highlightStore->items()) {
    if (mark.text.empty()) continue;
    if (out.write(reinterpret_cast<const uint8_t*>(mark.text.data()), mark.text.size()) !=
        static_cast<int>(mark.text.size()) || out.write(reinterpret_cast<const uint8_t*>("\n"), 1) != 1) {
      ok = false;
      break;
    }
  }
  out.close();
  if (!ok) { Storage.remove(path); return false; }
  exportStatus = std::string("Elmentve: ") + std::to_string(seq);
  LOG_INF("EPB", "Marked words exported to %s", path);
  return true;
}

void EpubReaderBookmarksActivity::openSelectedItem() {
  if (rows.empty() || nav.selected < 0 || nav.selected >= static_cast<int>(rows.size())) return;
  const RowRef row = rows[nav.selected];
  if (row.kind == RowKind::Export) {
    exportStatus = exportMarkedWords() ? exportStatus : "Mentési hiba";
    rebuildRows(); requestUpdate(true); return;
  }
  ProgressChangeResult result{};
  if (row.kind == RowKind::Bookmark) {
    const auto& bookmark = bookmarks.at(row.index);
    result.xpath = bookmark.xpath; result.percentage = bookmark.percentage; result.hasSavedProgress = true;
    result.hasVisibleTextOffset = bookmark.hasVisibleTextOffset; result.visibleTextOffset = bookmark.visibleTextOffset;
    result.spineIndex = bookmark.computedSpineIndex;
    if (bookmark.computedChapterPageCount > 0 && bookmark.computedChapterProgress < bookmark.computedChapterPageCount &&
        bookmark.computedSpineIndex < epub->getSpineItemsCount()) {
      result.page = bookmark.computedChapterProgress; result.totalPages = bookmark.computedChapterPageCount;
    }
  } else {
    const auto& mark = highlightStore->items().at(row.index);
    result.spineIndex = mark.spineIndex;
    result.hasSavedProgress = true;
    result.hasVisibleTextOffset = true;
    result.visibleTextOffset = mark.visibleTextOffset;
    result.percentage = epub->calculateProgress(mark.spineIndex, 0.0f);
  }
  setResult(std::move(result)); finish();
}

void EpubReaderBookmarksActivity::activateIndex(const int index) {
  if (confirmPopup.isActive() || index < 0 || index >= listCount()) return;
  app.clearTapFlash(); nav.selected = index; openSelectedItem();
}

void EpubReaderBookmarksActivity::onRowLongPress(const int index) {
  if (confirmPopup.isActive() || index < 0 || index >= listCount()) return;
  if (rows[index].kind == RowKind::Export) return;
  app.clearTapFlash(); nav.selected = index; showDeleteConfirmation();
}

bool EpubReaderBookmarksActivity::handleCustomInput() {
  if (confirmPopup.handleInput(mappedInput, [this] { requestUpdate(); })) return true;
  if (confirmingDelete) { confirmingDelete = false; requestUpdate(); return true; }
  return false;
}

bool EpubReaderBookmarksActivity::handleButtons() {
  if (mappedInput.wasReleased(MappedInputManager::Button::Back)) {
    ActivityResult result; result.isCancelled = true; setResult(std::move(result)); finish(); return true;
  }
  if (mappedInput.wasReleased(MappedInputManager::Button::Confirm)) {
    if (mappedInput.getHeldTime() > ENTER_DELETE_MODE_MS && !rows.empty() && rows[nav.selected].kind != RowKind::Export)
      showDeleteConfirmation();
    else openSelectedItem();
    return true;
  }
  return false;
}

void EpubReaderBookmarksActivity::showDeleteConfirmation() {
  if (rows.empty() || confirmPopup.isActive()) return;
  const RowRef row = rows[nav.selected];
  if (row.kind == RowKind::Export) return;
  confirmingDelete = true;
  const char* options[] = {tr(STR_CANCEL), tr(STR_DELETE)};
  const char* title = row.kind == RowKind::Highlight ? "Megjelölés törlése?" : tr(STR_CONFIRM_DELETE_BOOKMARK);
  confirmPopup.show(title, options, 2, 0, [this](int idx) {
    confirmingDelete = false;
    if (idx == 1) deleteSelectedItem();
    requestUpdate();
  });
  requestUpdate();
}

void EpubReaderBookmarksActivity::deleteSelectedItem() {
  if (rows.empty()) return;
  const RowRef row = rows[nav.selected];
  if (row.kind == RowKind::Bookmark) {
    bookmarks.erase(bookmarks.begin() + row.index);
    if (!BookmarkFile::save(epubPath, bookmarks)) LOG_ERR("EPB", "Failed to save bookmarks after delete");
  } else if (row.kind == RowKind::Highlight && highlightStore) {
    const HighlightAnchor mark = highlightStore->items().at(row.index);
    if (!highlightStore->remove(mark)) LOG_ERR("EPB", "Failed to remove marked word");
  }
  rebuildRows();
  if (nav.selected >= static_cast<int>(rows.size()) && nav.selected > 0) nav.selected--;
  nav.follow(listCount()); requestUpdate(true);
}

void EpubReaderBookmarksActivity::buildScreen(UiScreen& screen) {
  const auto& metrics = UITheme::getInstance().getMetrics();
  const Rect safe = UITheme::getInstance().getScreenSafeArea(renderer, true, false);
  screen.setContentMargin(fui::Insets{static_cast<int16_t>(safe.y + metrics.topPadding + metrics.headerHeight),
                                      static_cast<int16_t>(renderer.getScreenWidth() - (safe.x + safe.width)),
                                      static_cast<int16_t>(renderer.getScreenHeight() - (safe.y + safe.height)),
                                      static_cast<int16_t>(safe.x)});
  screen.spacer(static_cast<int16_t>(metrics.verticalSpacing));
  if (rows.empty()) { screen.centeredText(tr(STR_NO_BOOKMARKS), screen.theme().bodyText); return; }
  if (!mappedInput.hasTouch()) {
    const int helpLineHeight = renderer.getLineHeight(SMALL_FONT_ID);
    const fui::Rect band = screen.takeBottom(static_cast<int16_t>(helpLineHeight + metrics.verticalSpacing));
    GUI.drawHelpText(renderer, Rect{band.x, band.y + metrics.verticalSpacing, band.width, helpLineHeight},
                     tr(STR_HOLD_OPEN_TO_DELETE));
  }
  fui::ListProps props; props.items = rowItems.data(); props.count = static_cast<uint16_t>(rowItems.size());
  props.action = ACTION_ROW; props.inputMask = fui::InputTouch | fui::InputLongPress;
  syncListViewport(screen, props, /*hasSubtitle=*/true); screen.list(props);
}

void EpubReaderBookmarksActivity::render(RenderLock&&) {
  renderer.clearScreen();
  const auto pageWidth = renderer.getScreenWidth(); const auto orientation = renderer.getOrientation();
  const bool cw = orientation == GfxRenderer::Orientation::LandscapeClockwise;
  const bool ccw = orientation == GfxRenderer::Orientation::LandscapeCounterClockwise;
  const bool inv = orientation == GfxRenderer::Orientation::PortraitInverted;
  const int gutter = (cw || ccw) ? 40 : 0; const int contentX = cw ? gutter : 0;
  const int contentWidth = pageWidth - gutter; const int contentY = inv ? 50 : 0;
  const int titleX = contentX + (contentWidth - renderer.getTextWidth(UI_12_FONT_ID, tr(STR_BOOKMARKS), EpdFontFamily::BOLD)) / 2;
  renderer.drawText(UI_12_FONT_ID, titleX, 15 + contentY, tr(STR_BOOKMARKS), true, EpdFontFamily::BOLD);
  renderUi();
  if (confirmPopup.processRender(renderer, mappedInput)) return;
  const auto labels = mappedInput.mapLabels(tr(STR_BACK), rows.empty() ? "" : tr(STR_SELECT), tr(STR_DIR_UP), tr(STR_DIR_DOWN));
  GUI.drawButtonHints(renderer, labels.btn1, labels.btn2, labels.btn3, labels.btn4);
  renderer.displayBuffer();
}
''', encoding="utf-8")

# Make the combined list visible even when a book has marks but no classic bookmark.
replace_once(
    "src/activities/reader/EpubReaderActivity.cpp",
    "                             SETTINGS.orientation, !currentPageFootnotes.empty(), !cachedBookmarks.empty(), startOnBookTab),\n",
    "                             SETTINGS.orientation, !currentPageFootnotes.empty(),\n"
    "                             !cachedBookmarks.empty() || (highlightStore && !highlightStore->items().empty()), startOnBookTab),\n",
)

# -----------------------------------------------------------------------------
# 3) Stop a corrupted/unreadable sidecar from degenerating into a huge scan.
#    Bound the inner index/synonym scans too, not only the outer stem loop.
# -----------------------------------------------------------------------------
replace_once(
    "src/util/Dictionary.cpp",
    '''    if (!readSampleOffset(sidecar, mid, &offset) || !source.seekSet(offset) ||
        readWordInto(source, wordBuf, sizeof(wordBuf)) < 0) {
      lo = 0;  // unreadable sample: abandon the descent and scan from the start
      break;
    }''',
    '''    if (!readSampleOffset(sidecar, mid, &offset) || !source.seekSet(offset) ||
        readWordInto(source, wordBuf, sizeof(wordBuf)) < 0) {
      return UINT32_MAX;  // unreadable sample: never fall back to an unbounded scan from byte 0
    }''',
)
replace_once(
    "src/util/Dictionary.cpp",
    '''  readSampleOffset(sidecar, lo, &startByte);
  return startByte;''',
    '''  if (!readSampleOffset(sidecar, lo, &startByte)) return UINT32_MAX;
  return startByte;''',
)
replace_once(
    "src/util/Dictionary.cpp",
    '''  const uint32_t startByte = bisectSamples(session.qidx, session.idx, session.sampleCount, target);

  // Linear scan''',
    '''  const uint32_t startByte = bisectSamples(session.qidx, session.idx, session.sampleCount, target);
  if (startByte == UINT32_MAX) { result.readError = true; return result; }
  const unsigned long locateStart = millis();
  size_t locateProbes = 0;

  // Linear scan''',
)
replace_once(
    "src/util/Dictionary.cpp",
    '''  while (static_cast<uint32_t>(session.idx.position()) < session.idxSize) {
    if (readWordInto(session.idx, wordBuf, sizeof(wordBuf)) < 0) {''',
    '''  while (static_cast<uint32_t>(session.idx.position()) < session.idxSize) {
    if (++locateProbes > SAMPLE_INTERVAL + 8 || millis() - locateStart > 1500) {
      result.readError = true;
      break;
    }
    if (readWordInto(session.idx, wordBuf, sizeof(wordBuf)) < 0) {''',
)
replace_once(
    "src/util/Dictionary.cpp",
    '''  const uint32_t startByte = bisectSamples(session.sidx, session.syn, session.synSampleCount, target);

  // Linear scan''',
    '''  const uint32_t startByte = bisectSamples(session.sidx, session.syn, session.synSampleCount, target);
  if (startByte == UINT32_MAX) { result.readError = true; return result; }
  const unsigned long synonymStart = millis();
  size_t synonymProbes = 0;

  // Linear scan''',
)
replace_once(
    "src/util/Dictionary.cpp",
    '''  while (static_cast<uint32_t>(session.syn.position()) < session.synSize) {
    if (readWordInto(session.syn, wordBuf, sizeof(wordBuf)) < 0) break;''',
    '''  while (static_cast<uint32_t>(session.syn.position()) < session.synSize) {
    if (++synonymProbes > SAMPLE_INTERVAL + 8 || millis() - synonymStart > 1500) {
      result.readError = true;
      break;
    }
    if (readWordInto(session.syn, wordBuf, sizeof(wordBuf)) < 0) break;''',
)

print("CPHUN-132r4 bookmarks/marked words, TXT export, UI compaction and lookup guard patch applied")
