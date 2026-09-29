#!/usr/bin/env python3
from pathlib import Path

p = Path("src/activities/boot_sleep/SleepActivity.cpp")
s = p.read_text(encoding="utf-8")

old = """  const bool absolute =
      hasGreyscale && renderer.grayscaleCapabilities(HalDisplay::GrayscaleMode::Absolute).supported();
"""
new = """  // CPHUN-177A isolation probe: keep the CPHUN-177 SDK/application stack,
  // but force standard bitmap/cover sleep screens through the proven legacy
  // Overlay grayscale path. This changes no image quantization; it isolates
  // the SSD1677 Absolute activation/LUT path from the rest of CPHUN-177.
  const bool absolute = false;
"""
if old not in s:
    raise SystemExit("CPHUN-177A bitmap Absolute selector anchor missing")
if s.count(old) != 1:
    raise SystemExit(f"CPHUN-177A bitmap Absolute selector not unique: {s.count(old)}")
p.write_text(s.replace(old, new, 1), encoding="utf-8")
print("CPHUN-177A: standard bitmap sleep grayscale forced to legacy Overlay mode")
