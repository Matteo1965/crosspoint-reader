from pathlib import Path

def read(path):
    return Path(path).read_text(encoding="utf-8")

def write(path, s):
    Path(path).write_text(s, encoding="utf-8")

# ---------------------------------------------------------------------------
# CPHUN-136R2: unified Hungarian labels
# ---------------------------------------------------------------------------
btn_path = "src/activities/settings/ButtonFunctionsActivity.cpp"
s = read(btn_path)

replacements = {
    'case ReaderAction::OpenReaderMenu: return hu ? "Olvasó menü" : "Reader menu";':
        'case ReaderAction::OpenReaderMenu: return hu ? "Olvasómenü" : "Reader menu";',
    'case ReaderAction::OpenDictionary: return hu ? "Keresés / Szótár" : "Search / Dictionary";':
        'case ReaderAction::OpenDictionary: return hu ? "Szótár" : "Search / Dictionary";',
    'case ReaderAction::ToggleBookmark: return hu ? "Könyvjelző hozzáadása" : "Add bookmark";':
        'case ReaderAction::ToggleBookmark: return hu ? "Könyvjelző jelölés" : "Add bookmark";',
    'case ReaderAction::LineSpacingNext: return hu ? "Soremelés +" : "Line spacing +";':
        'case ReaderAction::LineSpacingNext: return hu ? "Sorköz +" : "Line spacing +";',
    'case ReaderAction::LineSpacingPrevious: return hu ? "Soremelés −" : "Line spacing -";':
        'case ReaderAction::LineSpacingPrevious: return hu ? "Sorköz −" : "Line spacing -";',
    'case ReaderAction::ToggleNightMode: return hu ? "Éjszakai mód KI/BE" : "Night mode on/off";':
        'case ReaderAction::ToggleNightMode: return hu ? "Sötét mód KI/BE" : "Night mode on/off";',
    'case ReaderAction::GoHome: return hu ? "Kezdőképernyő" : "Home";':
        'case ReaderAction::GoHome: return hu ? "Főoldal" : "Home";',
}
for old, new in replacements.items():
    if s.count(old) != 1:
        raise SystemExit(f"CPHUN-136R2: ButtonFunctions label anchor matches={s.count(old)}: {old}")
    s = s.replace(old, new, 1)
write(btn_path, s)

hu_path = "lib/I18n/translations/hungarian.yaml"
hu = read(hu_path)
auto_old = 'STR_AUTO_TURN_PAGES_PER_MIN: "Autom. lapozás (lap/perc)"'
auto_new = 'STR_AUTO_TURN_PAGES_PER_MIN: "Auto. lapozás, lap/perc"'
if hu.count(auto_old) != 1:
    raise SystemExit(f"CPHUN-136R2: auto-page-turn translation anchor matches={hu.count(auto_old)}")
hu = hu.replace(auto_old, auto_new, 1)
write(hu_path, hu)

# Reader menu should use exactly the same Auto. lapozás text.
menu_path = "src/activities/reader/EpubReaderMenuActivity.cpp"
menu = read(menu_path)
auto_override_old = 'items.push_back({MenuAction::AUTO_PAGE_TURN, StrId::STR_AUTO_TURN_PAGES_PER_MIN, "Auto. lapozás, lap/perc"});'
if auto_override_old not in menu:
    raise SystemExit("CPHUN-136R2: Reader auto-page-turn label missing")
# Keep as-is; assertion above is intentional.

# ---------------------------------------------------------------------------
# Common selector verification: one component, three modes.
# ---------------------------------------------------------------------------
mode_h = read("src/highlights/HighlightMode.h")
for token in ("Dictionary", "Highlight", "Edit"):
    if token not in mode_h:
        raise SystemExit(f"CPHUN-136R2: WordSelectionMode::{token} missing")

selector = read("src/activities/reader/DictionaryWordSelectActivity.cpp")
if '"Keresés"' not in selector or '"Megjelölés"' not in selector or '"Szerkesztés"' not in selector:
    raise SystemExit("CPHUN-136R2: selector mode button labels incomplete")
if selector.count("mode == WordSelectionMode::Highlight || mode == WordSelectionMode::Edit") < 2:
    raise SystemExit("CPHUN-136R2: common selector result routing incomplete")

reader = read("src/activities/reader/EpubReaderActivity.cpp")
dispatches = {
    "Dictionary": "openDictionaryWordSelect(WordSelectionMode::Dictionary)",
    "Highlight": "openDictionaryWordSelect(WordSelectionMode::Highlight)",
    "Edit": "openDictionaryWordSelect(WordSelectionMode::Edit)",
}
for name, token in dispatches.items():
    if token not in reader:
        raise SystemExit(f"CPHUN-136R2: {name} dispatch missing")

# All three modes must instantiate the same DictionaryWordSelectActivity,
# parameterized by 'mode', rather than separate chooser activities.
if "std::make_unique<DictionaryWordSelectActivity>" not in reader:
    raise SystemExit("CPHUN-136R2: common DictionaryWordSelectActivity instantiation missing")
if "currentSpineIndex, mode)" not in reader:
    raise SystemExit("CPHUN-136R2: selector constructor is not receiving WordSelectionMode")

print("CPHUN-136R2 applied: Hungarian labels unified and common 3-mode word selector verified")
