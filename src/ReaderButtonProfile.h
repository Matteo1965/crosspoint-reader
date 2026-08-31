#pragma once

#include <array>
#include <cstddef>
#include <cstdint>

#include "ReaderAction.h"

// Physical front-button identities. These deliberately describe the hardware
// positions/lines, not the logical Back/Confirm/Left/Right remap, so configured
// gestures remain attached to the same physical X4 buttons across orientation
// and logical-role changes.
enum class ReaderPhysicalButton : uint8_t {
  Back = 0,
  Confirm = 1,
  Left = 2,
  Right = 3,
  Count
};

enum class ReaderButtonGesture : uint8_t {
  Single = 0,
  Double = 1,
  Hold = 2,
  Count
};

constexpr size_t READER_PHYSICAL_BUTTON_COUNT = static_cast<size_t>(ReaderPhysicalButton::Count);
constexpr size_t READER_BUTTON_GESTURE_COUNT = static_cast<size_t>(ReaderButtonGesture::Count);
constexpr size_t READER_BUTTON_ACTION_SLOT_COUNT = READER_PHYSICAL_BUTTON_COUNT * READER_BUTTON_GESTURE_COUNT;

struct ReaderButtonProfile {
  std::array<uint8_t, READER_BUTTON_ACTION_SLOT_COUNT> actions{};

  constexpr ReaderAction get(const ReaderPhysicalButton button, const ReaderButtonGesture gesture) const {
    return static_cast<ReaderAction>(actions[index(button, gesture)]);
  }

  constexpr void set(const ReaderPhysicalButton button, const ReaderButtonGesture gesture, const ReaderAction action) {
    actions[index(button, gesture)] = static_cast<uint8_t>(action);
  }

  static constexpr size_t index(const ReaderPhysicalButton button, const ReaderButtonGesture gesture) {
    return static_cast<size_t>(button) * READER_BUTTON_GESTURE_COUNT + static_cast<size_t>(gesture);
  }
};

// Clean CPHUN-36 factory profile. CPHUN-35 defaults have no enabled double-click
// or hold reader shortcuts, so those slots intentionally start at None.
// The four single-click actions reproduce the default X4 reader controls.
constexpr ReaderButtonProfile makeFactoryReaderButtonProfile() {
  ReaderButtonProfile profile{};
  profile.set(ReaderPhysicalButton::Back, ReaderButtonGesture::Single, ReaderAction::ReaderBack);
  profile.set(ReaderPhysicalButton::Confirm, ReaderButtonGesture::Single, ReaderAction::OpenReaderMenu);
  profile.set(ReaderPhysicalButton::Left, ReaderButtonGesture::Single, ReaderAction::PreviousPage);
  profile.set(ReaderPhysicalButton::Right, ReaderButtonGesture::Single, ReaderAction::NextPage);
  return profile;
}

constexpr ReaderButtonProfile FACTORY_READER_BUTTON_PROFILE = makeFactoryReaderButtonProfile();

static_assert(READER_BUTTON_ACTION_SLOT_COUNT == 12, "X4 front-button profile must expose 4 x 3 action slots");
static_assert(FACTORY_READER_BUTTON_PROFILE.get(ReaderPhysicalButton::Back, ReaderButtonGesture::Double) ==
                  ReaderAction::None,
              "Factory double-click actions must start disabled");
static_assert(FACTORY_READER_BUTTON_PROFILE.get(ReaderPhysicalButton::Confirm, ReaderButtonGesture::Hold) ==
                  ReaderAction::None,
              "Factory hold actions must start disabled");
