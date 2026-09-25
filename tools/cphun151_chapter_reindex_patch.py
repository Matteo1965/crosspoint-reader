"""CPHUN-151: explicit current-chapter reindex without leaving the book.

Applied after the complete CPHUN-150 build patch chain. The current chapter's
page cache alone is removed; the book and extracted HTML caches stay intact.
"""
from pathlib import Path


def replace_once(path, old, new, label):
    file = Path(path)
    data = file.read_text(encoding="utf-8")
    count = data.count(old)
    if count != 1:
        raise SystemExit(f"CPHUN-151 {label}: expected one anchor; got {count}")
    file.write_text(data.replace(old, new, 1), encoding="utf-8")


menu_h = "src/activities/reader/EpubReaderMenuActivity.h"
menu_cpp = "src/activities/reader/EpubReaderMenuActivity.cpp"
reader_h = "src/activities/reader/EpubReaderActivity.h"
reader_cpp = "src/activities/reader/EpubReaderActivity.cpp"

replace_once(
    menu_h,
    "    DELETE_CACHE,\n    DICTIONARY,",
    "    DELETE_CACHE,\n    REINDEX_CHAPTER,\n    DICTIONARY,",
    "new menu action",
)
replace_once(
    menu_cpp,
    "       {MenuAction::DELETE_CACHE, StrId::STR_DELETE_CACHE},\n",
    '       {MenuAction::DELETE_CACHE, StrId::STR_DELETE_CACHE},\n'
    '       {MenuAction::REINDEX_CHAPTER, StrId::STR_DELETE_CACHE, "Fejezet újraindexelése"},\n',
    "last item on Book tab",
)
replace_once(
    reader_h,
    "  bool buildPopupPending = false;\n",
    "  bool buildPopupPending = false;\n"
    "  bool forceChapterReindex = false;\n",
    "explicit full chapter rebuild flag",
)

# Keep already-cached visible-text position before removing the section.
# An in-progress build MUST be aborted, not suspended on destruction, otherwise
# its destructor could write back the partial .bin we just deleted.
# Section::clearCache() removes only this spine's .bin and .tmp file.
chapter_action = '''    case EpubReaderMenuActivity::MenuAction::REINDEX_CHAPTER: {
      if (!epub || currentSpineIndex < 0 || currentSpineIndex >= epub->getSpineItemsCount()) {
        break;
      }

      bool cleared = false;
      {
        RenderLock lock;
        if (section) {
          rememberCurrentContentOffset();
          cachedSpineIndex = currentSpineIndex;
          cachedChapterTotalPageCount = section->pageCount;
          nextPageNumber = section->currentPage;
          section->abandonBuild();
          cleared = section->clearCache();
          section.reset();
        } else {
          // A chapter may be temporarily unloaded when this action is invoked.
          Section chapterCache(epub, currentSpineIndex, renderer);
          cleared = chapterCache.clearCache();
        }

        if (cleared) {
          // Always rebuild the entire current chapter, even if the existing
          // HTML cache permits a very fast, normally invisible reflow.
          forceChapterReindex = true;
          buildPopupPending = false;
          pendingPercentJump = false;
        }
      }
      if (!cleared) {
        LOG_ERR("ERS", "CPHUN-151: failed to remove chapter page cache");
        showIndexBuildError();
        break;
      }

      LOG_INF("ERS", "CPHUN-151: reindexing current chapter %d", currentSpineIndex);
      requestUpdate();
      break;
    }
'''
replace_once(
    reader_cpp,
    "    case EpubReaderMenuActivity::MenuAction::DELETE_CACHE: {",
    chapter_action + "    case EpubReaderMenuActivity::MenuAction::DELETE_CACHE: {",
    "chapter-only menu handler",
)

replace_once(
    reader_cpp,
    "      const bool needsFullBuild = pendingPercentJump;",
    "      const bool needsFullBuild = pendingPercentJump || forceChapterReindex;",
    "force complete chapter build",
)
replace_once(
    reader_cpp,
    '''        loan.end();
      } else {
        const int target = pendingPageJump.has_value()''',
    '''        loan.end();
        forceChapterReindex = false;
      } else {
        const int target = pendingPageJump.has_value()''',
    "clear the request only after successful complete build",
)

# No change to SECTION_FILE_VERSION: full and partial section formats are
# unchanged. Only current chapter's page cache is invalidated.
print("CPHUN-151 chapter-only reindex patch applied")
