from pathlib import Path
import re

# CPHUN-135r4k2f8
# Unified TSV export for MARK + EDIT records.
# - SD root /edits
# - deterministic filename derived from full EPUB path
# - removes legacy "Megjelölt szavak mentése" TXT export row
# - no export confirmation popup
# - Book tab menu action: "Szerkesztések exportálása"

menu_h = Path("src/activities/reader/EpubReaderMenuActivity.h")
s = menu_h.read_text(encoding="utf-8")
if "EXPORT_EDITS" not in s:
    s = s.replace("    TEXT_SETTINGS,\n", "    EXPORT_EDITS,\n    TEXT_SETTINGS,\n", 1)
menu_h.write_text(s, encoding="utf-8")

menu_cpp = Path("src/activities/reader/EpubReaderMenuActivity.cpp")
s = menu_cpp.read_text(encoding="utf-8")
export_row = '      {MenuAction::EXPORT_EDITS, StrId::STR_TEXT_SETTINGS, "Szerkesztések exportálása"},\n'
if export_row not in s:
    cover = '      {MenuAction::BOOK_COVER, StrId::STR_TEXT_SETTINGS, "Borító megjelenítése"},\n'
    if cover not in s:
        raise SystemExit("R4K2F8: BOOK_COVER menu row not found")
    s = s.replace(cover, cover + export_row, 1)
menu_cpp.write_text(s, encoding="utf-8")

reader_h = Path("src/activities/reader/EpubReaderActivity.h")
s = reader_h.read_text(encoding="utf-8")
if "bool exportEditsTsv();" not in s:
    anchor = "  void openEditKeyboard(HighlightResult selection);\n"
    if anchor not in s:
        raise SystemExit("R4K2F8: openEditKeyboard declaration not found")
    s = s.replace(anchor, anchor + "  bool exportEditsTsv();\n", 1)
reader_h.write_text(s, encoding="utf-8")

reader = Path("src/activities/reader/EpubReaderActivity.cpp")
s = reader.read_text(encoding="utf-8")

impl = r'''
bool EpubReaderActivity::exportEditsTsv() {
  if (!epub) return false;

  constexpr const char* EXPORT_DIR = "/edits";
  if (!Storage.exists(EXPORT_DIR) && !Storage.mkdir(EXPORT_DIR)) {
    LOG_ERR("ERS", "Failed to create edits export directory");
    return false;
  }

  const std::string bookPath = epub->getPath();
  const size_t slash = bookPath.find_last_of("/\\");
  const std::string bookFile = slash == std::string::npos ? bookPath : bookPath.substr(slash + 1);

  // Filename uses the full SD path so same-title test EPUBs in different
  // directories remain distinct:
  // /BOOX/test_v3/Michelangelo.epub -> /edits/BOOX_test_v3_Michelangelo.tsv
  std::string exportBase = bookPath;
  while (!exportBase.empty() && (exportBase.front() == '/' || exportBase.front() == '\\')) exportBase.erase(0, 1);
  const size_t dot = exportBase.find_last_of('.');
  if (dot != std::string::npos) exportBase.erase(dot);
  for (char& c : exportBase) {
    const unsigned char u = static_cast<unsigned char>(c);
    if (c == '/' || c == '\\' || c == '<' || c == '>' || c == ':' || c == '"' || c == '|' || c == '?' ||
        c == '*' || u < 32) {
      c = '_';
    }
  }
  if (exportBase.empty()) exportBase = "book";
  if (exportBase.size() > 180) exportBase.erase(0, exportBase.size() - 180);
  const std::string exportPath = std::string(EXPORT_DIR) + "/" + exportBase + ".tsv";

  auto field = [](std::string value) {
    for (char& c : value) {
      if (c == '\t' || c == '\r' || c == '\n') c = ' ';
    }
    return value;
  };

  auto xhtmlForSpine = [this](const int spine) -> std::string {
    if (!epub || spine < 0 || spine >= epub->getSpineItemsCount()) return {};
    return epub->getSpineItem(spine).href;
  };

  Storage.remove(exportPath.c_str());
  HalFile out;
  if (!Storage.openFileForWrite("ERS", exportPath, out)) {
    LOG_ERR("ERS", "Failed to open TSV export: %s", exportPath.c_str());
    return false;
  }

  auto writeText = [&](const std::string& text) -> bool {
    return text.empty() ||
           out.write(reinterpret_cast<const uint8_t*>(text.data()), text.size()) == static_cast<int>(text.size());
  };

  auto writeRow = [&](const uint32_t id, const char* type, const int spine, const uint32_t offset,
                      const uint16_t length, const std::string& original, const std::string& replacement) -> bool {
    std::string row;
    row.reserve(512 + original.size() + replacement.size());
    row += "1\t";
    row += std::to_string(id);
    row += "\t";
    row += type;
    row += "\t";
    row += field(bookPath);
    row += "\t";
    row += field(bookFile);
    row += "\t";
    row += field(epub->getTitle());
    row += "\t";
    row += field(epub->getAuthor());
    row += "\t";
    row += field(xhtmlForSpine(spine));
    row += "\t";
    row += std::to_string(spine);
    row += "\t";
    row += std::to_string(offset);
    row += "\t";
    row += std::to_string(length);
    row += "\t";
    row += field(original);
    row += "\t";
    row += field(replacement);
    // Reserved for later Calibre-assisted context verification. Intentionally
    // blank on-device to avoid rereading/inflating full XHTML only for export.
    row += "\t\t\n";
    return writeText(row);
  };

  const std::string header =
      "version\tid\ttype\tbook_path\tbook_file\tbook_title\tbook_author\txhtml\tspine\tvisible_offset\tlength\t"
      "original\treplacement\tcontext_before\tcontext_after\n";
  bool ok = writeText(header);
  uint32_t id = 1;

  if (ok && highlightStore) {
    for (const auto& mark : highlightStore->items()) {
      if (!writeRow(id++, "MARK", mark.spineIndex, mark.visibleTextOffset, mark.length, mark.text, "")) {
        ok = false;
        break;
      }
    }
  }

  if (ok && textEditStore) {
    for (const auto& edit : textEditStore->items()) {
      if (!writeRow(id++, "EDIT", edit.spineIndex, edit.visibleTextOffset, edit.length, edit.originalText,
                    edit.replacementText)) {
        ok = false;
        break;
      }
    }
  }

  out.flush();
  out.close();
  if (!ok) {
    Storage.remove(exportPath.c_str());
    LOG_ERR("ERS", "TSV export failed: %s", exportPath.c_str());
    return false;
  }

  LOG_INF("ERS", "TSV edits exported to %s (%lu records)", exportPath.c_str(),
          static_cast<unsigned long>(id - 1));
  return true;
}

'''

if "bool EpubReaderActivity::exportEditsTsv()" not in s:
    marker = "void EpubReaderActivity::onReaderMenuConfirm(EpubReaderMenuActivity::MenuAction action) {"
    if marker not in s:
        raise SystemExit("R4K2F8: onReaderMenuConfirm marker not found")
    s = s.replace(marker, impl + marker, 1)

case = '''    case EpubReaderMenuActivity::MenuAction::EXPORT_EDITS: {
      // Direct export: no confirmation popup.
      exportEditsTsv();
      openReaderMenu(true);
      break;
    }
'''
if "MenuAction::EXPORT_EDITS" not in s:
    anchor = '''    case EpubReaderMenuActivity::MenuAction::BOOK_COVER: {'''
    if anchor not in s:
        raise SystemExit("R4K2F8: BOOK_COVER switch case not found")
    s = s.replace(anchor, case + anchor, 1)

reader.write_text(s, encoding="utf-8")

# Remove legacy TXT export from the merged Bookmarks/Highlights list.
bh = Path("src/activities/reader/EpubReaderBookmarksActivity.h")
s = bh.read_text(encoding="utf-8")
s = s.replace("enum class RowKind : uint8_t { Bookmark, Highlight, Export };",
              "enum class RowKind : uint8_t { Bookmark, Highlight };")
s = s.replace("  std::string exportStatus;\n", "")
s = s.replace("  bool exportMarkedWords();\n", "")
bh.write_text(s, encoding="utf-8")

bc = Path("src/activities/reader/EpubReaderBookmarksActivity.cpp")
s = bc.read_text(encoding="utf-8")
s = s.replace('constexpr char EXPORT_ROOT[] = "/exports";\n', "")
s = s.replace(
    "  const size_t total = bookmarks.size() + highlightCount + (highlightCount ? 1 : 0);",
    "  const size_t total = bookmarks.size() + highlightCount;"
)

legacy_row = '''    if (!highlights.empty()) {
      rows.push_back({RowKind::Export, 0});
      rowLabels.push_back("Megjelölt szavak mentése");
      rowSubtitles.push_back(exportStatus.empty() ? "TXT" : exportStatus);
    }
'''
s = s.replace(legacy_row, "")

start = s.find("bool EpubReaderBookmarksActivity::exportMarkedWords() {")
if start >= 0:
    end = s.find("void EpubReaderBookmarksActivity::openSelectedItem()", start)
    if end < 0:
        raise SystemExit("R4K2F8: legacy export function end not found")
    s = s[:start] + s[end:]

legacy_branch = '''  if (row.kind == RowKind::Export) {
    exportStatus = exportMarkedWords() ? exportStatus : "Mentési hiba";
    rebuildRows(); requestUpdate(true); return;
  }
'''
s = s.replace(legacy_branch, "")

# Remove all remaining legacy Export-row guards now that RowKind::Export no longer exists.
s = s.replace("  if (rows[index].kind == RowKind::Export) return;\n", "")
s = s.replace(" && rows[nav.selected].kind != RowKind::Export", "")
s = s.replace("  if (row.kind == RowKind::Export) return;\n", "")

# Tolerate formatting variants of the same legacy branch.
s = re.sub(
    r'  if \(row\.kind == RowKind::Export\) \{\n.*?\n  \}\n(?=  ProgressChangeResult result\{\};)',
    '',
    s,
    count=1,
    flags=re.S,
)

# R132r5/r6 later converted the old TXT export into a Back-button export prompt.
# Remove that legacy prompt path completely as part of the TSV migration.
s = re.sub(
    r'void EpubReaderBookmarksActivity::finishCancelled\(\) \{.*?\n\}\n\n'
    r'void EpubReaderBookmarksActivity::showExportConfirmation\(\) \{.*?\n\}\n\n',
    '',
    s,
    count=1,
    flags=re.S,
)

s = re.sub(
    r'bool EpubReaderBookmarksActivity::handleCustomInput\(\) \{.*?\n\}',
    '''bool EpubReaderBookmarksActivity::handleCustomInput() {
  if (confirmPopup.handleInput(mappedInput, [this] { requestUpdate(); })) return true;
  if (confirmingDelete) { confirmingDelete = false; requestUpdate(); return true; }
  return false;
}''',
    s,
    count=1,
    flags=re.S,
)

s = re.sub(
    r'bool EpubReaderBookmarksActivity::handleButtons\(\) \{.*?\n\}',
    '''bool EpubReaderBookmarksActivity::handleButtons() {
  if (mappedInput.wasReleased(MappedInputManager::Button::Back)) {
    ActivityResult result;
    result.isCancelled = true;
    setResult(std::move(result));
    finish();
    return true;
  }
  if (mappedInput.wasReleased(MappedInputManager::Button::Confirm)) {
    if (mappedInput.getHeldTime() > ENTER_DELETE_MODE_MS && !rows.empty())
      showDeleteConfirmation();
    else
      openSelectedItem();
    return true;
  }
  return false;
}''',
    s,
    count=1,
    flags=re.S,
)

bc.write_text(s, encoding="utf-8")

# Header cleanup for the old TXT-export prompt state.
s = bh.read_text(encoding="utf-8")
for old in [
    "  std::string exportStatus;\n",
    "  bool exportMarkedWords();\n",
    "  void finishCancelled();\n",
    "  void showExportConfirmation();\n",
    "  bool confirmingExport = false;\n",
]:
    s = s.replace(old, "")
bh.write_text(s, encoding="utf-8")

print("CPHUN-135r4k2f8 applied: unified /edits TSV export, legacy TXT export/prompt removed")
