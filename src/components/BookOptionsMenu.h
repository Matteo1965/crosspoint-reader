#pragma once

#include <I18n.h>

#include <array>
#include <cstdint>
#include <functional>
#include <utility>

#include "components/OptionPopup.h"

enum class BookOptionsAction : uint8_t {
  Description = 0,
  Metadata,
  ShowCover,
  Open,
  RemoveFromRecent,
  Delete,
  RebuildLibrary,
  SwitchView,
  Search,
  ClearSearch,
};

inline void showBookOptionsMenu(OptionPopup& popup, const char* title, const bool includeRemoveFromRecent,
                                const char* switchViewLabel, const bool searchActive,
                                std::function<void(BookOptionsAction)> onSelect) {
  const bool hu = I18N.getLanguage() == Language::HU;
  const char* options[10] = {};
  std::array<BookOptionsAction, 10> actions{};
  int count = 0;

  if (switchViewLabel && *switchViewLabel) {
    options[count] = switchViewLabel;
    actions[count++] = BookOptionsAction::SwitchView;
  }

  options[count] = hu ? "Megnyitás" : "Open";
  actions[count++] = BookOptionsAction::Open;

  options[count] = searchActive ? (hu ? "Keresés módosítása" : "Modify search")
                                : (hu ? "Keresés" : "Search");
  actions[count++] = BookOptionsAction::Search;
  if (searchActive) {
    options[count] = hu ? "Keresés törlése" : "Clear search";
    actions[count++] = BookOptionsAction::ClearSearch;
  }

  options[count] = hu ? "Fülszöveg" : "Description";
  actions[count++] = BookOptionsAction::Description;
  options[count] = hu ? "Metaadatok" : "Metadata";
  actions[count++] = BookOptionsAction::Metadata;
  options[count] = hu ? "Borító megjelenítése" : "Show cover";
  actions[count++] = BookOptionsAction::ShowCover;
  options[count] = hu ? "Könyvtár frissítése" : "Refresh library";
  actions[count++] = BookOptionsAction::RebuildLibrary;

  if (includeRemoveFromRecent) {
    options[count] = tr(STR_REMOVE_FROM_RECENTS);
    actions[count++] = BookOptionsAction::RemoveFromRecent;
  }

  options[count] = tr(STR_DELETE);
  actions[count++] = BookOptionsAction::Delete;

  popup.showMultilineTitle(title, options, count, 0,
                           [actions, count, onSelect = std::move(onSelect)](const int choice) mutable {
                             if (choice < 0 || choice >= count) return;
                             if (onSelect) onSelect(actions[choice]);
                           });
}
