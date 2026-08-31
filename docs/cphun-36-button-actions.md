# CPHUN-36 configurable reader button actions

## Scope

CPHUN-36 adds configurable reader actions for the four physical X4 front/bottom buttons.
Each physical button exposes three gestures:

- single click (1x)
- double click (2x)
- hold

This yields 12 independently configurable action slots.

The mapping is tied to the physical front buttons, not to the current logical
Back/Confirm/Left/Right remap. This keeps gesture assignments predictable across
orientation and logical-role changes and leaves the action model reusable on
future devices with other input sources.

## Factory defaults

The factory profile reproduces the clean CPHUN-35 default single-click reader
behaviour:

| Physical button | 1x | 2x | Hold |
| --- | --- | --- | --- |
| Back | Reader Back | None | None |
| Confirm | Reader Menu | None | None |
| Left | Previous Page | None | None |
| Right | Next Page | None | None |

The existing CPHUN-35 factory defaults for configurable hold behaviour are Off /
Disabled, therefore the clean CPHUN-36 factory profile also starts all Hold slots
at None. Migration of a user's non-default legacy long-press choices is a separate
compatibility task and must not change the factory profile.

A `Factory Defaults` action in Settings -> Controls -> Button Functions restores
only this 12-slot reader button profile. It must not reset unrelated device or
reader settings.

## ReaderAction persistence contract

`ReaderAction` values are persisted as `uint8_t` values. Existing enum values must
never be reordered, deleted and reused, or inserted between older values. New
values are append-only. Unknown stored values fall back to `None`.

## Function chooser groups

The UI groups actions for readability, while the backend keeps one common
`ReaderAction` enum.

### Menus and screens

These actions leave the reading surface and open an existing screen or submenu:

- Reader Menu
- Dictionary
- Bookmarks
- Chapter Selection
- Go To Percent
- Text Settings
- Font menu (`TextSettingsActivity::Tab::Family`)
- Font Size menu (`TextSettingsActivity::Tab::Size`)
- Layout menu (`TextSettingsActivity::Tab::Layout`)
- Style menu (`TextSettingsActivity::Tab::Style`)

The Text Settings shortcuts must reuse the existing `TextSettingsActivity`
initial-tab parameter. Do not duplicate those screens.

### Immediate commands

These actions execute immediately and keep the reader visible:

- Reader Back
- Previous / Next Page
- Previous / Next Chapter
- Previous / Next Font
- Font Size - / +
- Previous / Next Line Spacing
- Screen Margin - / +
- Rotate Orientation
- Force Refresh
- Screenshot
- Home

Text-setting step actions must:

1. select the previous/next legal value using the same source of truth as the
   corresponding settings screen;
2. persist the new setting;
3. invalidate/rebuild the reader layout when the setting affects pagination;
4. remain on the reading screen so the visual change can be compared rapidly.

This behaviour is intentionally suitable for development and typography testing.

### Toggle actions

Toggle actions use one action per feature, not separate On and Off actions:

- Night Mode
- Bookmark
- Hyphenation
- Soft Hyphen
- Paragraph Alignment toggle

The action flips the current state and immediately applies the normal reader
refresh/relayout path required by that setting.

## Gesture detection contract

Double-click support must not execute the first click prematurely. Planned reader
front-button gesture handling:

1. first release arms a pending single-click;
2. a second release inside the double-click window cancels the pending single and
   emits Double;
3. timeout emits Single;
4. Hold emits Hold and suppresses both Single and Double for that contact;
5. gesture recognition uses physical front-button identity before logical button
   remapping.

The Enhanced Reading Mod's ~400 ms double-click model is a behavioural reference,
but CPHUN-36 keeps the action mapping generic and configurable.

## Settings UI

Location:

`Settings -> Controls -> Button Functions`

Initial structure:

- Button 1 / physical Back
- Button 2 / physical Confirm
- Button 3 / physical Left
- Button 4 / physical Right
- Factory Defaults

Each button opens:

- 1x press
- 2x press
- Hold

Each gesture opens the grouped ReaderAction chooser. `None` is always the first
choice so a gesture can be disabled quickly.

## Compatibility rules

- Do not alter Hungarian hyphenation or typography code in CPHUN-36 button work.
- Preserve the existing front-button logical remap feature.
- Preserve legacy settings until migration is explicitly implemented and tested.
- Hide the physical-front-button configuration screen on boards that do not have
  the four X4-style front buttons; the generic ReaderAction model remains usable
  by future touch, Home, Power, or side-button mappings.
