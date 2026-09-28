#!/usr/bin/env python3
from pathlib import Path

def replace_once(path, old, new):
    p=Path(path)
    s=p.read_text(encoding="utf-8")
    if old not in s:
        raise SystemExit(f"CPHUN-176 anchor missing in {path}: {old[:120]!r}")
    if s.count(old)!=1:
        raise SystemExit(f"CPHUN-176 anchor not unique in {path}: {old[:120]!r}")
    p.write_text(s.replace(old,new,1),encoding="utf-8")

# Upstream #3541 independent fix: exact 4-level quantization without dithering.
# This maps 0..255 into 0..3 by the top two bits, avoiding the uneven /85 buckets.
replace_once(
    "lib/Epub/Epub/converters/PngToFramebufferConverter.cpp",
    """          } else {
            ditheredGray = gray / 85;
            if (ditheredGray > 3) ditheredGray = 3;
          }
""",
    """          } else {
            // Upstream #3541: exact 2-bit grayscale quantization.
            ditheredGray = gray >> 6;
          }
"""
)

# Keep the non-alpha BMP transparent-overlay path explicitly documented and
# guarded: white pixels (val==3) are not painted in BW mode, so the retained
# reader framebuffer remains visible underneath. This is the #3541
# white-as-transparent behavior adapted to our pre-#3478 renderer.
replace_once(
    "lib/GfxRenderer/GfxRenderer.cpp",
    """      const uint8_t val = outputRow[bmpX / 4] >> (6 - ((bmpX * 2) % 8)) & 0x3;

      if (renderMode == BW && val < 3) {
""",
    """      const uint8_t val = outputRow[bmpX / 4] >> (6 - ((bmpX * 2) % 8)) & 0x3;

      // CPHUN-176 / upstream #3541: in the transparent sleep-overlay path,
      // white (val==3) is paper and remains untouched in BW rendering.
      // The general bitmap renderer already has this behavior because only
      // val<3 is painted; keep it explicit here until #3478 supplies the
      // Direct/Absolute grayscale capability path used by upstream #3541.
      if (renderMode == BW && val < 3) {
"""
)

# Make the dependency boundary explicit in SleepActivity so the subsequent
# #3478 integration can replace only the grayscale pipeline, not the existing
# transparent overlay feature.
replace_once(
    "src/activities/boot_sleep/SleepActivity.cpp",
    """void SleepActivity::renderBitmapSleepScreen(const Bitmap& bitmap, const bool preserveBackground) const {
""",
    """// CPHUN-176: upstream #3541's Direct/Absolute grayscale branch depends on
// the capability consolidation introduced by #3478. The independent #3541
// quantization/transparency fixes are backported now; this existing HALF-base
// pipeline is intentionally retained until #3478 is integrated next.
void SleepActivity::renderBitmapSleepScreen(const Bitmap& bitmap, const bool preserveBackground) const {
"""
)

print("CPHUN-176 upstream #3541 safe backport applied")
