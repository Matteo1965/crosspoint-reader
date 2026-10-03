#include "TextEditStore.h"

#include <ArduinoJson.h>
#include <HalStorage.h>
#include <PersistableStore.h>

#include <algorithm>

namespace {
constexpr char EDIT_DIR[] = "/.crosspoint/edits/";

std::string pathForBook(std::string bookPath) {
  if (!bookPath.empty() && bookPath.front() == '/') bookPath.erase(0, 1);
  std::replace(bookPath.begin(), bookPath.end(), '/', '_');
  std::replace(bookPath.begin(), bookPath.end(), '\\', '_');
  const size_t lastDot = bookPath.find_last_of('.');
  if (lastDot != std::string::npos) bookPath.erase(lastDot);
  return std::string(EDIT_DIR) + bookPath + ".json";
}
}  // namespace

TextEditStore::TextEditStore(std::string bookPath) : filePath_(pathForBook(std::move(bookPath))) {}

bool TextEditStore::load() {
  edits_.clear();
  if (!Storage.exists(filePath_.c_str())) return true;
  JsonDocument doc;
  if (!PersistableStoreBase::readDocFromFile(filePath_.c_str(), doc)) return false;
  for (JsonObject item : doc["edits"].as<JsonArray>()) {
    TextEditAnchor edit;
    edit.spineIndex = item["spine"] | 0;
    edit.visibleTextOffset = item["offset"] | static_cast<uint32_t>(0);
    edit.length = item["length"] | static_cast<uint16_t>(0);
    edit.originalText = item["original"] | "";
    edit.replacementText = item["replacement"] | "";
    edit.trimAdjacentSpace = item["trimAdjacentSpace"] | false;
    edits_.push_back(std::move(edit));
  }
  return true;
}

bool TextEditStore::save() const {
  JsonDocument doc;
  JsonArray arr = doc["edits"].to<JsonArray>();
  for (const auto& edit : edits_) {
    JsonObject item = arr.add<JsonObject>();
    item["spine"] = edit.spineIndex;
    item["offset"] = edit.visibleTextOffset;
    item["length"] = edit.length;
    item["original"] = edit.originalText;
    item["replacement"] = edit.replacementText;
    item["trimAdjacentSpace"] = edit.trimAdjacentSpace;
  }
  Storage.mkdir(EDIT_DIR);
  return PersistableStoreBase::writeDocToFile(filePath_.c_str(), doc);
}

const TextEditAnchor* TextEditStore::find(const int spineIndex, const uint32_t visibleTextOffset) const {
  const auto it = std::find_if(edits_.begin(), edits_.end(), [&](const TextEditAnchor& edit) {
    return edit.spineIndex == spineIndex && edit.visibleTextOffset == visibleTextOffset;
  });
  return it == edits_.end() ? nullptr : &*it;
}

bool TextEditStore::upsert(const TextEditAnchor& edit) {
  auto it = std::find_if(edits_.begin(), edits_.end(), [&](const TextEditAnchor& item) {
    return item.spineIndex == edit.spineIndex && item.visibleTextOffset == edit.visibleTextOffset;
  });
  if (it == edits_.end()) {
    edits_.push_back(edit);
    if (save()) return true;
    edits_.pop_back();
    return false;
  }
  const TextEditAnchor old = *it;
  *it = edit;
  if (save()) return true;
  *it = old;
  return false;
}
