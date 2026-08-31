#include "ReaderButtonProfileStore.h"

namespace {
constexpr char PROFILE_KEY[] = "actions";
}

void ReaderButtonProfileStore::toJson(JsonDocument& doc) const {
  JsonArray actions = doc[PROFILE_KEY].to<JsonArray>();
  for (const uint8_t action : profile_.actions) actions.add(action);
}

bool ReaderButtonProfileStore::fromJson(JsonVariantConst doc) {
  profile_ = FACTORY_READER_BUTTON_PROFILE;

  const JsonArrayConst actions = doc[PROFILE_KEY];
  if (actions.isNull()) return true;

  const size_t count = actions.size() < READER_BUTTON_ACTION_SLOT_COUNT ? actions.size() : READER_BUTTON_ACTION_SLOT_COUNT;
  for (size_t i = 0; i < count; ++i) {
    const uint8_t value = actions[i] | static_cast<uint8_t>(ReaderAction::None);
    profile_.actions[i] = isValidReaderAction(value) ? value : static_cast<uint8_t>(ReaderAction::None);
  }
  return true;
}

ReaderAction ReaderButtonProfileStore::get(const ReaderPhysicalButton button, const ReaderButtonGesture gesture) const {
  const uint8_t value = profile_.actions[ReaderButtonProfile::index(button, gesture)];
  return isValidReaderAction(value) ? static_cast<ReaderAction>(value) : ReaderAction::None;
}

void ReaderButtonProfileStore::set(const ReaderPhysicalButton button, const ReaderButtonGesture gesture,
                                   const ReaderAction action) {
  profile_.set(button, gesture, isValidReaderAction(static_cast<uint8_t>(action)) ? action : ReaderAction::None);
}

void ReaderButtonProfileStore::resetToFactory() { profile_ = FACTORY_READER_BUTTON_PROFILE; }
