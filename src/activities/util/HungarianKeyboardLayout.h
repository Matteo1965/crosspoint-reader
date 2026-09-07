#pragma once

#include <FreeInkUI.h>

namespace keyboard_layouts {
namespace hu_keyboard {

namespace fui = freeink::ui;

#define HUK(label, output, value) \
  fui::KeyboardKey { label, output, fui::KeyKind::Normal, fui::StateNormal, value, 2, true, nullptr }
#define HUKA(label, output, value, alt) \
  fui::KeyboardKey { label, output, fui::KeyKind::Normal, fui::StateNormal, value, 2, true, alt }
#define HUKW(label, output, value, units) \
  fui::KeyboardKey { label, output, fui::KeyKind::Normal, fui::StateNormal, value, units, true, nullptr }
#define HUKS(label, kind, value, units) \
  fui::KeyboardKey { label, nullptr, kind, fui::StateNormal, value, units, true, nullptr }

inline const fui::KeyboardKey NUM_ROW[] = {
    HUKA("1", "1", '1', "!"), HUKA("2", "2", '2', "@"), HUKA("3", "3", '3', "#"),
    HUKA("4", "4", '4', "$"), HUKA("5", "5", '5', "%"), HUKA("6", "6", '6', "^"),
    HUKA("7", "7", '7', "&"), HUKA("8", "8", '8', "*"), HUKA("9", "9", '9', "("),
    HUKA("0", "0", '0', ")"), HUKA("-", "-", '-', "_")};

inline const fui::KeyboardKey ROW1[] = {
    HUK("q", "q", 'q'), HUK("w", "w", 'w'), HUKA("e", "e", 'e', "é"), HUK("r", "r", 'r'),
    HUK("t", "t", 't'), HUK("z", "z", 'z'), HUKA("u", "u", 'u', "ú"), HUKA("i", "i", 'i', "í"),
    HUKA("o", "o", 'o', "ó"), HUK("p", "p", 'p'), HUKA("ö", "ö", 1303, "ő")};

inline const fui::KeyboardKey ROW2[] = {
    HUKA("a", "a", 'a', "á"), HUK("s", "s", 's'), HUK("d", "d", 'd'), HUK("f", "f", 'f'),
    HUK("g", "g", 'g'), HUK("h", "h", 'h'), HUK("j", "j", 'j'), HUK("k", "k", 'k'),
    HUK("l", "l", 'l'), HUK("é", "é", 1301), HUK("á", "á", 1302)};

inline const fui::KeyboardKey ROW3[] = {
    HUKS("Shift", fui::KeyKind::Shift, fui::QWERTY_KEY_SHIFT, 3),
    HUK("y", "y", 'y'), HUK("x", "x", 'x'), HUK("c", "c", 'c'), HUK("v", "v", 'v'),
    HUK("b", "b", 'b'), HUK("n", "n", 'n'), HUK("m", "m", 'm'), HUKA("ü", "ü", 1304, "ű"),
    HUKS("Del", fui::KeyKind::Delete, fui::QWERTY_KEY_BACKSPACE, 3)};

inline const fui::KeyboardKey SHIFT_ROW1[] = {
    HUK("Q", "Q", 'Q'), HUK("W", "W", 'W'), HUKA("E", "E", 'E', "É"), HUK("R", "R", 'R'),
    HUK("T", "T", 'T'), HUK("Z", "Z", 'Z'), HUKA("U", "U", 'U', "Ú"), HUKA("I", "I", 'I', "Í"),
    HUKA("O", "O", 'O', "Ó"), HUK("P", "P", 'P'), HUKA("Ö", "Ö", 1353, "Ő")};

inline const fui::KeyboardKey SHIFT_ROW2[] = {
    HUKA("A", "A", 'A', "Á"), HUK("S", "S", 'S'), HUK("D", "D", 'D'), HUK("F", "F", 'F'),
    HUK("G", "G", 'G'), HUK("H", "H", 'H'), HUK("J", "J", 'J'), HUK("K", "K", 'K'),
    HUK("L", "L", 'L'), HUK("É", "É", 1351), HUK("Á", "Á", 1352)};

inline const fui::KeyboardKey SHIFT_ROW3[] = {
    HUKS("Shift", fui::KeyKind::Shift, fui::QWERTY_KEY_SHIFT, 3),
    HUK("Y", "Y", 'Y'), HUK("X", "X", 'X'), HUK("C", "C", 'C'), HUK("V", "V", 'V'),
    HUK("B", "B", 'B'), HUK("N", "N", 'N'), HUK("M", "M", 'M'), HUKA("Ü", "Ü", 1354, "Ű"),
    HUKS("Del", fui::KeyKind::Delete, fui::QWERTY_KEY_BACKSPACE, 3)};

inline const fui::KeyboardKey BOTTOM[] = {
    HUKS("?123", fui::KeyKind::Mode, fui::QWERTY_KEY_MODE, 4), HUK(",", ",", ','),
    HUKS("Space", fui::KeyKind::Space, fui::QWERTY_KEY_SPACE, 10), HUK(".", ".", '.'),
    HUKS("OK", fui::KeyKind::Ok, fui::QWERTY_KEY_ENTER, 4)};

// When CrossPoint exposes more than one enabled layout, preserve the existing
// globe switch while keeping the punctuation keys directly accessible.
inline const fui::KeyboardKey BOTTOM_LANG[] = {
    HUKS("?123", fui::KeyKind::Mode, fui::QWERTY_KEY_MODE, 4), HUK(",", ",", ','),
    HUKS(nullptr, fui::KeyKind::Lang, fui::QWERTY_KEY_LANG, 2),
    HUKS("Space", fui::KeyKind::Space, fui::QWERTY_KEY_SPACE, 8), HUK(".", ".", '.'),
    HUKS("OK", fui::KeyKind::Ok, fui::QWERTY_KEY_ENTER, 4)};

inline const fui::KeyboardKey SYMBOL_ROW1[] = {
    HUK("1", "1", '1'), HUK("2", "2", '2'), HUK("3", "3", '3'), HUK("4", "4", '4'),
    HUK("5", "5", '5'), HUK("6", "6", '6'), HUK("7", "7", '7'), HUK("8", "8", '8'),
    HUK("9", "9", '9'), HUK("0", "0", '0'), HUK("-", "-", '-')};
inline const fui::KeyboardKey SYMBOL_ROW2[] = {
    HUK("/", "/", '/'), HUK(":", ":", ':'), HUK(";", ";", ';'), HUK("(", "(", '('), HUK(")", ")", ')'),
    HUK("€", "€", 1401), HUK("$", "$", '$'), HUK("&", "&", '&'), HUK("@", "@", '@'),
    HUK("„", "„", 1402), HUK("”", "”", 1403)};
inline const fui::KeyboardKey SYMBOL_ROW3[] = {
    HUKS("#+=", fui::KeyKind::Shift, fui::QWERTY_KEY_SHIFT, 4), HUK(".", ".", '.'), HUK(",", ",", ','),
    HUK("?", "?", '?'), HUK("!", "!", '!'), HUK("'", "'", '\''), HUK("\"", "\"", '"'),
    HUK("#", "#", '#'), HUK("…", "…", 1404), HUKS("Del", fui::KeyKind::Delete, fui::QWERTY_KEY_BACKSPACE, 4)};

inline const fui::KeyboardKey SYMBOL2_ROW1[] = {
    HUK("[", "[", '['), HUK("]", "]", ']'), HUK("{", "{", '{'), HUK("}", "}", '}'), HUK("<", "<", '<'),
    HUK(">", ">", '>'), HUK("^", "^", '^'), HUK("*", "*", '*'), HUK("+", "+", '+'), HUK("=", "=", '='),
    HUK("_", "_", '_')};
inline const fui::KeyboardKey SYMBOL2_ROW2[] = {
    HUK("\\", "\\", '\\'), HUK("|", "|", '|'), HUK("~", "~", '~'), HUK("`", "`", '`'), HUK("%", "%", '%'),
    HUK("–", "–", 1410), HUK("—", "—", 1411), HUK("±", "±", 1412), HUK("§", "§", 1413),
    HUK("°", "°", 1414), HUK("#", "#", '#')};
inline const fui::KeyboardKey SYMBOL2_ROW3[] = {
    HUKS("123", fui::KeyKind::Shift, fui::QWERTY_KEY_SHIFT, 4), HUK(".", ".", '.'), HUK(",", ",", ','),
    HUK("?", "?", '?'), HUK("!", "!", '!'), HUK("'", "'", '\''), HUK("\"", "\"", '"'),
    HUK(":", ":", ':'), HUK(";", ";", ';'), HUKS("Del", fui::KeyKind::Delete, fui::QWERTY_KEY_BACKSPACE, 4)};

inline const fui::KeyboardKey SYMBOL_BOTTOM[] = {
    HUKS("ABC", fui::KeyKind::Mode, fui::QWERTY_KEY_MODE, 4), HUK(",", ",", ','),
    HUKS("Space", fui::KeyKind::Space, fui::QWERTY_KEY_SPACE, 10), HUK(".", ".", '.'),
    HUKS("OK", fui::KeyKind::Ok, fui::QWERTY_KEY_ENTER, 4)};

inline const fui::KeyboardRow ROWS[] = {{NUM_ROW, 11, 0}, {ROW1, 11, 0}, {ROW2, 11, 0}, {ROW3, 10, 0}, {BOTTOM, 5, 0}};
inline const fui::KeyboardRow ROWS_LANG[] = {
    {NUM_ROW, 11, 0}, {ROW1, 11, 0}, {ROW2, 11, 0}, {ROW3, 10, 0}, {BOTTOM_LANG, 6, 0}};
inline const fui::KeyboardRow SHIFT_ROWS[] = {
    {NUM_ROW, 11, 0}, {SHIFT_ROW1, 11, 0}, {SHIFT_ROW2, 11, 0}, {SHIFT_ROW3, 10, 0}, {BOTTOM, 5, 0}};
inline const fui::KeyboardRow SHIFT_ROWS_LANG[] = {
    {NUM_ROW, 11, 0}, {SHIFT_ROW1, 11, 0}, {SHIFT_ROW2, 11, 0}, {SHIFT_ROW3, 10, 0}, {BOTTOM_LANG, 6, 0}};
inline const fui::KeyboardRow SYMBOL_ROWS[] = {
    {SYMBOL_ROW1, 11, 0}, {SYMBOL_ROW2, 11, 0}, {SYMBOL_ROW3, 10, 0}, {SYMBOL_BOTTOM, 5, 0}};
inline const fui::KeyboardRow SYMBOL2_ROWS[] = {
    {SYMBOL2_ROW1, 11, 0}, {SYMBOL2_ROW2, 11, 0}, {SYMBOL2_ROW3, 10, 0}, {SYMBOL_BOTTOM, 5, 0}};

inline const fui::KeyboardLayout LAYOUT{ROWS, 5};
inline const fui::KeyboardLayout LAYOUT_LANG{ROWS_LANG, 5};
inline const fui::KeyboardLayout SHIFT_LAYOUT{SHIFT_ROWS, 5};
inline const fui::KeyboardLayout SHIFT_LAYOUT_LANG{SHIFT_ROWS_LANG, 5};
inline const fui::KeyboardLayout SYMBOL_LAYOUT{SYMBOL_ROWS, 4};
inline const fui::KeyboardLayout SYMBOL2_LAYOUT{SYMBOL2_ROWS, 4};

inline const fui::KeyboardLayout& layout(const bool shifted, const bool symbols, const bool langKey) {
  if (symbols) return shifted ? SYMBOL2_LAYOUT : SYMBOL_LAYOUT;
  if (shifted) return langKey ? SHIFT_LAYOUT_LANG : SHIFT_LAYOUT;
  return langKey ? LAYOUT_LANG : LAYOUT;
}

#undef HUK
#undef HUKA
#undef HUKW
#undef HUKS

}  // namespace hu_keyboard
}  // namespace keyboard_layouts
