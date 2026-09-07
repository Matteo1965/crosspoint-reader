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

// The SDK currently defines ids 0..8. Keep Hungarian app-local until FreeInk
// grows an upstream Hungarian id; the proxy below intercepts it before the SDK
// switch sees it.
inline constexpr freeink::ui::KeyboardLayoutId HUNGARIAN_ID =
    static_cast<freeink::ui::KeyboardLayoutId>(9);

// Table position is the persisted bit assignment. Keep existing rows in place
// and append new layouts so SDK enum changes cannot reinterpret saved masks.
inline constexpr LayoutInfo ALL[] = {
    {freeink::ui::KeyboardLayoutId::QwertyEn, Language::EN},
    {freeink::ui::KeyboardLayoutId::AzertyFr, Language::FR},
    {freeink::ui::KeyboardLayoutId::QwertzDe, Language::DE},
    {freeink::ui::KeyboardLayoutId::SpanishEs, Language::ES},
    {freeink::ui::KeyboardLayoutId::CyrillicRu, Language::RU},
    {freeink::ui::KeyboardLayoutId::CyrillicUk, Language::UK},
    {freeink::ui::KeyboardLayoutId::CyrillicBe, Language::BE},
    {freeink::ui::KeyboardLayoutId::CyrillicKk, Language::KK},
    {freeink::ui::KeyboardLayoutId::HebrewIl, Language::HE},
    {HUNGARIAN_ID, Language::HU},
};
inline constexpr uint8_t COUNT = sizeof(ALL) / sizeof(ALL[0]);
static_assert(COUNT <= 16, "keyboard layout mask is uint16_t");

inline constexpr uint16_t bitAt(const uint8_t i) { return static_cast<uint16_t>(1u << i); }
// Symbol layers have no Latin letters, so credentials and URLs require at
// least one of these layouts to remain enabled.
inline constexpr uint16_t LATIN_BITS = bitAt(0) | bitAt(1) | bitAt(2) | bitAt(3) | bitAt(9);

uint16_t enabled();
freeink::ui::KeyboardLayoutId startingLayout();
freeink::ui::KeyboardLayoutId next(freeink::ui::KeyboardLayoutId current);

}  // namespace keyboard_layouts

// CrossPoint uses FreeInkUI's public data-driven KeyboardLayout API for the
// Hungarian tables. Redirect only calls made after this header is included;
// all SDK declarations have already been parsed, and all ordinary ids still
// delegate to the unmodified SDK implementation.
namespace freeink {
namespace ui {
inline const KeyboardLayout& builtinKeyboardLayoutCphun(const KeyboardLayoutId id, const bool shifted = false,
                                                        const bool symbols = false, const bool numberRow = false,
                                                        const bool langKey = false) {
  if (id == keyboard_layouts::HUNGARIAN_ID) {
    (void)numberRow;  // Hungarian's approved layout always carries its 11-key number row.
    return keyboard_layouts::hu_keyboard::layout(shifted, symbols, langKey);
  }
  return builtinKeyboardLayout(id, shifted, symbols, numberRow, langKey);
}
}  // namespace ui
}  // namespace freeink

#define builtinKeyboardLayout builtinKeyboardLayoutCphun
