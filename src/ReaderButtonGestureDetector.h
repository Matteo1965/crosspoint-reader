#pragma once

#include <array>
#include <cstdint>
#include <optional>

#include "ReaderButtonProfile.h"

struct ReaderButtonGestureEvent {
  ReaderPhysicalButton button;
  ReaderButtonGesture gesture;
};

// Pure state machine for physical reader-button gestures. Hardware polling stays
// outside this class so the timing rules can be unit-tested without Arduino/HAL.
class ReaderButtonGestureDetector {
 public:
  static constexpr uint32_t DEFAULT_DOUBLE_CLICK_MS = 400;
  static constexpr uint32_t DEFAULT_HOLD_MS = 600;

  explicit ReaderButtonGestureDetector(uint32_t doubleClickMs = DEFAULT_DOUBLE_CLICK_MS,
                                       uint32_t holdMs = DEFAULT_HOLD_MS)
      : doubleClickMs_(doubleClickMs), holdMs_(holdMs) {}

  // Call on the raw physical press edge.
  void onPressed(ReaderPhysicalButton button, uint32_t nowMs);

  // Call while the raw physical button remains held. Emits Hold exactly once.
  std::optional<ReaderButtonGestureEvent> onHeld(ReaderPhysicalButton button, uint32_t nowMs);

  // Call on the raw physical release edge. A first short release is delayed so
  // it can still become a double-click. A completed hold suppresses release.
  std::optional<ReaderButtonGestureEvent> onReleased(ReaderPhysicalButton button, uint32_t nowMs);

  // Call once per reader loop. Emits an armed Single when its double-click
  // window expires. At most one event is returned per call.
  std::optional<ReaderButtonGestureEvent> poll(uint32_t nowMs);

  void reset();

 private:
  struct ButtonState {
    bool down = false;
    bool holdEmitted = false;
    bool singlePending = false;
    uint32_t pressedAt = 0;
    uint32_t firstReleasedAt = 0;
  };

  static constexpr size_t buttonIndex(ReaderPhysicalButton button) { return static_cast<size_t>(button); }

  std::array<ButtonState, READER_PHYSICAL_BUTTON_COUNT> states_{};
  uint32_t doubleClickMs_;
  uint32_t holdMs_;
};
