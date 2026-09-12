#include "ManualDictionarySearchActivity.h"

#include <GfxRenderer.h>
#include <freertos/FreeRTOS.h>
#include <freertos/task.h>

#include <algorithm>
#include <cctype>

#include "CrossPointSettings.h"
#include "DictionaryDefinitionActivity.h"
#include "activities/util/KeyboardEntryActivity.h"
#include "components/UITheme.h"

namespace {
void indexBuildYield(void*) { vTaskDelay(1); }
}

void ManualDictionarySearchActivity::onEnter() {
  Activity::onEnter();
  promptKeyboard();
}

std::string ManualDictionarySearchActivity::trimCopy(const std::string& value) {
  size_t first = 0;
  while (first < value.size() && std::isspace(static_cast<unsigned char>(value[first]))) first++;
  size_t last = value.size();
  while (last > first && std::isspace(static_cast<unsigned char>(value[last - 1]))) last--;
  return value.substr(first, last - first);
}

void ManualDictionarySearchActivity::finishCancelled() {
  ActivityResult result;
  result.isCancelled = true;
  setResult(std::move(result));
  finish();
}

void ManualDictionarySearchActivity::promptKeyboard() {
  popup = Popup::None;
  startActivityForResult(
      std::make_unique<KeyboardEntryActivity>(renderer, mappedInput, "Kézi keresés", query, 96, InputType::Text),
      [this](const ActivityResult& result) {
        if (result.isCancelled) {
          finishCancelled();
          return;
        }
        const auto* keyboard = std::get_if<KeyboardResult>(&result.data);
        if (!keyboard) {
          finishCancelled();
          return;
        }
        query = trimCopy(keyboard->text);
        if (query.empty()) {
          promptKeyboard();
          return;
        }
        performLookup();
      });
}

void ManualDictionarySearchActivity::performLookup() {
  popup = Popup::Busy;
  if (!dictOpenAttempted) {
    dictOpenAttempted = true;
    dictOpenOk = dict.open(SETTINGS.dictionaryName);
    dictNeedsIndex = dictOpenOk && dict.needsIndex();
  }
  popupMsg = dictNeedsIndex ? StrId::STR_DICT_INDEXING : StrId::STR_DICT_LOOKING_UP;
  requestUpdateAndWait();

  bool ok = dictOpenOk;
  Dictionary::IndexResult indexResult = Dictionary::IndexResult::Ok;
  if (ok && dictNeedsIndex) {
    ok = dict.buildIndex(&indexBuildYield, nullptr, &indexResult);
    dictNeedsIndex = !ok;
  }

  std::string definition;
  std::string headword;
  Dictionary::LookupResult lookupResult = Dictionary::LookupResult::NotFound;
  const bool found = ok && dict.lookup(query.c_str(), definition, headword, &lookupResult);

  if (found) {
    popup = Popup::None;
    startActivityForResult(
        std::make_unique<DictionaryDefinitionActivity>(renderer, mappedInput, std::move(headword), std::move(definition),
                                                       dict.definitionsAreHtml(), true),
        [this](const ActivityResult& result) {
          if (result.isCancelled) {
            finishCancelled();
          } else {
            promptKeyboard();
          }
        });
    return;
  }

  popup = Popup::Error;
  if (!ok) {
    switch (indexResult) {
      case Dictionary::IndexResult::LowMemory:
        popupMsg = StrId::STR_DICT_LOW_MEMORY;
        break;
      case Dictionary::IndexResult::ReadError:
        popupMsg = StrId::STR_DICT_READ_FAILED;
        break;
      case Dictionary::IndexResult::Ok:
      default:
        popupMsg = StrId::STR_DICT_ERROR;
        break;
    }
  } else {
    switch (lookupResult) {
      case Dictionary::LookupResult::Decompress:
        popupMsg = StrId::STR_DICT_DECOMPRESS_ERROR;
        break;
      case Dictionary::LookupResult::LowMemory:
        popupMsg = StrId::STR_DICT_LOW_MEMORY;
        break;
      case Dictionary::LookupResult::ReadError:
        popupMsg = StrId::STR_DICT_READ_FAILED;
        break;
      case Dictionary::LookupResult::NotFound:
      default:
        popup = Popup::NotFound;
        popupMsg = StrId::STR_DICT_NOT_FOUND;
        break;
    }
  }
  popupTime = millis();
  requestUpdate();
}

void ManualDictionarySearchActivity::loop() {
  if (mappedInput.wasReleased(MappedInputManager::Button::Back)) {
    finishCancelled();
    return;
  }
  if ((popup == Popup::NotFound || popup == Popup::Error) && millis() - popupTime >= POPUP_DURATION_MS) {
    promptKeyboard();
  }
}

void ManualDictionarySearchActivity::render(RenderLock&&) {
  renderer.clearScreen();
  if (popup != Popup::None) {
    GUI.drawPopup(renderer, I18N.get(popupMsg));
    return;
  }
  renderer.displayBuffer();
}
