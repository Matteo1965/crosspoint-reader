from pathlib import Path
import re
import runpy

# Compatibility entry point for the CPHUN-135r4b build workflow.
# The actual feature/memory patching lives in cphun135r4b_patch_driver.py.
driver = Path(__file__).with_name("cphun135r4b_patch_driver.py")
runpy.run_path(str(driver), run_name="__main__")

# CPHUN-135r4b crash guard:
# Opening the Reader menu must never trigger whole-book footnote indexing.
reader = Path("src/activities/reader/EpubReaderActivity.cpp")
s = reader.read_text(encoding="utf-8")

open_menu = re.compile(
    r'(void EpubReaderActivity::openReaderMenu\(const bool startOnBookTab\)\s*\{\s*'
    r'pendingManualTurn\s*=\s*0\s*;)\s*ensureBookFootnotes\(\)\s*;',
    re.S,
)
s, n = open_menu.subn(r'\1', s, count=1)

menu_body = re.search(
    r'void EpubReaderActivity::openReaderMenu\(const bool startOnBookTab\)\s*\{(.*?)\n\}',
    s,
    re.S,
)
if not menu_body:
    raise SystemExit("CPHUN-135r4b: openReaderMenu() body not found after patching")
if "ensureBookFootnotes();" in menu_body.group(1):
    raise SystemExit("CPHUN-135r4b: eager footnote indexing still present in openReaderMenu()")

# CPHUN-135r4d crash guard:
# Reader menu -> Footnotes must not scan every XHTML spine synchronously on X4.
# Use the already parsed current-page footnote list. Whole-book indexing will be
# reintroduced only through an incremental/background implementation.
old_case = '''    case EpubReaderMenuActivity::MenuAction::FOOTNOTES: {
      ensureBookFootnotes();
      openFootnotesList(true, true);
      break;
    }'''
new_case = '''    case EpubReaderMenuActivity::MenuAction::FOOTNOTES: {
      openFootnotesList(false, true);
      break;
    }'''
if old_case in s:
    s = s.replace(old_case, new_case, 1)
elif new_case not in s:
    raise SystemExit("CPHUN-135r4d: FOOTNOTES menu action not found")
reader.write_text(s, encoding="utf-8")
print("CPHUN-135r4d Reader-menu footnotes use current-page index; whole-book synchronous scan disabled")

# -----------------------------------------------------------------------------
# fn keyboard visual/layout correction.
# -----------------------------------------------------------------------------
layout_path = Path("src/activities/util/HungarianKeyboardLayout.h")
k = layout_path.read_text(encoding="utf-8")

k2, n1 = re.subn(r'(inline const fui::KeyboardRow SYMBOL_ROWS\[\] = \{\n\s*)\{SYMBOL_ROW1, 11, 0\}',
                  r'\1{NUM_ROW, 11, 0}', k, count=1)
k = k2
k2, n2 = re.subn(r'(inline const fui::KeyboardRow SYMBOL2_ROWS\[\] = \{\n\s*)\{SYMBOL_ROW1, 11, 0\}',
                  r'\1{NUM_ROW, 11, 0}', k, count=1)
k = k2
if n1 != 1 or n2 != 1:
    raise SystemExit(f"CPHUN-135r4b: fn NUM_ROW substitution failed: symbol={n1}, symbol2={n2}")

def fix_symbol_action_row(text: str, name: str) -> str:
    pat = re.compile(rf'(inline const fui::KeyboardKey {name}\[\]\s*=\s*\{{)(.*?)(\}};)', re.S)
    m = pat.search(text)
    if not m:
        raise SystemExit(f"CPHUN-135r4b: {name} not found")
    body = m.group(2)
    body, ns = re.subn(
        r'(^\s*)HUKS\([^\n]*fui::KeyKind::Shift[^\n]*\),',
        r'\1HUKS(nullptr, fui::KeyKind::Shift, fui::QWERTY_KEY_SHIFT, 3),',
        body,
        count=1,
        flags=re.M,
    )
    if ns != 1:
        raise SystemExit(f"CPHUN-135r4b: {name} Shift normalization failed: {ns}")
    body, nb = re.subn(
        r',\s*(?:HUKW|HUKS)\([^\n]*\)\s*$',
        ',\n    HUKS(nullptr, fui::KeyKind::Delete, fui::QWERTY_KEY_BACKSPACE, 3)',
        body,
        count=1,
    )
    if nb != 1:
        raise SystemExit(f"CPHUN-135r4b: {name} Backspace normalization failed: {nb}")
    return text[:m.start()] + m.group(1) + body + m.group(3) + text[m.end():]

k = fix_symbol_action_row(k, "SYMBOL_ROW3")
k = fix_symbol_action_row(k, "SYMBOL2_ROW3")
layout_path.write_text(k, encoding="utf-8")

renderer_path = Path("src/activities/util/KeyboardLayoutSet.h")
r = renderer_path.read_text(encoding="utf-8")
fallback = '''  if (!keyboard_layouts::hu_keyboard::isHungarianLetterLayout(*props.layout)) {
    keyboard(frame, rect, props);
    return;
  }

'''
if fallback not in r:
    raise SystemExit("CPHUN-135r4b: Hungarian symbol-layout generic-renderer fallback not found")
r = r.replace(fallback, "", 1)
renderer_path.write_text(r, encoding="utf-8")

kcheck = layout_path.read_text(encoding="utf-8")
if not re.search(r'SYMBOL_ROWS\[\].*?\{NUM_ROW, 11, 0\}', kcheck, re.S):
    raise SystemExit("CPHUN-135r4b: fn first row is not NUM_ROW")
if not re.search(r'SYMBOL_ROW3\[\].*?KeyKind::Shift.*?QWERTY_KEY_BACKSPACE', kcheck, re.S):
    raise SystemExit("CPHUN-135r4b: fn Shift/Backspace controls missing")
if 'HUKS("fn", fui::KeyKind::Mode' not in kcheck or 'HUKS("OK", fui::KeyKind::Ok' not in kcheck:
    raise SystemExit("CPHUN-135r4b: fn/OK bottom controls missing")
print("CPHUN-135r4b fn keyboard fixed: normal number row + Hungarian Shift/Delete/Backspace/fn/OK rendering")

# The workflow temporarily lowers the cache version to 56 for older patches.
section_path = Path("lib/Epub/Epub/Section.cpp")
section = section_path.read_text(encoding="utf-8")
section2, nv = re.subn(r'SECTION_FILE_VERSION = \d+', 'SECTION_FILE_VERSION = 61', section, count=1)
if nv != 1:
    raise SystemExit("CPHUN-135r4b: SECTION_FILE_VERSION assignment not found")
section_path.write_text(section2, encoding="utf-8")

# CPHUN-135r4d identity.
build_id_path = Path("src/CPHUNBuildId.h")
build_id = build_id_path.read_text(encoding="utf-8")
build_id2, nbid = re.subn(r'#define CPHUN_BUILD_ID "[^"]+"',
                           '#define CPHUN_BUILD_ID "CPHUN-260917-135R4D-EXP"',
                           build_id, count=1)
if nbid != 1:
    raise SystemExit("CPHUN-135r4d: CPHUN_BUILD_ID define not found")
build_id_path.write_text(build_id2, encoding="utf-8")
print("CPHUN-135r4d build identity applied")
