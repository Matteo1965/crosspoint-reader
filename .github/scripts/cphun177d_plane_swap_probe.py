#!/usr/bin/env python3
from pathlib import Path
p=Path("freeink-sdk/libs/display/FreeInkDisplay/src/driver/Ssd1677Driver.cpp")
s=p.read_text()
old="writeGrayRam(bus, CMD_WRITE_RAM_BW, lsb, _bufferSize);"
new="writeGrayRam(bus, _absoluteInput ? CMD_WRITE_RAM_RED : CMD_WRITE_RAM_BW, lsb, _bufferSize);"
assert s.count(old)==1
s=s.replace(old,new,1)
old="writeGrayRam(bus, CMD_WRITE_RAM_RED, msb, _bufferSize);"
new="writeGrayRam(bus, _absoluteInput ? CMD_WRITE_RAM_BW : CMD_WRITE_RAM_RED, msb, _bufferSize);"
assert s.count(old)==1
s=s.replace(old,new,1)
p.write_text(s)
print("CPHUN-178: Absolute plane assignment retained; no sleepdiag writes")
