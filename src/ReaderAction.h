#pragma once

#include <cstdint>

// CPHUN-36 configurable reader actions.
//
// IMPORTANT: ReaderAction values are persisted in settings.json. Existing values
// must never be reordered or reused. New actions may only be appended before
// COUNT so saved button profiles remain compatible across firmware upgrades.
enum class ReaderAction : uint8_t {
  None = 0,

  // Navigation / reading
  ReaderBack = 1,
  PreviousPage = 2,
  NextPage = 3,
  PreviousChapter = 4,
  NextChapter = 5,
  OpenReaderMenu = 6,
  OpenDictionary = 7,
  OpenBookmarks = 8,
  ToggleBookmark = 9,
  OpenChapterSelection = 10,
  OpenGoToPercent = 11,

  // Direct text-setting screens
  OpenTextSettings = 12,
  OpenFontMenu = 13,
  OpenFontSizeMenu = 14,
  OpenLayoutMenu = 15,
  OpenStyleMenu = 16,

  // Immediate text-setting steps. These keep the reader on-screen, persist the
  // new value and trigger the normal reader relayout/re-render path.
  FontNext = 17,
  FontPrevious = 18,
  FontSizeUp = 19,
  FontSizeDown = 20,
  LineSpacingNext = 21,
  LineSpacingPrevious = 22,
  ScreenMarginUp = 23,
  ScreenMarginDown = 24,

  // Toggle-style actions
  ToggleNightMode = 25,
  ToggleHyphenation = 26,
  ToggleSoftHyphen = 27,
  ToggleParagraphAlignment = 28,

  // Display / utility actions
  RotateOrientation = 29,
  ForceRefresh = 30,
  Screenshot = 31,
  GoHome = 32,
  OpenSettings = 33,

  COUNT
};

enum class ReaderActionGroup : uint8_t {
  None,
  Menu,
  Immediate,
  Toggle,
};

constexpr bool isValidReaderAction(const uint8_t value) {
  return value < static_cast<uint8_t>(ReaderAction::COUNT);
}

constexpr ReaderActionGroup readerActionGroup(const ReaderAction action) {
  switch (action) {
    case ReaderAction::None:
      return ReaderActionGroup::None;

    case ReaderAction::OpenReaderMenu:
    case ReaderAction::OpenDictionary:
    case ReaderAction::OpenBookmarks:
    case ReaderAction::OpenChapterSelection:
    case ReaderAction::OpenGoToPercent:
    case ReaderAction::OpenTextSettings:
    case ReaderAction::OpenFontMenu:
    case ReaderAction::OpenFontSizeMenu:
    case ReaderAction::OpenLayoutMenu:
    case ReaderAction::OpenStyleMenu:
    case ReaderAction::OpenSettings:
      return ReaderActionGroup::Menu;

    case ReaderAction::ToggleBookmark:
    case ReaderAction::ToggleNightMode:
    case ReaderAction::ToggleHyphenation:
    case ReaderAction::ToggleSoftHyphen:
    case ReaderAction::ToggleParagraphAlignment:
      return ReaderActionGroup::Toggle;

    default:
      return ReaderActionGroup::Immediate;
  }
}

static_assert(static_cast<uint8_t>(ReaderAction::COUNT) <= 255,
              "ReaderAction must remain persistable in one uint8_t");
