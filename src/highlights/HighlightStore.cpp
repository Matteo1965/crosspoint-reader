#include "HighlightStore.h"

#include <ArduinoJson.h>
#include <HalStorage.h>
#include <PersistableStore.h>

#include <algorithm>

namespace {
constexpr char HIGHLIGHT_DIR[] = "/.crosspoint/highlights/";

std::string pathForBook(std::string bookPath) {
  if (!bookPath.empty() && bookPath.front() == '/') bookPath.erase(0, 1);
  std::replace(bookPath.begin(), bookPath.end(), '/', '_');
  std::replace(bookPath.begin(), bookPath.end(), '\\', '_');
  const size_t lastDot = bookPath.find_last_of('.');
  if (lastDot != std::string::npos) bookPath.erase(lastDot);
  return std::string(HIGHLIGHT_DIR) + bookPath + ".json";
}

bool sameAnchor(const HighlightAnchor& a, const HighlightAnchor& b) {
  return a.spineIndex == b.spineIndex && a.visibleTextOffset == b.visibleTextOffset;
}
}  // namespace

HighlightStore::HighlightStore(std::string bookPath) : filePath_(pathForBook(std::move(bookPath))) {}

bool HighlightStore::load() {
  highlights_.clear();
  if (!Storage.exists(filePath_.c_str())) return true;
  JsonDocument doc;
  if (!PersistableStoreBase::readDocFromFile(filePath_.c_str(), doc)) return false;
  for (JsonObject item : doc["highlights"].as<JsonArray>()) {
    HighlightAnchor anchor;
    anchor.spineIndex = item["spine"] | 0;
    anchor.visibleTextOffset = item["offset"] | static_cast<uint32_t>(0);
    anchor.length = item["length"] | static_cast<uint16_t>(0);
    anchor.text = item["text"] | "";
    highlights_.push_back(std::move(anchor));
  }
  return true;
}

bool HighlightStore::save() const {
  JsonDocument doc;
  JsonArray arr = doc["highlights"].to<JsonArray>();
  for (const auto& anchor : highlights_) {
    JsonObject item = arr.add<JsonObject>();
    item["spine"] = anchor.spineIndex;
    item["offset"] = anchor.visibleTextOffset;
    item["length"] = anchor.length;
    item["text"] = anchor.text;
  }
  Storage.mkdir(HIGHLIGHT_DIR);
  return PersistableStoreBase::writeDocToFile(filePath_.c_str(), doc);
}

bool HighlightStore::contains(const HighlightAnchor& anchor) const {
  return std::any_of(highlights_.begin(), highlights_.end(),
                     [&](const HighlightAnchor& item) { return sameAnchor(item, anchor); });
}

bool HighlightStore::add(const HighlightAnchor& anchor) {
  if (contains(anchor)) return true;
  highlights_.push_back(anchor);
  if (save()) return true;
  highlights_.pop_back();
  return false;
}

bool HighlightStore::remove(const HighlightAnchor& anchor) {
  const auto it = std::find_if(highlights_.begin(), highlights_.end(),
                               [&](const HighlightAnchor& item) { return sameAnchor(item, anchor); });
  if (it == highlights_.end()) return true;
  const HighlightAnchor removed = *it;
  const size_t index = static_cast<size_t>(it - highlights_.begin());
  highlights_.erase(it);
  if (save()) return true;
  highlights_.insert(highlights_.begin() + index, removed);
  return false;
}

bool HighlightStore::toggle(const HighlightAnchor& anchor) {
  return contains(anchor) ? remove(anchor) : add(anchor);
}
