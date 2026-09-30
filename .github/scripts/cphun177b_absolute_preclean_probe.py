#!/usr/bin/env python3
"""CPHUN-177B single-variable panel-state probe.

After the normal bitmap BW workbuffer is prepared and dumped, run one HALF
refresh to put physical ink in a known BW state before the otherwise unchanged
X4 Absolute grayscale pass. Keep factory LUT, plane inversion, 0xCC activation
and shutdown identical to CPHUN-177. This is an isolation test, not a final fix.
"""
from pathlib import Path

p = Path("src/activities/boot_sleep/SleepActivity.cpp")
s = p.read_text(encoding="utf-8")

old = """  dumpSleepDiagPlane177("/sleepdiag/cphun177_bitmap_bw.bin", renderer);
  if (absolute) {
    if (!renderer.displayGrayscaleBase(HalDisplay::GrayscaleMode::Absolute)) return;
"""
new = """  dumpSleepDiagPlane177("/sleepdiag/cphun177_bitmap_bw.bin", renderer);
  if (absolute) {
    // CPHUN-177B: isolated physical-panel precondition. BW pixels, both gray
    // planes, factory LUT and absolute activation remain unchanged.
    renderer.displayBuffer(HalDisplay::HALF_REFRESH);
    if (!renderer.displayGrayscaleBase(HalDisplay::GrayscaleMode::Absolute)) return;
"""
if s.count(old) != 1:
    raise SystemExit(f"CPHUN-177B expected exactly one cover precondition anchor, found {s.count(old)}")
s = s.replace(old, new, 1)

old_meta = 'out.print("build=CPHUN-260929-177-GRAY-SLEEPDIAG\\n");'
new_meta = 'out.print("build=CPHUN-260930-177B-ABS-PRECLEAN\\n");'
if s.count(old_meta) != 1:
    raise SystemExit("CPHUN-177B sleepdiag build metadata anchor missing")
s = s.replace(old_meta, new_meta, 1)

p.write_text(s, encoding="utf-8")
print("CPHUN-177B: bitmap Absolute mode with exactly one HALF BW preclean")
