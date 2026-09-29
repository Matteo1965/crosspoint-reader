#!/usr/bin/env bash
set -euo pipefail

SDK_REF="fde240faaeae6c340dacd435a4f77d2ef2f82dfd"
SDK_DIR="freeink-sdk"

# CPHUN-177 / upstream #3478:
# Backport only the FreeInkDisplay grayscale-capability layer required by
# CrossPoint absolute grayscale. Do NOT move the whole SDK submodule: the full
# SDK delta also changes unrelated board definitions (including X4 SPI defaults).

git -C "$SDK_DIR" fetch --quiet origin "$SDK_REF"

paths=(
  libs/display/FreeInkDisplay/include/GrayscaleCapabilities.h
  libs/display/FreeInkDisplay/include/FreeInkDisplay.h
  libs/display/FreeInkDisplay/src/FreeInkDisplay.cpp
  libs/display/FreeInkDisplay/src/driver/PanelDriver.h
  libs/display/FreeInkDisplay/src/driver/Ssd1677Driver.cpp
  libs/display/FreeInkDisplay/src/driver/Ssd1677Driver.h
  libs/display/FreeInkDisplay/src/driver/Uc8253X3Driver.h
  libs/display/FreeInkDisplay/src/driver/Uc8279Driver.cpp
  libs/display/FreeInkDisplay/src/driver/Uc8279Driver.h
  libs/display/FreeInkDisplay/src/driver/Uc8179Driver.cpp
  libs/display/FreeInkDisplay/src/driver/Uc8179Driver.h
  libs/display/FreeInkDisplay/src/driver/Uc8279X4Driver.cpp
  libs/display/FreeInkDisplay/src/driver/Uc8279X4Driver.h
)

git -C "$SDK_DIR" checkout "$SDK_REF" -- "${paths[@]}"

# Guard the original X4 board profile from unrelated SDK changes.
grep -q 'constexpr BoardProfile XTEINK_X4' "$SDK_DIR/libs/hardware/BoardConfig/include/BoardConfig.h"
grep -q '#define FREEINK_X4_DISPLAY_SPI_HZ 20000000u' "$SDK_DIR/libs/hardware/BoardConfig/include/BoardConfig.h"

# Capability API and verified X4 absolute grayscale must now be present.
grep -q 'enum class GrayscaleMode' "$SDK_DIR/libs/display/FreeInkDisplay/include/GrayscaleCapabilities.h"
grep -q 'absoluteGrayscale: verified X4 factory LUT' "$SDK_DIR/libs/display/FreeInkDisplay/src/driver/Ssd1677Driver.cpp"

echo "CPHUN-177 selective FreeInk grayscale SDK backport staged"
