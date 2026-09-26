# CPHUN-157 — Selected upstream 1.6.5rc fixes

Base: agent/cphun-156-longword-settings-and-encoding (available development branch; not independently verified as the source of the last tested firmware).
Upstream reference: https://github.com/crosspoint-reader/crosspoint-reader/releases/tag/1.6.5rc

## Scope and status

- [ ] USB cable unplug / soft-disconnect. Upstream: src/activities/network/UsbDriveActivity.cpp and lib/hal/HalStorage.cpp; that upstream activity path is absent in the selected HU base, so locate the HU USB ownership before porting.
- [ ] Short button taps while idle. Upstream: src/main.cpp 50 ms idle polling in 10 ms slices plus HalGPIO::rawInputActive(). The HU HAL lacks this helper; verify the selected freeink-sdk InputManager exposes isPowerButtonPhysicallyPressed/readButtonAdc before using the upstream implementation.
- [ ] Dropped presses during list repaint. Upstream UiListActivity uses requestSelection/requestScroll and new FreeInk viewport API. The HU branch uses RenderLock and an older viewport API; do not replace wholesale without adapting the UI SDK and preserving the HU row-height changes.
- [ ] Sleep-screen grayscale and transparency. Upstream requires gray-plane capability checks; preserve HU sleep-overlay BMP/PNG handling and verify screen capabilities before porting.
- [x] End-of-book menu selection race. Ported upstream atomic selector with relaxed load/store for input and render tasks into EndOfBookOptions.h/.cpp.
- [ ] Chapter position display fix. Compare upstream EpubReaderActivity chapterPosition() and menu construction with HU reader page calculation, preserving reindexing and Hungarian hyphenation.

## Test matrix before a release build

1. USB plug, enter drive mode, unplug without OS eject, reconnect, leave drive mode.
2. Rapid short Up/Down/Confirm/Back taps after prolonged idle and immediately after wake.
3. Repeated taps while large list repaints, including RoundedRaff dense rows.
4. Transparent PNG/BGRA BMP overlays over dark/light pages, grayscale and inverted cover.
5. Chapter first/middle/last pages, in-progress reindex, end-of-book selection with rapid navigation and confirm.
6. Ensure Hungarian extended hyphenation, letter spacing, SD card fonts and setting persistence are unchanged.

Do not merge to a tested release branch or mark the five items complete until the remaining code ports and hardware tests pass.
