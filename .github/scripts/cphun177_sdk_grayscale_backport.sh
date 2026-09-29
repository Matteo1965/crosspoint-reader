#!/usr/bin/env bash
set -euo pipefail

SDK_DIR="freeink-sdk"

# CPHUN-172 release sync already selects FreeInk SDK 13418e0..., which is newer
# than the SDK snapshot used by upstream #3478 and already contains the complete
# GrayscaleMode / GrayscaleCapabilities / X4 SSD1677 absolute-grayscale support.
# Therefore do not replace SDK files here: doing so would downgrade newer SDK
# fixes. Only verify the APIs that the application-side CPHUN-177 backport needs.

grep -q 'enum class GrayscaleMode' "$SDK_DIR/libs/display/FreeInkDisplay/include/GrayscaleCapabilities.h"
grep -q 'Absolute' "$SDK_DIR/libs/display/FreeInkDisplay/include/GrayscaleCapabilities.h"
grep -q 'GrayscaleCapabilities grayscaleCapabilities' "$SDK_DIR/libs/display/FreeInkDisplay/include/FreeInkDisplay.h"
grep -q 'absoluteGrayscale: verified X4 factory LUT' "$SDK_DIR/libs/display/FreeInkDisplay/src/driver/Ssd1677Driver.cpp"

echo "CPHUN-177: release-sync FreeInk SDK already provides #3478 grayscale capability layer"
