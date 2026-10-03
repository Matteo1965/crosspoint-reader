#pragma once

#include <cstdint>
#include <string>
#include <vector>

struct TextEditAnchor {
  int spineIndex = 0;
  uint32_t visibleTextOffset = 0;
  uint16_t length = 0;
  std::string originalText;
  std::string replacementText;
  bool trimAdjacentSpace = false;
};

class TextEditStore {
 public:
  explicit TextEditStore(std::string bookPath);
  bool load();
  bool save() const;
  const TextEditAnchor* find(int spineIndex, uint32_t visibleTextOffset) const;
  bool upsert(const TextEditAnchor& edit);
  const std::vector<TextEditAnchor>& items() const { return edits_; }

 private:
  std::string filePath_;
  std::vector<TextEditAnchor> edits_;
};
