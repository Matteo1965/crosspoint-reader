from pathlib import Path


def replace_once(path, old, new):
    p = Path(path)
    text = p.read_text(encoding="utf-8")
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"CPHUN-135r2: {path}: expected one match, found {count}: {old[:160]!r}")
    p.write_text(text.replace(old, new, 1), encoding="utf-8")


# -----------------------------------------------------------------------------
# Hungarian keyboard layout only
# -----------------------------------------------------------------------------
layout = "src/activities/util/HungarianKeyboardLayout.h"

replace_once(
    layout,
    "namespace fui = freeink::ui;\n\n",
    "namespace fui = freeink::ui;\n\n"
    "// CPHUN-135r2: separate forward-delete key used only by the Hungarian layout.\n"
    "inline constexpr int16_t FORWARD_DELETE_KEY = -100;\n\n",
)

replace_once(
    layout,
    '''inline const fui::KeyboardKey NUM_ROW[] = {
    HUK("0", "0", '0'), HUK("1", "1", '1'), HUK("2", "2", '2'), HUK("3", "3", '3'),
    HUK("4", "4", '4'), HUK("5", "5", '5'), HUK("6", "6", '6'), HUK("7", "7", '7'),
    HUK("8", "8", '8'), HUK("9", "9", '9'), HUK("-", "-", '-')};
''',
    '''inline const fui::KeyboardKey NUM_ROW[] = {
    HUK("0", "0", '0'), HUK("1", "1", '1'), HUK("2", "2", '2'), HUK("3", "3", '3'),
    HUK("4", "4", '4'), HUK("5", "5", '5'), HUK("6", "6", '6'), HUK("7", "7", '7'),
    HUK("8", "8", '8'), HUK("9", "9", '9'),
    HUKS(nullptr, fui::KeyKind::Delete, FORWARD_DELETE_KEY, 2)};
''',
)

replace_once(
    layout,
    '''inline const fui::KeyboardKey BOTTOM[] = {
    HUKS("fn", fui::KeyKind::Mode, fui::QWERTY_KEY_MODE, 2),
    HUK("/", "/", '/'), HUK("?", "?", '?'),
    HUKS("Space", fui::KeyKind::Space, fui::QWERTY_KEY_SPACE, 10),
    HUK(",", ",", ','), HUK(".", ".", '.'),
    HUKS("OK", fui::KeyKind::Ok, fui::QWERTY_KEY_ENTER, 2)};
''',
    '''inline const fui::KeyboardKey BOTTOM[] = {
    HUKS("fn", fui::KeyKind::Mode, fui::QWERTY_KEY_MODE, 2),
    HUK("/", "/", '/'), HUK("?", "?", '?'),
    HUKS("Space", fui::KeyKind::Space, fui::QWERTY_KEY_SPACE, 10),
    HUK(",", ",", ','), HUK(".", ".", '.'), HUK("-", "-", '-'),
    HUKS("OK", fui::KeyKind::Ok, fui::QWERTY_KEY_ENTER, 2)};
''',
)

replace_once(
    layout,
    '''inline const fui::KeyboardKey BOTTOM_LANG[] = {
    HUKS("fn", fui::KeyKind::Mode, fui::QWERTY_KEY_MODE, 2),
    HUKS(nullptr, fui::KeyKind::Lang, fui::QWERTY_KEY_LANG, 2),
    HUK("/", "/", '/'), HUK("?", "?", '?'),
    HUKS("Space", fui::KeyKind::Space, fui::QWERTY_KEY_SPACE, 8),
    HUK(",", ",", ','), HUK(".", ".", '.'),
    HUKS("OK", fui::KeyKind::Ok, fui::QWERTY_KEY_ENTER, 2)};
''',
    '''inline const fui::KeyboardKey BOTTOM_LANG[] = {
    HUKS("fn", fui::KeyKind::Mode, fui::QWERTY_KEY_MODE, 2),
    HUKS(nullptr, fui::KeyKind::Lang, fui::QWERTY_KEY_LANG, 2),
    HUK("/", "/", '/'), HUK("?", "?", '?'),
    HUKS("Space", fui::KeyKind::Space, fui::QWERTY_KEY_SPACE, 8),
    HUK(",", ",", ','), HUK(".", ".", '.'), HUK("-", "-", '-'),
    HUKS("OK", fui::KeyKind::Ok, fui::QWERTY_KEY_ENTER, 2)};
''',
)

replace_once(
    layout,
    '''inline const fui::KeyboardRow ROWS[] = {{NUM_ROW, 11, 0}, {ROW1, 11, 0}, {ROW2, 11, 0}, {ROW3, 10, 0}, {BOTTOM, 7, 0}};
inline const fui::KeyboardRow ROWS_LANG[] = {
    {NUM_ROW, 11, 0}, {ROW1, 11, 0}, {ROW2, 11, 0}, {ROW3, 10, 0}, {BOTTOM_LANG, 8, 0}};
inline const fui::KeyboardRow SHIFT_ROWS[] = {
    {NUM_ROW, 11, 0}, {SHIFT_ROW1, 11, 0}, {SHIFT_ROW2, 11, 0}, {SHIFT_ROW3, 10, 0}, {BOTTOM, 7, 0}};
inline const fui::KeyboardRow SHIFT_ROWS_LANG[] = {
    {NUM_ROW, 11, 0}, {SHIFT_ROW1, 11, 0}, {SHIFT_ROW2, 11, 0}, {SHIFT_ROW3, 10, 0}, {BOTTOM_LANG, 8, 0}};
''',
    '''inline const fui::KeyboardRow ROWS[] = {{NUM_ROW, 11, 0}, {ROW1, 11, 0}, {ROW2, 11, 0}, {ROW3, 10, 0}, {BOTTOM, 8, 0}};
inline const fui::KeyboardRow ROWS_LANG[] = {
    {NUM_ROW, 11, 0}, {ROW1, 11, 0}, {ROW2, 11, 0}, {ROW3, 10, 0}, {BOTTOM_LANG, 9, 0}};
inline const fui::KeyboardRow SHIFT_ROWS[] = {
    {NUM_ROW, 11, 0}, {SHIFT_ROW1, 11, 0}, {SHIFT_ROW2, 11, 0}, {SHIFT_ROW3, 10, 0}, {BOTTOM, 8, 0}};
inline const fui::KeyboardRow SHIFT_ROWS_LANG[] = {
    {NUM_ROW, 11, 0}, {SHIFT_ROW1, 11, 0}, {SHIFT_ROW2, 11, 0}, {SHIFT_ROW3, 10, 0}, {BOTTOM_LANG, 9, 0}};
''',
)

# -----------------------------------------------------------------------------
# New 32x36 Delete icon, converted directly from the user-supplied delete02.png.
# Existing Backspace and Shift icons remain untouched.
# -----------------------------------------------------------------------------
icons = "src/activities/util/HungarianKeyboardIcons.h"
icon_block = '''inline constexpr uint8_t FORWARD_DELETE_ICON_32X36[] = {
    0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF,
    0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF,
    0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFE, 0x00, 0x0F, 0xFF,
    0xFE, 0x00, 0x07, 0xFF, 0xFE, 0x7F, 0xE3, 0xFF, 0xFE, 0x7F, 0xF1, 0xFF,
    0xFE, 0x7F, 0xF8, 0xFF, 0xFE, 0x67, 0x9C, 0x7F, 0xFE, 0x67, 0x9E, 0x3F,
    0xFE, 0x73, 0x3F, 0x1F, 0xFE, 0x78, 0x7F, 0x8F, 0xFE, 0x7C, 0xFF, 0xCF,
    0xFE, 0x78, 0x7F, 0x8F, 0xFE, 0x73, 0x3F, 0x1F, 0xFE, 0x67, 0x9E, 0x3F,
    0xFE, 0x67, 0x9C, 0x7F, 0xFE, 0x7F, 0xF8, 0xFF, 0xFE, 0x7F, 0xF1, 0xFF,
    0xFE, 0x7F, 0xE3, 0xFF, 0xFE, 0x00, 0x07, 0xFF, 0xFE, 0x00, 0x0F, 0xFF,
    0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF,
    0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF,
    0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF,
};

inline const freeink::ui::BitmapRef forwardDeleteIcon63x36() {
  return freeink::ui::BitmapRef{FORWARD_DELETE_ICON_32X36, 32, 36, freeink::ui::BitmapFormat::Mask1, true};
}

'''
replace_once(
    icons,
    "// Keep the existing renderer API and #80 geometry unchanged. BitmapMode::Contain\n",
    icon_block + "// Keep the existing renderer API and #80 geometry unchanged. BitmapMode::Contain\n",
)

# -----------------------------------------------------------------------------
# Hungarian keyboard renderer: draw the new icon for forward delete and retain
# the original Backspace icon for QWERTY_KEY_BACKSPACE.
# Keep every row at the same 22-unit total after adding '-' to the bottom row.
# -----------------------------------------------------------------------------
layout_set = "src/activities/util/KeyboardLayoutSet.h"
replace_once(
    layout_set,
    '''    if (key.kind == KeyKind::Delete) {
      frame.target().bitmap(centeredRect(keyRect, Size{63, 36}),
                            keyboard_layouts::hu_keyboard::backspaceIcon63x36(), BitmapMode::Contain, ink);
      return;
    }
''',
    '''    if (key.kind == KeyKind::Delete) {
      const auto icon = key.value == keyboard_layouts::hu_keyboard::FORWARD_DELETE_KEY
                            ? keyboard_layouts::hu_keyboard::forwardDeleteIcon63x36()
                            : keyboard_layouts::hu_keyboard::backspaceIcon63x36();
      frame.target().bitmap(centeredRect(keyRect, Size{63, 36}), icon, BitmapMode::Contain, ink);
      return;
    }
''',
)
replace_once(
    layout_set,
    '''        if (key.kind == KeyKind::Mode || key.kind == KeyKind::Ok) return 3;
        if (key.kind == KeyKind::Space) return layoutRow.count == 7 ? 8 : 6;
''',
    '''        if (key.kind == KeyKind::Mode || key.kind == KeyKind::Ok) return 3;
        if (key.kind == KeyKind::Space) {
          if (layoutRow.count == 7) return 8;
          if (layoutRow.count == 9) return 4;
          return 6;
        }
''',
)

# -----------------------------------------------------------------------------
# Text editing semantics: Backspace still removes the previous UTF-8 code point;
# the new Hungarian Delete removes the next UTF-8 code point without moving the
# cursor. This preserves insertion editing exactly as before.
# -----------------------------------------------------------------------------
header = "src/activities/util/KeyboardEntryActivity.h"
replace_once(
    header,
    "  bool backspaceUtf8();\n",
    "  bool backspaceUtf8();\n  bool deleteForwardUtf8();\n",
)

cpp = "src/activities/util/KeyboardEntryActivity.cpp"
replace_once(
    cpp,
    '''bool KeyboardEntryActivity::backspaceUtf8() {
  if (text.empty() || cursorPos == 0) return false;
  const size_t prev = utf8Prev(text, cursorPos);
  text.erase(prev, cursorPos - prev);
  cursorPos = prev;
  return true;
}

''',
    '''bool KeyboardEntryActivity::backspaceUtf8() {
  if (text.empty() || cursorPos == 0) return false;
  const size_t prev = utf8Prev(text, cursorPos);
  text.erase(prev, cursorPos - prev);
  cursorPos = prev;
  return true;
}

bool KeyboardEntryActivity::deleteForwardUtf8() {
  if (text.empty() || cursorPos >= text.length()) return false;
  const size_t next = utf8Next(text, cursorPos);
  text.erase(cursorPos, next - cursorPos);
  return true;
}

''',
)
replace_once(
    cpp,
    "    case fui::QWERTY_KEY_BACKSPACE:\n",
    "    case keyboard_layouts::hu_keyboard::FORWARD_DELETE_KEY:\n"
    "      delPressCount = 0;\n"
    "      hintVisible = false;\n"
    "      return deleteForwardUtf8();\n"
    "    case fui::QWERTY_KEY_BACKSPACE:\n",
)

# Build identity only; no additional feature changes.
build_id = "src/CPHUNBuildId.h"
p = Path(build_id)
s = p.read_text(encoding="utf-8")
if "CPHUN-260916-135-EXP" in s and "CPHUN-260916-135-EXP-r2" not in s:
    p.write_text(s.replace("CPHUN-260916-135-EXP", "CPHUN-260916-135-EXP-r2", 1), encoding="utf-8")

print("CPHUN-135r2 keyboard-only Delete layout patch applied")
