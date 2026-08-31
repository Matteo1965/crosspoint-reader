#include "ReaderButtonGestureDetector.h"

void ReaderButtonGestureDetector::onPressed(const ReaderPhysicalButton button, const uint32_t nowMs) {
  auto& state = states_[buttonIndex(button)];
  state.down = true;
  state.holdEmitted = false;
  state.pressedAt = nowMs;
}

std::optional<ReaderButtonGestureEvent> ReaderButtonGestureDetector::onHeld(const ReaderPhysicalButton button,
                                                                            const uint32_t nowMs) {
  auto& state = states_[buttonIndex(button)];
  if (!state.down || state.holdEmitted || nowMs - state.pressedAt < holdMs_) return std::nullopt;

  state.holdEmitted = true;
  state.singlePending = false;
  return ReaderButtonGestureEvent{button, ReaderButtonGesture::Hold};
}

std::optional<ReaderButtonGestureEvent> ReaderButtonGestureDetector::onReleased(const ReaderPhysicalButton button,
                                                                                const uint32_t nowMs) {
  auto& state = states_[buttonIndex(button)];
  if (!state.down) return std::nullopt;
  state.down = false;

  if (state.holdEmitted) {
    state.holdEmitted = false;
    state.singlePending = false;
    return std::nullopt;
  }

  if (state.singlePending && nowMs - state.firstReleasedAt <= doubleClickMs_) {
    state.singlePending = false;
    return ReaderButtonGestureEvent{button, ReaderButtonGesture::Double};
  }

  state.singlePending = true;
  state.firstReleasedAt = nowMs;
  return std::nullopt;
}

std::optional<ReaderButtonGestureEvent> ReaderButtonGestureDetector::poll(const uint32_t nowMs) {
  for (size_t i = 0; i < states_.size(); ++i) {
    auto& state = states_[i];
    if (!state.singlePending || nowMs - state.firstReleasedAt <= doubleClickMs_) continue;

    state.singlePending = false;
    return ReaderButtonGestureEvent{static_cast<ReaderPhysicalButton>(i), ReaderButtonGesture::Single};
  }
  return std::nullopt;
}

void ReaderButtonGestureDetector::reset() {
  for (auto& state : states_) state = ButtonState{};
}
