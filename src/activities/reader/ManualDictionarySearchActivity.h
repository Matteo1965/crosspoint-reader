#pragma once

#include <I18n.h>

#include <string>

#include "activities/Activity.h"
#include "util/Dictionary.h"

class ManualDictionarySearchActivity final : public Activity {
 public:
  explicit ManualDictionarySearchActivity(GfxRenderer& renderer, MappedInputManager& mappedInput)
      : Activity("ManualDictionarySearch", renderer, mappedInput) {}

  void onEnter() override;
  void loop() override;
  void render(RenderLock&&) override;

 private:
  enum class Popup : uint8_t { None, Busy, NotFound, Error };

  void promptKeyboard();
  void performLookup();
  void finishCancelled();
  static std::string trimCopy(const std::string& value);

  Dictionary dict;
  bool dictOpenAttempted = false;
  bool dictOpenOk = false;
  bool dictNeedsIndex = false;
  std::string query;
  Popup popup = Popup::None;
  StrId popupMsg = StrId::STR_DICT_LOOKING_UP;
  unsigned long popupTime = 0;

  static constexpr unsigned long POPUP_DURATION_MS = 1500;
};
