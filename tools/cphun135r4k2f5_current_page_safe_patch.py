from pathlib import Path

# CPHUN-135r4k2f5 SAFE
# Restore footnote UI to current-page-only operation. This removes every
# interactive call to ensureBookFootnotes(), whose current-spine scan can
# exhaust X4 resources on books such as Michelangelo.
# Also write a low-risk index-miss diagnostic under /logfiles when the user
# invokes Footnotes but the rendered page has no indexed footnote entries.

p = Path("src/activities/reader/EpubReaderActivity.cpp")
s = p.read_text(encoding="utf-8")

# Never scan a spine while opening the Reader menu.
s = s.replace(
'''void EpubReaderActivity::openReaderMenu(const bool startOnBookTab) {
  pendingManualTurn = 0;
  ensureBookFootnotes();''',
'''void EpubReaderActivity::openReaderMenu(const bool startOnBookTab) {
  pendingManualTurn = 0;''',
1)

# Menu visibility: use only already-rendered current-page footnotes.
s = s.replace(
'''                             SETTINGS.orientation, !bookFootnotes.empty(), !cachedBookmarks.empty(), startOnBookTab),''',
'''                             SETTINGS.orientation, !currentPageFootnotes.empty(), !cachedBookmarks.empty(), startOnBookTab),''',
1)

old_case = '''    case EpubReaderMenuActivity::MenuAction::FOOTNOTES: {
      // CPHUN-135r4i: rebuild a bounded index for the CURRENT spine only.
      // Keep the current-page list as fallback for already parsed references.
      bookFootnotesIndexed = false;
      ensureBookFootnotes();
      if (!bookFootnotes.empty()) {
        openFootnotesList(true, true);
      } else {
        openFootnotesList(false, true);
      }
      break;
    }'''

new_case = '''    case EpubReaderMenuActivity::MenuAction::FOOTNOTES: {
      // CPHUN-135r4k2f5 SAFE: current-page data only. Do not start a
      // current-spine or whole-book XHTML scan from an interactive menu.
      if (currentPageFootnotes.empty()) {
        constexpr const char* LOG_DIR = "/logfiles";
        if (Storage.ensureDirectoryExists(LOG_DIR)) {
          const std::string path =
              std::string(LOG_DIR) + "/footnote_index_error_" + std::to_string(millis()) + ".txt";
          HalFile logFile;
          if (Storage.openFileForWrite("ERS", path, logFile)) {
            std::string log = "CrossPoint Footnote Index Diagnostic\\nFormat version: 1\\n\\n";
            log += std::string("Firmware: ") + CPHUN_BUILD_ID + "\\n";
            log += "Book: " + epub->getTitle() + "\\n";
            log += "EPUB: " + epub->getPath() + "\\n";
            log += "Source spine: " + std::to_string(currentSpineIndex) + "\\n";
            if (currentSpineIndex >= 0 && currentSpineIndex < epub->getSpineItemsCount()) {
              log += "Source XHTML: " + epub->getSpineItem(currentSpineIndex).href + "\\n";
            }
            log += "Rendered page: " + std::to_string(section ? section->currentPage : 0) + "\\n";
            log += "Current-page indexed footnotes: 0\\n\\n";
            log += "Error: CURRENT_PAGE_FOOTNOTE_INDEX_EMPTY\\n";
            logFile.write(reinterpret_cast<const uint8_t*>(log.data()), log.size());
            logFile.flush();
            logFile.close();
          }
        }
      }
      openFootnotesList(false, true);
      break;
    }'''

if old_case not in s:
    # Allow applying over an R4H-style case if the generated chain changes.
    old_case2 = '''    case EpubReaderMenuActivity::MenuAction::FOOTNOTES: {
      // CPHUN-135r4h crash fix: never synchronously scan the whole EPUB from
      // the Reader menu. On X4, ensureBookFootnotes() can exhaust resources
      // while walking many spine items (reproduced with Michelangelo around
      // id_Footnote_132). Use only the already parsed current-page index here.
      openFootnotesList(false, true);
      break;
    }'''
    if old_case2 not in s:
        raise SystemExit("R4K2F5: FOOTNOTES menu case not found")
    s = s.replace(old_case2, new_case, 1)
else:
    s = s.replace(old_case, new_case, 1)

p.write_text(s, encoding="utf-8")
print("CPHUN-135r4k2f5 applied: current-page-only footnotes + index-miss log")
