from pathlib import Path
import re

p = Path("src/activities/util/HungarianKeyboardLayout.h")
s = p.read_text(encoding="utf-8")


def replace_array(name: str, body: str):
    global s
    pat = re.compile(rf'inline const fui::KeyboardKey {name}\[\]\s*=\s*\{{.*?\}};', re.S)
    repl = f'inline const fui::KeyboardKey {name}[] = {{\n{body}\n}};'
    s2, n = pat.subn(lambda m: repl, s, count=1)
    if n != 1:
        raise SystemExit(f"CPHUN-135r4g: {name} array not found: {n}")
    s = s2


# User-reviewed fn/symbol layout corrections.
# Row 2: slash is already permanently available on the bottom row, so use backslash.
replace_array(
    "SYMBOL_ROW2",
    '''    HUK("\\\\", "\\\\", '\\\\'), HUK(":", ":", ':'), HUK(";", ";", ';'), HUK("(", "(", '('), HUK(")", ")", ')'),
    HUK("€", "€", 1401), HUK("$", "$", '$'), HUK("&", "&", '&'), HUK("@", "@", '@'),
    HUK("„", "„", 1402), HUK("”", "”", 1403)''',
)

# Row 3: keep the bracket family, retain en dash, and replace the two cramped/
# ambiguous middle symbols with the fundamental + and * operators.
replace_array(
    "SYMBOL_EXTRA_ROW",
    '''    HUK("[", "[", '['), HUK("]", "]", ']'), HUK("{", "{", '{'), HUK("}", "}", '}'),
    HUK("–", "–", 1410), HUK("+", "+", '+'), HUK("*", "*", '*'), HUK("§", "§", 1413),
    HUK("°", "°", 1414), HUK("«", "«", 1415), HUK("»", "»", 1416)''',
)

# Row 4 is rebuilt as EXACTLY ten keys. This fixes the former row-count/array
# mismatch that let the renderer read the following array's '[' and ']' keys.
# The ellipsis gets 3 width-units so it is no longer squeezed/truncated.
replace_array(
    "SYMBOL_ROW3",
    '''    HUKS(nullptr, fui::KeyKind::Shift, fui::QWERTY_KEY_SHIFT, 3),
    HUK("=", "=", '='), HUK("!", "!", '!'), HUK("'", "'", '\\''), HUK("\\\"", "\\\"", '\"'),
    HUK("#", "#", '#'), HUKW("…", "…", 1404, 3), HUK("<", "<", '<'), HUK(">", ">", '>'),
    HUKS(nullptr, fui::KeyKind::Delete, fui::QWERTY_KEY_BACKSPACE, 3)''',
)

# Lock the visible symbol layer row counts to the actual arrays.
rows_pat = re.compile(r'inline const fui::KeyboardRow SYMBOL_ROWS\[\]\s*=\s*\{.*?\};', re.S)
rows_repl = '''inline const fui::KeyboardRow SYMBOL_ROWS[] = {
    {NUM_ROW, 11, 0}, {SYMBOL_ROW2, 11, 0}, {SYMBOL_EXTRA_ROW, 11, 0}, {SYMBOL_ROW3, 10, 0},
    {SYMBOL_BOTTOM, 7, 0}};'''
s, n = rows_pat.subn(lambda m: rows_repl, s, count=1)
if n != 1:
    raise SystemExit(f"CPHUN-135r4g: SYMBOL_ROWS not found: {n}")

# The primary symbol layer must remain five rows high.
s, n = re.subn(r'inline const fui::KeyboardLayout SYMBOL_LAYOUT\{SYMBOL_ROWS,\s*\d+\};',
                'inline const fui::KeyboardLayout SYMBOL_LAYOUT{SYMBOL_ROWS, 5};', s, count=1)
if n != 1:
    raise SystemExit("CPHUN-135r4g: SYMBOL_LAYOUT definition not found")

# Structural checks: 10-row action keys and no accidental duplicate ? or slash.
row3 = re.search(r'inline const fui::KeyboardKey SYMBOL_ROW3\[\]\s*=\s*\{(.*?)\};', s, re.S).group(1)
if row3.count('HUK(') + row3.count('HUKW(') + row3.count('HUKS(') != 10:
    raise SystemExit("CPHUN-135r4g: SYMBOL_ROW3 is not exactly 10 keys")
if 'HUK("?", "?", \'?\')' in row3:
    raise SystemExit("CPHUN-135r4g: duplicate ? remained in SYMBOL_ROW3")
if 'HUK("<", "<", \'<\')' not in row3 or 'HUK(">", ">", \'>\')' not in row3:
    raise SystemExit("CPHUN-135r4g: < > keys missing")

p.write_text(s, encoding="utf-8")
print("CPHUN-135r4g keyboard corrections applied: \\, +, *, =, <, >, wide ellipsis, right-edge Backspace")
