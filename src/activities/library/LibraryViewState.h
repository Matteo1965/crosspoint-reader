#pragma once

#include <cstdint>
#include <memory>

struct LibraryViewState {
  int activeSortTab = 0;
  uint8_t descendingTabs = 3u;  // Recent/New newest first; Title/Author ascending.
};

using LibraryViewStatePtr = std::shared_ptr<LibraryViewState>;
