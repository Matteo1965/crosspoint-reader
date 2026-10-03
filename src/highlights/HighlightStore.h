#pragma once

#include <cstdint>
#include <string>
#include <vector>

struct HighlightAnchor {
  int spineIndex = 0;
  uint32_t visibleTextOffset = 0;
  uint16_t length = 0;
  std::string text;
};

class HighlightStore {
 public:
  explicit HighlightStore(std::string bookPath);
  bool load();
  bool save() const;
  bool contains(const HighlightAnchor& anchor) const;
  bool add(const HighlightAnchor& anchor);
  bool remove(const HighlightAnchor& anchor);
  bool toggle(const HighlightAnchor& anchor);
  const std::vector<HighlightAnchor>& items() const { return highlights_; }

 private:
  std::string filePath_;
  std::vector<HighlightAnchor> highlights_;
};
