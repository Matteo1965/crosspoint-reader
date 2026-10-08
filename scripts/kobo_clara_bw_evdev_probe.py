#!/usr/bin/env python3
"""CP-KOBO-009: safe, read-only touchscreen axis discovery.

No EVIOCGRAB, no writes to /dev/input, no framebuffer refreshes, no
firmware changes. Intended for manual invocation on a Kobo via Python 3.
Do not infer rotation from axis ranges alone.
"""
import argparse
import fcntl
import json
import os
import struct
from pathlib import Path

# linux/input-event-codes.h
ABS_X, ABS_Y, ABS_MT_POSITION_X, ABS_MT_POSITION_Y = 0x00, 0x01, 0x35, 0x36
AXES = {"ABS_X": ABS_X, "ABS_Y": ABS_Y,
        "ABS_MT_POSITION_X": ABS_MT_POSITION_X,
        "ABS_MT_POSITION_Y": ABS_MT_POSITION_Y}
ABSINFO_FORMAT = "iiiiii"
ABSINFO_SIZE = struct.calcsize(ABSINFO_FORMAT)

def eviocgabs(axis):
    # _IOC(_IOC_READ, 'E', 0x40 + axis, sizeof(input_absinfo))
    return (2 << 30) | (ABSINFO_SIZE << 16) | (ord("E") << 8) | (0x40 + axis)

def probe_event(path):
    result = {"path": str(path), "axes": {}}
    try:
        fd = os.open(path, os.O_RDONLY | os.O_NONBLOCK | getattr(os, "O_CLOEXEC", 0))
    except OSError as exc:
        result["error"] = f"{type(exc).__name__}: {exc.strerror}"
        return result
    try:
        for name, code in AXES.items():
            buf = bytearray(ABSINFO_SIZE)
            try:
                fcntl.ioctl(fd, eviocgabs(code), buf, True)
            except OSError:
                continue  # Axis not implemented by this device
            value, minimum, maximum, fuzz, flat, resolution = struct.unpack(ABSINFO_FORMAT, buf)
            result["axes"][name] = {"min": minimum, "max": maximum,
                                   "value": value, "fuzz": fuzz,
                                   "flat": flat, "resolution": resolution}
    finally:
        os.close(fd)
    return result

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--device", action="append", type=Path,
                   help="Input event device to query; repeat as needed. Default: /dev/input/event*.")
    p.add_argument("--output", type=Path, help="JSON output path (optional)")
    args = p.parse_args()
    devices = args.device if args.device is not None else sorted(Path("/dev/input").glob("event*"))
    report = {"purpose": "CP-KOBO-009 read-only evdev ABS axis report",
              "devices": [probe_event(d) for d in devices],
              "warning": "Axis orientation and touch/display rotation need on-device tap calibration."}
    data = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(data, encoding="utf-8")
    print(data, end="")

if __name__ == "__main__":
    main()
