#pragma once

#include <cstdint>
#include <memory>

struct LibraryViewState {
  int activeSortTab = 0;
  uint8_t descendingTabs = 2u;  // Recent asc, New desc, Title/Author asc.
};

using LibraryViewStatePtr = std::shared_ptr<LibraryViewState>;
