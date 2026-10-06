#pragma once

#include <I18n.h>

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
};

inline void showBookOptionsMenu(OptionPopup& popup, const char* title, const bool includeRemoveFromRecent,
                                std::function<void(BookOptionsAction)> onSelect) {
  const bool hu = I18N.getLanguage() == Language::HU;
  const char* options[7] = {};
  BookOptionsAction actions[7] = {};
  int count = 0;

  options[count] = hu ? "Fülszöveg" : "Description";
  actions[count++] = BookOptionsAction::Description;
  options[count] = hu ? "Metaadatok" : "Metadata";
  actions[count++] = BookOptionsAction::Metadata;
  options[count] = hu ? "Borító megjelenítése" : "Show cover";
  actions[count++] = BookOptionsAction::ShowCover;
  options[count] = hu ? "Megnyitás" : "Open";
  actions[count++] = BookOptionsAction::Open;

  if (includeRemoveFromRecent) {
    options[count] = tr(STR_REMOVE_FROM_RECENTS);
    actions[count++] = BookOptionsAction::RemoveFromRecent;
  }

  options[count] = tr(STR_DELETE);
  actions[count++] = BookOptionsAction::Delete;
  options[count] = tr(STR_LIBRARY_REBUILD);
  actions[count++] = BookOptionsAction::RebuildLibrary;

  popup.showMultilineTitle(title, options, count, 0,
                           [actions, count, onSelect = std::move(onSelect)](const int choice) mutable {
                             if (choice < 0 || choice >= count) return;
                             if (onSelect) onSelect(actions[choice]);
                           });
}
