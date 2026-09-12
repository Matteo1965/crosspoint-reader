from pathlib import Path


def replace_once(path, old, new):
    p = Path(path)
    text = p.read_text(encoding="utf-8")
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{path}: expected exactly one match, found {count}: {old!r}")
    p.write_text(text.replace(old, new, 1), encoding="utf-8")


# 1) Reader menu: add a distinct action and place it directly under the existing dictionary lookup.
replace_once(
    "src/activities/reader/EpubReaderMenuActivity.h",
    "    DICTIONARY,\n    BOOK_DESCRIPTION,",
    "    DICTIONARY,\n    MANUAL_DICTIONARY_SEARCH,\n    BOOK_DESCRIPTION,",
)
replace_once(
    "src/activities/reader/EpubReaderMenuActivity.cpp",
    '  items.push_back({MenuAction::DICTIONARY, StrId::STR_LOOKUP, "Szótári keresés"});\n',
    '  items.push_back({MenuAction::DICTIONARY, StrId::STR_LOOKUP, "Szótári keresés"});\n'
    '  items.push_back({MenuAction::MANUAL_DICTIONARY_SEARCH, StrId::STR_LOOKUP, "Kézi keresés"});\n',
)

# 2) Definition viewer: in manual-search mode, Confirm returns to the keyboard while Back exits the manual search.
replace_once(
    "src/activities/reader/DictionaryDefinitionActivity.h",
    "                                        std::string definition, bool htmlDefinition = false)\n"
    "      : Activity(\"DictionaryDefinition\", renderer, mappedInput),\n"
    "        headword(std::move(headword)),\n"
    "        definition(std::move(definition)),\n"
    "        htmlDefinition(htmlDefinition) {}",
    "                                        std::string definition, bool htmlDefinition = false,\n"
    "                                        bool manualSearchMode = false)\n"
    "      : Activity(\"DictionaryDefinition\", renderer, mappedInput),\n"
    "        headword(std::move(headword)),\n"
    "        definition(std::move(definition)),\n"
    "        htmlDefinition(htmlDefinition),\n"
    "        manualSearchMode(manualSearchMode) {}",
)
replace_once(
    "src/activities/reader/DictionaryDefinitionActivity.h",
    "  const bool htmlDefinition;\n",
    "  const bool htmlDefinition;\n  const bool manualSearchMode;\n",
)
replace_once(
    "src/activities/reader/DictionaryDefinitionActivity.cpp",
    "void DictionaryDefinitionActivity::loop() {\n"
    "  if (mappedInput.wasReleased(MappedInputManager::Button::Back)) {\n"
    "    finish();\n"
    "    return;\n"
    "  }\n",
    "void DictionaryDefinitionActivity::loop() {\n"
    "  if (mappedInput.wasReleased(MappedInputManager::Button::Back)) {\n"
    "    if (manualSearchMode) {\n"
    "      ActivityResult result;\n"
    "      result.isCancelled = true;\n"
    "      setResult(std::move(result));\n"
    "    }\n"
    "    finish();\n"
    "    return;\n"
    "  }\n"
    "  if (manualSearchMode && mappedInput.wasReleased(MappedInputManager::Button::Confirm)) {\n"
    "    finish();\n"
    "    return;\n"
    "  }\n",
)
replace_once(
    "src/activities/reader/DictionaryDefinitionActivity.cpp",
    "  const auto labels =\n"
    "      mappedInput.mapLabels(tr(STR_BACK), \"\", (currentPage > 0 ? \"<\" : \"\"), (currentPage + 1 < totalPages ? \">\" : \"\"));\n",
    "  const auto labels = mappedInput.mapLabels(\n"
    "      tr(STR_BACK), manualSearchMode ? \"Billentyűzet\" : \"\", (currentPage > 0 ? \"<\" : \"\"),\n"
    "      (currentPage + 1 < totalPages ? \">\" : \"\"));\n",
)

# 3) New manual search activity. It owns the keyboard -> lookup -> definition loop.
manual_h = r'''#pragma once

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
'''

manual_cpp = r'''#include "ManualDictionarySearchActivity.h"

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
'''

Path("src/activities/reader/ManualDictionarySearchActivity.h").write_text(manual_h, encoding="utf-8")
Path("src/activities/reader/ManualDictionarySearchActivity.cpp").write_text(manual_cpp, encoding="utf-8")

# 4) Reader wiring: preserve the existing selected-word search and add the manual path separately.
replace_once(
    "src/activities/reader/EpubReaderActivity.cpp",
    '#include "DictionaryWordSelectActivity.h"\n',
    '#include "DictionaryWordSelectActivity.h"\n#include "ManualDictionarySearchActivity.h"\n',
)
replace_once(
    "src/activities/reader/EpubReaderActivity.cpp",
    "    case EpubReaderMenuActivity::MenuAction::DICTIONARY: {\n"
    "      openDictionaryWordSelect();\n"
    "      break;\n"
    "    }\n",
    "    case EpubReaderMenuActivity::MenuAction::DICTIONARY: {\n"
    "      openDictionaryWordSelect();\n"
    "      break;\n"
    "    }\n"
    "    case EpubReaderMenuActivity::MenuAction::MANUAL_DICTIONARY_SEARCH: {\n"
    "      if (SETTINGS.dictionaryName[0] == '\\0') {\n"
    "        showDictionaryMessage = true;\n"
    "        dictionaryMessageTime = millis();\n"
    "        requestUpdate();\n"
    "        break;\n"
    "      }\n"
    "      startActivityForResult(std::make_unique<ManualDictionarySearchActivity>(renderer, mappedInput),\n"
    "                             [this](const ActivityResult&) { openReaderMenu(); });\n"
    "      break;\n"
    "    }\n",
)

# 5) Build id only; no pending BookInfo/Fülszöveg changes are bundled into #107.
replace_once(
    "src/CPHUNBuildId.h",
    '#define CPHUN_BUILD_ID "CPHUN-260912-106"',
    '#define CPHUN_BUILD_ID "CPHUN-260912-107"',
)
