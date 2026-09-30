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
p=Path("src/activities/boot_sleep/SleepActivity.cpp")
s=p.read_text()
old='build=CPHUN-260930-177B-ABS-PRECLEAN'
assert s.count(old)==1
p.write_text(s.replace(old,'build=CPHUN-260930-177D-ABS-PLANESWAP',1))
print("CPHUN-177D: only Absolute plane assignment changed")
