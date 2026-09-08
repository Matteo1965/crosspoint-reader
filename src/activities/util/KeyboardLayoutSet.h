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

// CPHUN-69: FreeInkUI renders KeyboardKey::alt as a corner hint. Hungarian
// keeps those fields empty and resolves the same long-press outputs here, so
// the key faces stay uncluttered without losing Ő/Ű/Í/Ó/Ú or number-row alts.
inline const char* keyboardAltOutputForCphun(const KeyboardLayout& layout, const int16_t value) {
  if (const char* huAlt = keyboard_layouts::hu_keyboard::altOutputFor(layout, value)) return huAlt;
  return keyboardAltOutputFor(layout, value);
}

// CPHUN-73/74: on the Hungarian letter layers, keep FreeInkUI's exact keyboard
// behavior but move each row's integer-division remainder away from the final
// key. Row 1 gives it to W; row 2 gives it to A. Ö and Á therefore keep the
// normal key width, while the requested optical spacing is preserved.
template <size_t MaxInteractions>
void keyboardCphun(Frame<MaxInteractions>& frame, Rect rect, const KeyboardProps& props) {
  if (!props.layout || !keyboard_layouts::hu_keyboard::isHungarianLetterLayout(*props.layout)) {
    keyboard(frame, rect, props);
    return;
  }

  KeyboardProps huProps = props;
  huProps.shiftLabel = "Sh";
  huProps.modeLabel = "Fn";

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
    bp.label = (key.kind == KeyKind::Space || key.kind == KeyKind::Delete || key.kind == KeyKind::Lang)
                   ? nullptr
                   : key.label;
    if (key.kind == KeyKind::Ok && huProps.okLabel) bp.label = huProps.okLabel;
    if (key.kind == KeyKind::Shift && huProps.shiftLabel) bp.label = huProps.shiftLabel;
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

    if (key.kind == KeyKind::Delete || key.kind == KeyKind::Lang) {
      const Paint ink = styles.resolve(frame.stateFor(action, key.value, state)).foreground;
      const int16_t lh = frame.target().lineHeight(keyText.font);
      const int16_t desired = static_cast<int16_t>(lh + lh / 8);
      int16_t iconSize = static_cast<int16_t>(((desired + 8) / 16) * 16);
      if (iconSize < 16) iconSize = 16;
      const int16_t maxSize = keyRect.height < keyRect.width ? keyRect.height : keyRect.width;
      while (iconSize > maxSize && iconSize > 16) iconSize = static_cast<int16_t>(iconSize - 16);
      if (iconSize > maxSize) iconSize = maxSize;
      const BitmapRef icon = key.kind == KeyKind::Delete ? lucideDeleteIcon16() : lucideGlobeIcon32();
      frame.target().bitmap(centeredRect(keyRect, Size{iconSize, iconSize}), icon, BitmapMode::Contain, ink);
      return;
    }

    if (key.kind == KeyKind::Normal && key.alt) {
      TextStyle altStyle = huProps.altText;
      altStyle.align = TextAlign::Right;
      altStyle.maxLines = 1;
      altStyle.color = styles.resolve(frame.stateFor(action, key.value, state)).foreground.color;
      const int16_t altLh = frame.target().lineHeight(altStyle.font);
      frame.target().text(Rect{static_cast<int16_t>(keyRect.x + 2), static_cast<int16_t>(keyRect.y + 2),
                               static_cast<int16_t>(keyRect.width - 3), altLh},
                          key.alt, altStyle);
      return;
    }

    if (key.kind != KeyKind::Space) return;
    const Paint ink = styles.resolve(frame.stateFor(action, key.value, state)).foreground;
    const int16_t cx = static_cast<int16_t>(keyRect.x + keyRect.width / 2);
    const int16_t cy = static_cast<int16_t>(keyRect.y + keyRect.height / 2);
    const int16_t half = static_cast<int16_t>(keyRect.width * 9 / 20);
    frame.target().line(Point{static_cast<int16_t>(cx - half), static_cast<int16_t>(cy + 3)},
                        Point{static_cast<int16_t>(cx + half), static_cast<int16_t>(cy + 3)}, 3, ink);
  };

  for (uint8_t row = 0; row < huProps.layout->rowCount; ++row) {
    const KeyboardRow& layoutRow = huProps.layout->rows[row];
    if (!layoutRow.keys || layoutRow.count == 0) continue;
    rowHitOverflow = row == huProps.layout->rowCount - 1 ? huProps.bottomHitOverflow : 0;
    uint16_t units = static_cast<uint16_t>(layoutRow.insetUnits * 2);
    uint16_t keyUnitsTotal = 0;
    for (uint8_t col = 0; col < layoutRow.count; ++col) {
      const uint8_t keyUnits = layoutRow.keys[col].widthUnits ? layoutRow.keys[col].widthUnits : 1;
      keyUnitsTotal = static_cast<uint16_t>(keyUnitsTotal + keyUnits);
      units = static_cast<uint16_t>(units + keyUnits);
    }
    const int16_t unitW = static_cast<int16_t>((rect.width - gap * (layoutRow.count - 1)) / units);
    const int16_t y = static_cast<int16_t>(rect.y + row * (rowH + gap));
    int16_t x = static_cast<int16_t>(rect.x + layoutRow.insetUnits * unitW);
    const int16_t rowRight = static_cast<int16_t>(rect.right() - layoutRow.insetUnits * unitW);
    const int16_t remainder = static_cast<int16_t>(rowRight - x - gap * (layoutRow.count - 1) -
                                                   unitW * keyUnitsTotal);
    const int8_t remainderTargetCol = row == 1 ? 1 : (row == 2 ? 0 : -1);

    for (uint8_t col = 0; col < layoutRow.count; ++col) {
      const KeyboardKey& key = layoutRow.keys[col];
      const uint8_t keyUnits = key.widthUnits ? key.widthUnits : 1;
      int16_t w = static_cast<int16_t>(unitW * keyUnits);
      if (remainderTargetCol >= 0) {
        if (col == static_cast<uint8_t>(remainderTargetCol)) w = static_cast<int16_t>(w + remainder);
      } else if (col == layoutRow.count - 1) {
        w = static_cast<int16_t>(rowRight - x);
      }
      drawKey(Rect{x, y, w, rowH}, key, logicalIndex++);
      x = static_cast<int16_t>(x + w + gap);
    }
  }
}
}  // namespace ui
}  // namespace freeink

#define builtinKeyboardLayout builtinKeyboardLayoutCphun
#define keyboardAltOutputFor keyboardAltOutputForCphun
#define keyboard keyboardCphun
