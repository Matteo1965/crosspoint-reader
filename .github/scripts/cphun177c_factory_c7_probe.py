#!/usr/bin/env python3
"""CPHUN-177C isolated SSD1677 factory activation probe.

Retains 177B's explicit HALF preclean, unchanged Absolute planes, SDK LUT and
all surrounding logic; substitutes the older SDK's factory activation 0xC7 for
0xCC and tracks the power-down it performs. Diagnostic experiment only.
"""
from pathlib import Path

p = Path("freeink-sdk/libs/display/FreeInkDisplay/src/driver/Ssd1677Driver.cpp")
s = p.read_text(encoding="utf-8")
old = """    bus.cmd(CMD_DISPLAY_UPDATE_CTRL2);
    bus.data(0xCC);  // CLOCK_ON|ANALOG_ON|MODE_SELECT|DISPLAY_START
    bus.cmd(CMD_MASTER_ACTIVATION);
    bus.waitRefreshComplete("factory_gray");
    _isScreenOn = true;
    if (turnOff) powerOffController(bus);
    _needsGrayClear = true;  // restoring RAM alone cannot restore B/W ink
"""
new = """    bus.cmd(CMD_DISPLAY_UPDATE_CTRL2);
    // CPHUN-177C: older SDK factory-Absolute activation, isolated versus 177B.
    // 0xC7 starts the same external LUT update and powers the analog/clock off.
    bus.data(0xC7);
    bus.cmd(CMD_MASTER_ACTIVATION);
    bus.waitRefreshComplete("factory_gray");
    _isScreenOn = false;  // 0xC7 already powered down; no second power-off.
    _needsGrayClear = true;  // restoring RAM alone cannot restore B/W ink
"""
if s.count(old) != 1:
    raise SystemExit(f"CPHUN-177C SSD1677 factory activation anchor count={s.count(old)}")
p.write_text(s.replace(old,new,1),encoding="utf-8")
print("CPHUN-177C: SSD1677 factory Absolute activation 0xCC -> 0xC7")
