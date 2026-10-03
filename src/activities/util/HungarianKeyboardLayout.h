#pragma once

#include <FreeInkUI.h>

namespace keyboard_layouts {
namespace hu_keyboard {

namespace fui = freeink::ui;

// CPHUN-135r2: separate forward-delete key used only by the Hungarian layout.
inline constexpr int16_t FORWARD_DELETE_KEY = -100;

#define HUK(label, output, value) \
  fui::KeyboardKey { label, output, fui::KeyKind::Normal, fui::StateNormal, value, 2, true, nullptr }
#define HUKW(label, output, value, units) \
  fui::KeyboardKey { label, output, fui::KeyKind::Normal, fui::StateNormal, value, units, true, nullptr }
#define HUKS(label, kind, value, units) \
  fui::KeyboardKey { label, nullptr, kind, fui::StateNormal, value, units, true, nullptr }

// CPHUN-75: 11 ordinary keys x 2 units = 22 units. On the X4 trial width
// of 462 px this gives an exact 21 px/unit, i.e. 42 px per ordinary key.
inline const fui::KeyboardKey NUM_ROW[] = {
    HUK("0", "0", '0'), HUK("1", "1", '1'), HUK("2", "2", '2'), HUK("3", "3", '3'),
    HUK("4", "4", '4'), HUK("5", "5", '5'), HUK("6", "6", '6'), HUK("7", "7", '7'),
    HUK("8", "8", '8'), HUK("9", "9", '9'),
    HUKS(nullptr, fui::KeyKind::Delete, FORWARD_DELETE_KEY, 2)};

inline const fui::KeyboardKey ROW1[] = {
    HUK("q", "q", 'q'), HUK("w", "w", 'w'), HUK("e", "e", 'e'), HUK("r", "r", 'r'),
    HUK("t", "t", 't'), HUK("z", "z", 'z'), HUK("u", "u", 'u'), HUK("i", "i", 'i'),
    HUK("o", "o", 'o'), HUK("p", "p", 'p'), HUK("ö", "ö", 1303)};

inline const fui::KeyboardKey ROW2[] = {
    HUK("a", "a", 'a'), HUK("s", "s", 's'), HUK("d", "d", 'd'), HUK("f", "f", 'f'),
    HUK("g", "g", 'g'), HUK("h", "h", 'h'), HUK("j", "j", 'j'), HUK("k", "k", 'k'),
    HUK("l", "l", 'l'), HUK("é", "é", 1301), HUK("á", "á", 1302)};

inline const fui::KeyboardKey ROW3[] = {
    HUKS(nullptr, fui::KeyKind::Shift, fui::QWERTY_KEY_SHIFT, 3),
    HUK("y", "y", 'y'), HUK("x", "x", 'x'), HUK("c", "c", 'c'), HUK("v", "v", 'v'),
    HUK("b", "b", 'b'), HUK("n", "n", 'n'), HUK("m", "m", 'm'), HUK("ü", "ü", 1304),
    HUKS("Del", fui::KeyKind::Delete, fui::QWERTY_KEY_BACKSPACE, 3)};

inline const fui::KeyboardKey SHIFT_ROW1[] = {
    HUK("Q", "Q", 'Q'), HUK("W", "W", 'W'), HUK("E", "E", 'E'), HUK("R", "R", 'R'),
    HUK("T", "T", 'T'), HUK("Z", "Z", 'Z'), HUK("U", "U", 'U'), HUK("I", "I", 'I'),
    HUK("O", "O", 'O'), HUK("P", "P", 'P'), HUK("Ö", "Ö", 1353)};

inline const fui::KeyboardKey SHIFT_ROW2[] = {
    HUK("A", "A", 'A'), HUK("S", "S", 'S'), HUK("D", "D", 'D'), HUK("F", "F", 'F'),
    HUK("G", "G", 'G'), HUK("H", "H", 'H'), HUK("J", "J", 'J'), HUK("K", "K", 'K'),
    HUK("L", "L", 'L'), HUK("É", "É", 1351), HUK("Á", "Á", 1352)};

inline const fui::KeyboardKey SHIFT_ROW3[] = {
    HUKS(nullptr, fui::KeyKind::Shift, fui::QWERTY_KEY_SHIFT, 3),
    HUK("Y", "Y", 'Y'), HUK("X", "X", 'X'), HUK("C", "C", 'C'), HUK("V", "V", 'V'),
    HUK("B", "B", 'B'), HUK("N", "N", 'N'), HUK("M", "M", 'M'), HUK("Ü", "Ü", 1354),
    HUKS("Del", fui::KeyKind::Delete, fui::QWERTY_KEY_BACKSPACE, 3)};

// Bottom rows total exactly 22 units. The ordinary controls are 2 units
// (42 px on X4); Space is 5 keys wide without globe and 4 keys wide with it.
inline const fui::KeyboardKey BOTTOM[] = {
    HUKS("fn", fui::KeyKind::Mode, fui::QWERTY_KEY_MODE, 2),
    HUK("/", "/", '/'), HUK("?", "?", '?'),
    HUKS("Space", fui::KeyKind::Space, fui::QWERTY_KEY_SPACE, 10),
    HUK(",", ",", ','), HUK(".", ".", '.'), HUK("-", "-", '-'),
    HUKS("OK", fui::KeyKind::Ok, fui::QWERTY_KEY_ENTER, 2)};

inline const fui::KeyboardKey BOTTOM_LANG[] = {
    HUKS("fn", fui::KeyKind::Mode, fui::QWERTY_KEY_MODE, 2),
    HUKS(nullptr, fui::KeyKind::Lang, fui::QWERTY_KEY_LANG, 2),
    HUK("/", "/", '/'), HUK("?", "?", '?'),
    HUKS("Space", fui::KeyKind::Space, fui::QWERTY_KEY_SPACE, 8),
    HUK(",", ",", ','), HUK(".", ".", '.'), HUK("-", "-", '-'),
    HUKS("OK", fui::KeyKind::Ok, fui::QWERTY_KEY_ENTER, 2)};

inline const fui::KeyboardKey SYMBOL_ROW1[] = {
    HUK("1", "1", '1'), HUK("2", "2", '2'), HUK("3", "3", '3'), HUK("4", "4", '4'),
    HUK("5", "5", '5'), HUK("6", "6", '6'), HUK("7", "7", '7'), HUK("8", "8", '8'),
    HUK("9", "9", '9'), HUK("0", "0", '0'),
    HUKS("Del", fui::KeyKind::Delete, fui::QWERTY_KEY_BACKSPACE, 2)};
inline const fui::KeyboardKey SYMBOL_ROW2[] = {
    HUK("\\", "\\", '\\'), HUK(":", ":", ':'), HUK(";", ";", ';'), HUK("(", "(", '('), HUK(")", ")", ')'),
    HUK("€", "€", 1401), HUK("$", "$", '$'), HUK("&", "&", '&'), HUK("@", "@", '@'),
    HUK("„", "„", 1402), HUK("”", "”", 1403)
};
inline const fui::KeyboardKey SYMBOL_EXTRA_ROW[] = {
    HUK("[", "[", '['), HUK("]", "]", ']'), HUK("{", "{", '{'), HUK("}", "}", '}'),
    HUK("–", "–", 1410), HUK("+", "+", '+'), HUK("*", "*", '*'), HUK("§", "§", 1413),
    HUK("°", "°", 1414), HUK("«", "«", 1415), HUK("»", "»", 1416)
};
inline const fui::KeyboardKey SYMBOL_ROW3[] = {
    HUKS(nullptr, fui::KeyKind::Shift, fui::QWERTY_KEY_SHIFT, 3),
    HUK("=", "=", '='), HUK("!", "!", '!'), HUK("'", "'", '\''), HUK("\"", "\"", '"'),
    HUK("#", "#", '#'), HUKW("…", "…", 1404, 3), HUK("<", "<", '<'), HUK(">", ">", '>'),
    HUKS(nullptr, fui::KeyKind::Delete, fui::QWERTY_KEY_BACKSPACE, 3)
};

inline const fui::KeyboardKey SYMBOL2_ROW1[] = {
    HUK("[", "[", '['), HUK("]", "]", ']'), HUK("{", "{", '{'), HUK("}", "}", '}'), HUK("<", "<", '<'),
    HUK(">", ">", '>'), HUK("^", "^", '^'), HUK("*", "*", '*'), HUK("+", "+", '+'), HUK("=", "=", '='),
    HUK("_", "_", '_')};
inline const fui::KeyboardKey SYMBOL2_ROW2[] = {
    HUK("\\", "\\", '\\'), HUK("|", "|", '|'), HUK("~", "~", '~'), HUK("`", "`", '`'), HUK("%", "%", '%'),
    HUK("–", "–", 1410), HUK("—", "—", 1411), HUK("±", "±", 1412), HUK("§", "§", 1413),
    HUK("°", "°", 1414), HUK("#", "#", '#')};
inline const fui::KeyboardKey SYMBOL2_ROW3[] = {
    HUKS(nullptr, fui::KeyKind::Shift, fui::QWERTY_KEY_SHIFT, 3),
    HUK("?", "?", '?'), HUK("!", "!", '!'), HUK("'", "'", '\''), HUK("\"", "\"", '"'),
    HUK(":", ":", ':'), HUK(";", ";", ';'),
    HUKS(nullptr, fui::KeyKind::Delete, fui::QWERTY_KEY_BACKSPACE, 3)};

inline const fui::KeyboardKey SYMBOL_BOTTOM[] = {
    HUKS("fn", fui::KeyKind::Mode, fui::QWERTY_KEY_MODE, 2),
    HUK("/", "/", '/'), HUK("?", "?", '?'),
    HUKS("Space", fui::KeyKind::Space, fui::QWERTY_KEY_SPACE, 10),
    HUK(",", ",", ','), HUK(".", ".", '.'),
    HUKS("OK", fui::KeyKind::Ok, fui::QWERTY_KEY_ENTER, 2)};

inline const fui::KeyboardRow ROWS[] = {{NUM_ROW, 11, 0}, {ROW1, 11, 0}, {ROW2, 11, 0}, {ROW3, 10, 0}, {BOTTOM, 8, 0}};
inline const fui::KeyboardRow ROWS_LANG[] = {
    {NUM_ROW, 11, 0}, {ROW1, 11, 0}, {ROW2, 11, 0}, {ROW3, 10, 0}, {BOTTOM_LANG, 9, 0}};
inline const fui::KeyboardRow SHIFT_ROWS[] = {
    {NUM_ROW, 11, 0}, {SHIFT_ROW1, 11, 0}, {SHIFT_ROW2, 11, 0}, {SHIFT_ROW3, 10, 0}, {BOTTOM, 8, 0}};
inline const fui::KeyboardRow SHIFT_ROWS_LANG[] = {
    {NUM_ROW, 11, 0}, {SHIFT_ROW1, 11, 0}, {SHIFT_ROW2, 11, 0}, {SHIFT_ROW3, 10, 0}, {BOTTOM_LANG, 9, 0}};
inline const fui::KeyboardRow SYMBOL_ROWS[] = {
    {NUM_ROW, 11, 0}, {SYMBOL_ROW2, 11, 0}, {SYMBOL_EXTRA_ROW, 11, 0}, {SYMBOL_ROW3, 10, 0},
    {SYMBOL_BOTTOM, 7, 0}};
inline const fui::KeyboardRow SYMBOL2_ROWS[] = {
    {NUM_ROW, 11, 0}, {SYMBOL2_ROW1, 11, 0}, {SYMBOL2_ROW2, 11, 0}, {SYMBOL2_ROW3, 10, 0},
    {SYMBOL_BOTTOM, 7, 0}};

inline const fui::KeyboardLayout LAYOUT{ROWS, 5};
inline const fui::KeyboardLayout LAYOUT_LANG{ROWS_LANG, 5};
inline const fui::KeyboardLayout SHIFT_LAYOUT{SHIFT_ROWS, 5};
inline const fui::KeyboardLayout SHIFT_LAYOUT_LANG{SHIFT_ROWS_LANG, 5};
inline const fui::KeyboardLayout SYMBOL_LAYOUT{SYMBOL_ROWS, 5};
inline const fui::KeyboardLayout SYMBOL2_LAYOUT{SYMBOL2_ROWS, 5};

inline const fui::KeyboardLayout& layout(const bool shifted, const bool symbols, const bool langKey) {
  if (symbols) return shifted ? SYMBOL2_LAYOUT : SYMBOL_LAYOUT;
  if (shifted) return langKey ? SHIFT_LAYOUT_LANG : SHIFT_LAYOUT;
  return langKey ? LAYOUT_LANG : LAYOUT;
}

inline bool isHungarianLetterLayout(const fui::KeyboardLayout& current) {
  return &current == &LAYOUT || &current == &LAYOUT_LANG || &current == &SHIFT_LAYOUT ||
         &current == &SHIFT_LAYOUT_LANG;
}

inline bool isHungarianLayout(const fui::KeyboardLayout& current) {
  return isHungarianLetterLayout(current) || &current == &SYMBOL_LAYOUT || &current == &SYMBOL2_LAYOUT;
}

inline bool isShiftedLetterLayout(const fui::KeyboardLayout& current) {
  return &current == &SHIFT_LAYOUT || &current == &SHIFT_LAYOUT_LANG;
}

inline const char* altOutputFor(const fui::KeyboardLayout& current, const int16_t value) {
  if (!isHungarianLetterLayout(current)) return nullptr;
  switch (value) {
    case '1': return "!"; case '2': return "@"; case '3': return "#"; case '4': return "$";
    case '5': return "%"; case '6': return "^"; case '7': return "&"; case '8': return "*";
    case '9': return "("; case '0': return ")"; case '-': return "_"; default: break;
  }
  if (isShiftedLetterLayout(current)) {
    switch (value) {
      case 'A': return "Á"; case 'E': return "É"; case 'I': return "Í"; case 'O': return "Ó";
      case 'U': return "Ú"; case 1353: return "Ő"; case 1354: return "Ű"; default: return nullptr;
    }
  }
  switch (value) {
    case 'a': return "á"; case 'e': return "é"; case 'i': return "í"; case 'o': return "ó";
    case 'u': return "ú"; case 1303: return "ő"; case 1304: return "ű"; default: return nullptr;
  }
}

#undef HUK
#undef HUKW
#undef HUKS

}  // namespace hu_keyboard
}  // namespace keyboard_layouts
