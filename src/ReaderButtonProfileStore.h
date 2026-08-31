#pragma once

#include <ArduinoJson.h>
#include <PersistableStore.h>

#include "ReaderButtonProfile.h"

class ReaderButtonProfileStore : public PersistableStore<ReaderButtonProfileStore> {
 private:
  ReaderButtonProfileStore() : profile_(FACTORY_READER_BUTTON_PROFILE) {}

  friend class PersistableStore<ReaderButtonProfileStore>;

 public:
  static const char* getFilePath() { return "/.crosspoint/reader-buttons.json"; }

  void toJson(JsonDocument& doc) const;
  bool fromJson(JsonVariantConst doc);

  ReaderAction get(ReaderPhysicalButton button, ReaderButtonGesture gesture) const;
  void set(ReaderPhysicalButton button, ReaderButtonGesture gesture, ReaderAction action);
  void resetToFactory();

  const ReaderButtonProfile& profile() const { return profile_; }

 private:
  ReaderButtonProfile profile_;
};

#define READER_BUTTONS ReaderButtonProfileStore::getInstance()
