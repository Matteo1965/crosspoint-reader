from pathlib import Path

# CPHUN-135r4k2f9
# Reader menu wording/layout:
# - "Éjszakai mód" -> "Sötét mód"
# - move NIGHT_MODE from Olvasás to Könyv
# - place it immediately below Képernyő nézet (ROTATE_SCREEN)

p = Path("src/activities/reader/EpubReaderMenuActivity.cpp")
s = p.read_text(encoding="utf-8")

# Remove Night mode from Reading tab.
reading_variants = [
    '  items.push_back({MenuAction::NIGHT_MODE, StrId::STR_NIGHT_MODE});\n',
    '  items.push_back({MenuAction::NIGHT_MODE, StrId::STR_NIGHT_MODE, "Sötét mód"});\n',
]
removed = False
for old in reading_variants:
    if old in s:
        s = s.replace(old, "", 1)
        removed = True
        break
if not removed:
    raise SystemExit("R4K2F9: NIGHT_MODE row not found on Reading tab")

# Insert after Képernyő nézet on Book tab. The preceding patch chain moves
# ROTATE_SCREEN into buildMoreItems().
rotate_book = '      {MenuAction::ROTATE_SCREEN, StrId::STR_ORIENTATION},\n'
dark_book = '      {MenuAction::NIGHT_MODE, StrId::STR_NIGHT_MODE, "Sötét mód"},\n'
if dark_book not in s:
    if rotate_book not in s:
        raise SystemExit("R4K2F9: Book-tab ROTATE_SCREEN row not found")
    s = s.replace(rotate_book, rotate_book + dark_book, 1)

# Semantic verification: NIGHT_MODE appears exactly once in menu construction,
# and the visible label is the requested Hungarian wording.
construction = s[s.find("buildReadingItems"):s.find("const std::vector<EpubReaderMenuActivity::MenuItem>&")]
if construction.count("MenuAction::NIGHT_MODE") != 1:
    raise SystemExit("R4K2F9: NIGHT_MODE menu row count is not 1")
if '"Sötét mód"' not in construction:
    raise SystemExit("R4K2F9: requested Sötét mód label missing")

p.write_text(s, encoding="utf-8")
print("CPHUN-135r4k2f9 applied: Sötét mód moved to Könyv below Képernyő nézet")
