#pragma once

#include <FreeInkUI.h>
#include <I18n.h>

#include <cstdint>

#include "HungarianKeyboardLayout.h"

namespace keyboard_layouts {

struct LayoutInfo {
  freeink::ui::KeyboardLayoutId id;
  Language language;
};

// Table position is the persisted bit assignment. Keep existing rows in place
// and append new layouts so SDK enum changes cannot reinterpret saved masks.
inline constexpr freeink::ui::KeyboardLayoutId HUNGARIAN_ID =
    static_cast<freeink::ui::KeyboardLayoutId>(9);

// Only layouts with matching installed hyphenation patterns and an actual
// keyboard: English, French, German, Spanish and Hungarian.
inline constexpr LayoutInfo ALL[] = {
    {freeink::ui::KeyboardLayoutId::QwertyEn, Language::EN},
    {freeink::ui::KeyboardLayoutId::AzertyFr, Language::FR},
    {freeink::ui::KeyboardLayoutId::QwertzDe, Language::DE},
    {freeink::ui::KeyboardLayoutId::SpanishEs, Language::ES},
    {HUNGARIAN_ID, Language::HU},
};
inline constexpr uint8_t COUNT = sizeof(ALL) / sizeof(ALL[0]);
static_assert(COUNT <= 16, "keyboard layout mask is uint16_t");

inline constexpr uint16_t bitAt(const uint8_t i) { return static_cast<uint16_t>(1u << i); }
// Symbol layers have no Latin letters, so credentials and URLs require at
// least one of these layouts to remain enabled.
inline constexpr uint16_t LATIN_BITS = bitAt(0) | bitAt(1) | bitAt(2) | bitAt(3) | bitAt(4);

uint16_t enabled();
freeink::ui::KeyboardLayoutId startingLayout();
freeink::ui::KeyboardLayoutId next(freeink::ui::KeyboardLayoutId current);

}  // namespace keyboard_layouts

// CPHUN-224's keyboard layers, without its X4-specific coordinate overrides.
namespace freeink::ui {
inline const KeyboardLayout& builtinKeyboardLayoutHuPicco(const KeyboardLayoutId id,
    const bool shifted = false, const bool symbols = false,
    const bool numberRow = false, const bool langKey = false) {
  if (id == keyboard_layouts::HUNGARIAN_ID) {
    (void)numberRow;
    return keyboard_layouts::hu_keyboard::layout(shifted, symbols, langKey);
  }
  return builtinKeyboardLayout(id, shifted, symbols, numberRow, langKey);
}
inline const char* keyboardAltOutputHuPicco(const KeyboardLayout& layout, const int16_t value) {
  if (const char* out = keyboard_layouts::hu_keyboard::altOutputFor(layout, value)) return out;
  return keyboardAltOutputFor(layout, value);
}
}  // namespace freeink::ui
