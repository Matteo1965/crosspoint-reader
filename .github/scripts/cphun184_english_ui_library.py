#!/usr/bin/env python3
from pathlib import Path
import re

def read(path):
    return Path(path).read_text(encoding="utf-8")

def write(path, text):
    Path(path).write_text(text, encoding="utf-8")

# ---------------------------------------------------------------------------
# CPHUN-184
# 1) English Letter spacing correction: stable 4-state labels and persistence.
#    OFF=0, Weak=10, Medium=40, Strong=70.
# 2) Library Recent overlay: EPUB-only, while preserving recent.json and
#    File Browser visibility for TXT/MD/XTC.
# ---------------------------------------------------------------------------

# --- Text Settings ----------------------------------------------------------
p = "src/activities/settings/TextSettingsActivity.cpp"
s = read(p)

# Keep the CPHUN-182 crash fix (stable string literals), but make the visible
# threshold label match the popup semantics in both languages.
old_threshold_helper = """const char* letterSpacingThresholdLabel(const uint8_t value) {
  switch (value) {
    case 0: return "0";
    case 50: return "50";
    case 60: return "60";
    case 70: return "70";
    default: return "60";
  }
}
"""
new_threshold_helper = """const char* letterSpacingThresholdLabel(const uint8_t value) {
  const bool hu = I18N.getLanguage() == Language::HU;
  switch (value) {
    case 0: return hu ? "KI" : "OFF";
    case 50: return hu ? "Gyenge" : "Weak";
    case 60: return hu ? "Közepes" : "Medium";
    case 70: return hu ? "Erős" : "Strong";
    default: return hu ? "Közepes" : "Medium";
  }
}
"""
if old_threshold_helper not in s:
    raise SystemExit("CPHUN-184 threshold display helper anchor missing")
s = s.replace(old_threshold_helper, new_threshold_helper, 1)

fn_start = s.find("void TextSettingsActivity::confirmLayoutRow(int row)")
fn_end = s.find("void TextSettingsActivity::confirmStyleRow", fn_start)
if fn_start < 0 or fn_end < 0:
    raise SystemExit("CPHUN-184 confirmLayoutRow boundaries missing")

section = s[fn_start:fn_end]
pattern = re.compile(
    r'    case LayoutRow::LetterSpacingCorrection: \{.*?'
    r'\n    \}\n    case LayoutRow::ShortHyphen:',
    re.S,
)
replacement = """    case LayoutRow::LetterSpacingCorrection: {
      const bool hu = I18N.getLanguage() == Language::HU;
      const char* options[] = {
          hu ? "KI" : "OFF",
          hu ? "Gyenge" : "Weak",
          hu ? "Közepes" : "Medium",
          hu ? "Erős" : "Strong",
      };
      int cur = 0;
      switch (SETTINGS.letterSpacingLimitPercent) {
        case 0: cur = 0; break;
        case 10: cur = 1; break;
        case 40: cur = 2; break;
        case 70: cur = 3; break;
        default: cur = 0; break;
      }
      optionPopup_.show(
          hu ? "Betűköz korrekció" : "Letter spacing correction",
          options, 4, cur, [](int idx) {
            static constexpr uint16_t values[] = {0, 10, 40, 70};
            if (idx >= 0 && idx < 4) {
              SETTINGS.letterSpacingLimitPercent = values[idx];
              SETTINGS.saveToFile();
            }
          });
      requestUpdate();
      break;
    }
    case LayoutRow::ShortHyphen:"""
section2, count = pattern.subn(replacement, section, count=1)
if count != 1:
    raise SystemExit(f"CPHUN-184 letter-spacing picker matches={count}")
s = s[:fn_start] + section2 + s[fn_end:]

# Make the row value use the same semantic labels as the popup.
# Find the LetterSpacingCorrection case specifically inside layoutValueText()
# and replace that balanced braced case body. This survives generated-source
# variations and inserted neighboring cases.
value_fn_start = s.find("std::string TextSettingsActivity::layoutValueText(int row) const")
value_fn_end = s.find("void TextSettingsActivity::confirmStyleRow", value_fn_start)
if value_fn_start < 0 or value_fn_end < 0:
    raise SystemExit("CPHUN-184 layoutValueText boundaries missing")
case_start = s.find("    case LayoutRow::LetterSpacingCorrection: {", value_fn_start, value_fn_end)
if case_start < 0:
    raise SystemExit("CPHUN-184 layoutValueText LetterSpacingCorrection case missing")
brace_start = s.find("{", case_start)
depth = 0
case_end = None
for i in range(brace_start, value_fn_end):
    if s[i] == "{":
        depth += 1
    elif s[i] == "}":
        depth -= 1
        if depth == 0:
            case_end = i + 1
            break
if case_end is None:
    raise SystemExit("CPHUN-184 layoutValueText LetterSpacingCorrection brace parse failed")
new_value_block = """    case LayoutRow::LetterSpacingCorrection: {
      const bool hu = I18N.getLanguage() == Language::HU;
      switch (SETTINGS.letterSpacingLimitPercent) {
        case 0: return hu ? "KI" : "OFF";
        case 10: return hu ? "Gyenge" : "Weak";
        case 40: return hu ? "Közepes" : "Medium";
        case 70: return hu ? "Erős" : "Strong";
        default: return hu ? "KI" : "OFF";
      }
    }"""
s = s[:case_start] + new_value_block + s[case_end:]
write(p, s)

# --- Library Recent overlay -------------------------------------------------
p = "src/activities/library/LibraryListActivity.h"
s = read(p)
old = """  uint16_t pinnedAscRows[RecentBooksStore::MAX_RECENT_BOOKS] = {};
  uint16_t overlapRows[RecentBooksStore::MAX_RECENT_BOOKS] = {};
  uint8_t pinnedTotal = 0;"""
new = """  uint16_t pinnedAscRows[RecentBooksStore::MAX_RECENT_BOOKS] = {};
  uint16_t overlapRows[RecentBooksStore::MAX_RECENT_BOOKS] = {};
  // Library shows EPUB only. Keep a compact mapping from visible pinned rows
  // to the original RecentBooksStore slots so non-EPUB recents remain stored
  // for other UI paths without appearing on the Library shelf.
  uint8_t pinnedBookIndices[RecentBooksStore::MAX_RECENT_BOOKS] = {};
  uint8_t pinnedTotal = 0;"""
if old not in s:
    raise SystemExit("CPHUN-184 pinned header anchor missing")
s = s.replace(old, new, 1)
write(p, s)

p = "src/activities/library/LibraryListActivity.cpp"
s = read(p)
if "#include <FsHelpers.h>" not in s:
    anchor = "#include <FreeInkUIIcon.h>\n"
    if anchor not in s:
        raise SystemExit("CPHUN-184 FsHelpers include anchor missing")
    s = s.replace(anchor, anchor + "#include <FsHelpers.h>\n", 1)

old_resolve = """void LibraryListActivity::resolvePinned() {
  const auto& books = RECENT_BOOKS.getBooks();
  pinnedTotal = static_cast<uint8_t>(std::min<size_t>(books.size(), RecentBooksStore::MAX_RECENT_BOOKS));
  for (int i = 0; i < pinnedTotal; i++) pinnedAscRows[i] = 0xFFFF;
  if (pinnedTotal > 0 && index.isOpen()) {
    library::BookIdentity identities[RecentBooksStore::MAX_RECENT_BOOKS];
    for (int i = 0; i < pinnedTotal; i++) {
      const std::string& path = books[static_cast<size_t>(i)].path;
      identities[i].pathHash = library::clixPathHash(path.data(), path.size());
      // Size is only a lookup prefilter; 0 (stat failed, e.g. the index handle
      // is the card's one open reader) falls back to hash-only matching.
      identities[i].fileSize = 0;
      HalFile file;
      if (Storage.openFileForRead("LIB", path.c_str(), file)) {
        identities[i].fileSize = static_cast<uint32_t>(file.fileSize());
      }
    }
    if (!index.recentRowsFor(identities, pinnedTotal, pinnedAscRows)) {
      // Without the match the overlay would duplicate every pinned book that is
      // also in the index; better to drop the pins than to show doubles.
      LOG_ERR("LIB", "recent-book lookup failed; overlay disabled");
      pinnedTotal = 0;
    }
  }
  refreshOverlap();
}"""
new_resolve = """void LibraryListActivity::resolvePinned() {
  const auto& books = RECENT_BOOKS.getBooks();
  pinnedTotal = 0;
  for (size_t storeIndex = 0;
       storeIndex < books.size() && pinnedTotal < RecentBooksStore::MAX_RECENT_BOOKS;
       ++storeIndex) {
    const std::string& path = books[storeIndex].path;
    if (!FsHelpers::checkFileExtension(path, ".epub")) continue;
    pinnedBookIndices[pinnedTotal] = static_cast<uint8_t>(storeIndex);
    pinnedAscRows[pinnedTotal] = 0xFFFF;
    ++pinnedTotal;
  }

  if (pinnedTotal > 0 && index.isOpen()) {
    library::BookIdentity identities[RecentBooksStore::MAX_RECENT_BOOKS];
    for (int i = 0; i < pinnedTotal; i++) {
      const std::string& path = books[pinnedBookIndices[i]].path;
      identities[i].pathHash = library::clixPathHash(path.data(), path.size());
      // Size is only a lookup prefilter; 0 (stat failed, e.g. the index handle
      // is the card's one open reader) falls back to hash-only matching.
      identities[i].fileSize = 0;
      HalFile file;
      if (Storage.openFileForRead("LIB", path.c_str(), file)) {
        identities[i].fileSize = static_cast<uint32_t>(file.fileSize());
      }
    }
    if (!index.recentRowsFor(identities, pinnedTotal, pinnedAscRows)) {
      LOG_ERR("LIB", "recent-book lookup failed; overlay disabled");
      pinnedTotal = 0;
    }
  }
  refreshOverlap();
}"""
if old_resolve not in s:
    raise SystemExit("CPHUN-184 resolvePinned anchor missing")
s = s.replace(old_resolve, new_resolve, 1)

# Every pinned-row access must use the compact visible->store mapping.
s = s.replace(
"""    if (selectedEntry() >= static_cast<int>(books.size())) return;
    path = books[static_cast<size_t>(selectedEntry())].path;""",
"""    if (selectedEntry() >= pinnedCount()) return;
    path = books[pinnedBookIndices[selectedEntry()]].path;""", 1)

s = s.replace(
"""    if (index < 0 || index >= static_cast<int>(books.size())) return;
    promptRemoveRecentBook(books[static_cast<size_t>(index)].path, books[static_cast<size_t>(index)].title);""",
"""    if (index < 0 || index >= pinnedCount()) return;
    const auto& book = books[pinnedBookIndices[index]];
    promptRemoveRecentBook(book.path, book.title);""", 1)

s = s.replace(
"""    if (entry < 0 || entry >= static_cast<int>(books.size())) return false;
    const auto& book = books[static_cast<size_t>(entry)];""",
"""    if (entry < 0 || entry >= pinnedCount()) return false;
    const auto& book = books[pinnedBookIndices[entry]];""", 1)

s = s.replace(
"""      if (selectedEntry() < static_cast<int>(books.size())) {
        const auto& book = books[static_cast<size_t>(selectedEntry())];""",
"""      if (selectedEntry() < pinnedCount()) {
        const auto& book = books[pinnedBookIndices[selectedEntry()]];""", 1)

write(p, s)

# Audits
ui = read("src/activities/settings/TextSettingsActivity.cpp")
libh = read("src/activities/library/LibraryListActivity.h")
libcpp = read("src/activities/library/LibraryListActivity.cpp")
checks = [
    ('static constexpr uint16_t values[] = {0, 10, 40, 70};', ui),
    ('hu ? "Gyenge" : "Weak"', ui),
    ('hu ? "Közepes" : "Medium"', ui),
    ('hu ? "Erős" : "Strong"', ui),
    ('case 50: return hu ? "Gyenge" : "Weak";', ui),
    ('case 60: return hu ? "Közepes" : "Medium";', ui),
    ('case 70: return hu ? "Erős" : "Strong";', ui),
    ('pinnedBookIndices[RecentBooksStore::MAX_RECENT_BOOKS]', libh),
    ('FsHelpers::checkFileExtension(path, ".epub")', libcpp),
    ('books[pinnedBookIndices[selectedEntry()]]', libcpp),
    ('books[pinnedBookIndices[entry]]', libcpp),
]
for token, text in checks:
    if token not in text:
        raise SystemExit("CPHUN-184 audit missing: " + token)

print("CPHUN-184 applied: English 4-state letter spacing + EPUB-only Library recent overlay")
