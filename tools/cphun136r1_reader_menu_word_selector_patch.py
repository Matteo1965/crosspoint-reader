from pathlib import Path
import re

# CPHUN-136R1
# - Remove GO_HOME from Könyv tab.
# - Render dictionary setting as one left-aligned label: "Szótár: <név>".
# - Finalize the common word selector's three direct modes:
#   Dictionary -> Keresés, Highlight -> Megjelölés, Edit -> Szerkesztés.

def read(path):
    return Path(path).read_text(encoding="utf-8")

def write(path, s):
    Path(path).write_text(s, encoding="utf-8")

# ---------------------------------------------------------------------------
# Reader menu cleanup + dictionary row layout
# ---------------------------------------------------------------------------
menu_path = "src/activities/reader/EpubReaderMenuActivity.cpp"
s = read(menu_path)

# Remove Főoldalra from Könyv.
s2, n = re.subn(
    r'^\s*\{MenuAction::GO_HOME,\s*StrId::STR_GO_HOME_BUTTON(?:,\s*"[^"]*")?\},\n',
    '',
    s,
    count=1,
    flags=re.MULTILINE,
)
if n != 1:
    raise SystemExit(f"CPHUN-136R1: expected one GO_HOME row, found {n}")
s = s2

# Direct Reader-menu entries must remain independently available.
# Rename dictionary entry to the concise mode name requested by the unified UX.
s2, n = re.subn(
    r'items\.push_back\(\{MenuAction::DICTIONARY,\s*StrId::STR_LOOKUP,\s*"[^"]*"\}\);',
    'items.push_back({MenuAction::DICTIONARY, StrId::STR_LOOKUP, "Szótár"});',
    s,
    count=1,
)
if n != 1:
    raise SystemExit("CPHUN-136R1: DICTIONARY menu row not found")
s = s2

if 'MenuAction::HIGHLIGHT' not in s or '"Megjelölés"' not in s:
    raise SystemExit("CPHUN-136R1: direct Megjelölés menu entry missing")
if 'MenuAction::EDIT' not in s or '"Szerkesztés"' not in s:
    raise SystemExit("CPHUN-136R1: direct Szerkesztés menu entry missing")

# In buildScreen(), replace the dictionary setting's separate label/value
# presentation with one persistent left-aligned label string.
old = '''    } else if (action == MenuAction::DICTIONARY_SETTINGS) {
      menuRowItems[i].value = selectedDictionaryOption < dictionaryOptionPointers.size()
                                  ? dictionaryOptionPointers[selectedDictionaryOption]
                                  : nullptr;
    } else if (action == MenuAction::NIGHT_MODE) {'''
new = '''    } else if (action == MenuAction::DICTIONARY_SETTINGS) {
      dictionaryRowLabel = "Szótár: ";
      if (selectedDictionaryOption < dictionaryOptionPointers.size() &&
          dictionaryOptionPointers[selectedDictionaryOption] &&
          dictionaryOptionPointers[selectedDictionaryOption][0] != '\\0') {
        dictionaryRowLabel += dictionaryOptionPointers[selectedDictionaryOption];
      } else {
        dictionaryRowLabel += "Nincs beállítva";
      }
      menuRowItems[i].label = dictionaryRowLabel.c_str();
      menuRowItems[i].value = nullptr;
    } else if (action == MenuAction::NIGHT_MODE) {'''
if old not in s:
    raise SystemExit("CPHUN-136R1: DICTIONARY_SETTINGS value-layout block not found")
s = s.replace(old, new, 1)

write(menu_path, s)

# Backing storage for the dynamic label must outlive buildScreen().
hdr_path = "src/activities/reader/EpubReaderMenuActivity.h"
h = read(hdr_path)
anchor = '  std::vector<std::string> dictionaryOptionLabels;\n'
if anchor not in h:
    raise SystemExit("CPHUN-136R1: dictionaryOptionLabels header anchor missing")
if 'std::string dictionaryRowLabel;' not in h:
    h = h.replace(anchor, anchor + '  std::string dictionaryRowLabel;\n', 1)
write(hdr_path, h)

# ---------------------------------------------------------------------------
# Common word selector: explicit three-mode behavior and button labels
# ---------------------------------------------------------------------------
mode_path = "src/highlights/HighlightMode.h"
m = read(mode_path)
for token in ("Dictionary", "Highlight", "Edit"):
    if token not in m:
        raise SystemExit(f"CPHUN-136R1: WordSelectionMode::{token} missing")

sel_path = "src/activities/reader/DictionaryWordSelectActivity.cpp"
w = read(sel_path)

# Final button labels; no post-selection action chooser.
pattern = re.compile(
    r'''  const char\* confirmLabel = mode == WordSelectionMode::Highlight\s*\n'''
    r'''\s*\? "Megjelölés"\s*\n'''
    r'''\s*: \(mode == WordSelectionMode::Edit \? "Szerkesztés" : tr\(STR_LOOKUP\)\);'''
)
replacement = '''  const char* confirmLabel = mode == WordSelectionMode::Highlight
                                 ? "Megjelölés"
                                 : (mode == WordSelectionMode::Edit ? "Szerkesztés" : "Keresés");'''
w2, n = pattern.subn(replacement, w, count=1)
if n != 1:
    # Accept already-flattened formatting and patch the dictionary fallback only.
    w2, n2 = re.subn(
        r'(mode == WordSelectionMode::Edit \? "Szerkesztés" : )tr\(STR_LOOKUP\)',
        r'\1"Keresés"',
        w,
        count=1,
    )
    if n2 != 1:
        raise SystemExit("CPHUN-136R1: common selector confirm-label block not found")
w = w2

# Ensure Highlight/Edit both return the selected anchor, while Dictionary performs lookup.
if w.count('mode == WordSelectionMode::Highlight || mode == WordSelectionMode::Edit') < 2:
    raise SystemExit("CPHUN-136R1: selector mode routing is not unified for Confirm + touch")

write(sel_path, w)

# Reader dispatch must route all three direct menu items into the same selector.
reader = read("src/activities/reader/EpubReaderActivity.cpp")
required = [
    'openDictionaryWordSelect(WordSelectionMode::Dictionary)',
    'openDictionaryWordSelect(WordSelectionMode::Highlight)',
    'openDictionaryWordSelect(WordSelectionMode::Edit)',
]
for token in required:
    if token not in reader:
        raise SystemExit(f"CPHUN-136R1: direct selector dispatch missing: {token}")

print("CPHUN-136R1 applied: Home removed, dictionary row compacted, 3-mode common selector finalized")
