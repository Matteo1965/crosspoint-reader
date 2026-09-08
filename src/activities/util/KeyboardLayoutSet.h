#pragma once

#include <FreeInkUI.h>
#include <I18n.h>

#include <cstdint>

#include "HungarianKeyboardIconsSafe.h"
#include "HungarianKeyboardLayout.h"

namespace keyboard_layouts {

struct LayoutInfo {
  freeink::ui::KeyboardLayoutId id;
  Language language;
};

inline constexpr freeink::ui::KeyboardLayoutId HUNGARIAN_ID =
    static_cast<freeink::ui::KeyboardLayoutId>(9);

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
inline constexpr uint16_t LATIN_BITS = bitAt(0) | bitAt(1) | bitAt(2) | bitAt(3) | bitAt(9);

uint16_t enabled();
freeink::ui::KeyboardLayoutId startingLayout();
freeink::ui::KeyboardLayoutId next(freeink::ui::KeyboardLayoutId current);

}  // namespace keyboard_layouts

namespace freeink {
namespace ui {
inline const KeyboardLayout& builtinKeyboardLayoutCphun(const KeyboardLayoutId id, const bool shifted = false,
                                                        const bool symbols = false, const bool numberRow = false,
                                                        const bool langKey = false) {
  if (id == keyboard_layouts::HUNGARIAN_ID) {
    (void)numberRow;
    return keyboard_layouts::hu_keyboard::layout(shifted, symbols, langKey);
  }
  return builtinKeyboardLayout(id, shifted, symbols, numberRow, langKey);
}

inline const char* keyboardAltOutputForCphun(const KeyboardLayout& layout, const int16_t value) {
  if (const char* huAlt = keyboard_layouts::hu_keyboard::altOutputFor(layout, value)) return huAlt;
  return keyboardAltOutputFor(layout, value);
}

// CPHUN-79 X4 geometry: all Hungarian letter rows share the same absolute
// horizontal anchors. The first drawable pixel is x=15 and the last is x=466,
// so the key band is 452 px wide in half-open Rect coordinates [15,467).
// Ordinary keys stay equal at 41 px. Shift/Backspace/fn/OK are equal at 62 px.
// The 11-key rows use one neutral 1 px center spacer to fill 452 exactly.
template <size_t MaxInteractions>
void keyboardCphun(Frame<MaxInteractions>& frame, Rect rect, const KeyboardProps& props) {
  if (!props.layout || !keyboard_layouts::hu_keyboard::isHungarianLayout(*props.layout)) {
    keyboard(frame, rect, props);
    return;
  }

  // X4 portrait keyboard band: use the measured device coordinates directly.
  if (rect.width >= 440 && rect.width <= 470) {
    rect.x = 15;
    rect.width = 452;
  }

  if (!keyboard_layouts::hu_keyboard::isHungarianLetterLayout(*props.layout)) {
    keyboard(frame, rect, props);
    return;
  }

  KeyboardProps huProps = props;
  huProps.shiftLabel = nullptr;
  huProps.modeLabel = "fn";
  huProps.padding = Insets{0, 0, 0, 0};

  if (!huProps.layout->rows || huProps.layout->rowCount == 0) return;
  StyleSet styles = huProps.keyStyles.unset() ? defaultButtonStyles() : huProps.keyStyles;
  if (huProps.keyRadius > 0) setStyleRadius(styles, huProps.keyRadius);
  TextStyle keyText = huProps.labelText;
  keyText.align = TextAlign::Center;
  keyText.maxLines = 1;
  rect = rect.inset(huProps.padding);
  if (rect.empty() || rect.width < 10 || rect.height < 10) return;
  const int16_t gap = huProps.gap < 0 ? 0 : huProps.gap;
  const int16_t rowH =
      static_cast<int16_t>((rect.height - gap * (huProps.layout->rowCount - 1)) / huProps.layout->rowCount);
  int16_t logicalIndex = 0;

  auto actionFor = [&](KeyKind kind) {
    if (kind == KeyKind::Shift && huProps.shiftAction != NO_ACTION) return huProps.shiftAction;
    if (kind == KeyKind::Mode && huProps.modeAction != NO_ACTION) return huProps.modeAction;
    if (kind == KeyKind::Lang && huProps.langAction != NO_ACTION) return huProps.langAction;
    if (kind == KeyKind::Delete && huProps.deleteAction != NO_ACTION) return huProps.deleteAction;
    if (kind == KeyKind::Ok && huProps.okAction != NO_ACTION) return huProps.okAction;
    return huProps.keyAction;
  };

  int16_t rowHitOverflow = 0;
  auto drawKey = [&](Rect keyRect, const KeyboardKey& key, int16_t selectedIndex) {
    State state = StateNormal;
    if (huProps.selectedIndex == selectedIndex) state |= huProps.inactiveSelection ? StateFocused : StateSelected;
    if (!key.enabled || key.kind == KeyKind::Disabled) state |= StateDisabled;
    const ActionId action = actionFor(key.kind);
    ButtonProps bp;
    bp.label = (key.kind == KeyKind::Space || key.kind == KeyKind::Delete || key.kind == KeyKind::Lang ||
                key.kind == KeyKind::Shift)
                   ? nullptr
                   : key.label;
    if (key.kind == KeyKind::Ok && huProps.okLabel) bp.label = huProps.okLabel;
    if (key.kind == KeyKind::Mode && huProps.modeLabel) bp.label = huProps.modeLabel;
    bp.action = action;
    bp.value = key.value;
    bp.inputMask = huProps.inputMask;
    bp.state = state;
    bp.text = keyText;
    bp.styles = styles;
    bp.minTouchSize = huProps.minTouchSize;
    bp.hitPadding.bottom = rowHitOverflow;
    bp.radius = huProps.keyRadius;
    bp.enabled = key.enabled && key.kind != KeyKind::Disabled;
    button(frame, keyRect, bp);

    const Paint ink = styles.resolve(frame.stateFor(action, key.value, state)).foreground;

    if (key.kind == KeyKind::Shift) {
      // Render inside a smaller safe box. The backing mask is 64 px wide and
      // byte-aligned, preventing the 63 px row-padding artifact seen on device.
      frame.target().bitmap(centeredRect(keyRect, Size{60, 32}),
                            keyboard_layouts::hu_keyboard::shiftIconSafe64x36(), BitmapMode::Contain, ink);
      return;
    }

    if (key.kind == KeyKind::Delete) {
      frame.target().bitmap(centeredRect(keyRect, Size{60, 32}),
                            keyboard_layouts::hu_keyboard::backspaceIconSafe64x36(), BitmapMode::Contain, ink);
      return;
    }

    if (key.kind == KeyKind::Lang) {
      const int16_t lh = frame.target().lineHeight(keyText.font);
      const int16_t desired = static_cast<int16_t>(lh + lh / 8);
      int16_t iconSize = static_cast<int16_t>(((desired + 8) / 16) * 16);
      if (iconSize < 16) iconSize = 16;
      const int16_t maxSize = keyRect.height < keyRect.width ? keyRect.height : keyRect.width;
      while (iconSize > maxSize && iconSize > 16) iconSize = static_cast<int16_t>(iconSize - 16);
      if (iconSize > maxSize) iconSize = maxSize;
      frame.target().bitmap(centeredRect(keyRect, Size{iconSize, iconSize}), lucideGlobeIcon32(), BitmapMode::Contain, ink);
      return;
    }

    if (key.kind == KeyKind::Normal && key.alt) {
      TextStyle altStyle = huProps.altText;
      altStyle.align = TextAlign::Right;
      altStyle.maxLines = 1;
      altStyle.color = ink.color;
      const int16_t altLh = frame.target().lineHeight(altStyle.font);
      frame.target().text(Rect{static_cast<int16_t>(keyRect.x + 2), static_cast<int16_t>(keyRect.y + 2),
                               static_cast<int16_t>(keyRect.width - 3), altLh},
                          key.alt, altStyle);
      return;
    }

    if (key.kind != KeyKind::Space) return;
    const int16_t glyphW = static_cast<int16_t>(keyRect.width * 4 / 5);
    const Rect glyph{static_cast<int16_t>(keyRect.x + (keyRect.width - glyphW) / 2),
                     static_cast<int16_t>(keyRect.y + (keyRect.height - 11) / 2), glyphW, 11};
    frame.target().stroke(glyph, ink, 2, 5);
  };

  for (uint8_t row = 0; row < huProps.layout->rowCount; ++row) {
    const KeyboardRow& layoutRow = huProps.layout->rows[row];
    if (!layoutRow.keys || layoutRow.count == 0) continue;
    const bool bottomRow = row == huProps.layout->rowCount - 1;
    rowHitOverflow = bottomRow ? huProps.bottomHitOverflow : 0;
    const int16_t y = static_cast<int16_t>(rect.y + row * (rowH + gap));
    int16_t x = rect.x;

    for (uint8_t col = 0; col < layoutRow.count; ++col) {
      const KeyboardKey& key = layoutRow.keys[col];
      int16_t w = 41;

      if (row == 3) {
        // 62 + (8 x 41) + 62 = 452.
        if (key.kind == KeyKind::Shift || key.kind == KeyKind::Delete) w = 62;
      } else if (bottomRow) {
        // No-language row: 62 + 41 + 41 + 164 + 41 + 41 + 62 = 452.
        // Language row:    62 + 41 + 41 + 41 + 123 + 41 + 41 + 62 = 452.
        if (key.kind == KeyKind::Mode || key.kind == KeyKind::Ok) {
          w = 62;
        } else if (key.kind == KeyKind::Space) {
          w = layoutRow.count == 7 ? 164 : 123;
        }
      }

      drawKey(Rect{x, y, w, rowH}, key, logicalIndex++);
      x = static_cast<int16_t>(x + w + gap);

      // 11 equal 41 px keys total 451 px; put the remaining neutral pixel in
      // the middle of the row instead of widening '-', Ö or Á.
      if (row < 3 && layoutRow.count == 11 && col == 5) x = static_cast<int16_t>(x + 1);
    }
  }
}
}  // namespace ui
}  // namespace freeink

#define builtinKeyboardLayout builtinKeyboardLayoutCphun
#define keyboardAltOutputFor keyboardAltOutputForCphun
#define keyboard keyboardCphun
