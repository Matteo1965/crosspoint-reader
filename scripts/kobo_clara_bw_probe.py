#!/usr/bin/env python3
"""CP-KOBO-008: read-only Linux capability inventory for Kobo Clara BW.

No framebuffer writes, device grabs, system changes, or root privileges.
Use --root to run the same inspection against a CI fixture.
"""
import argparse
import json
from pathlib import Path

def read(root, path, limit=8192):
    try:
        return (root / path.lstrip("/")).read_text(errors="replace")[:limit].strip()
    except (OSError, UnicodeError):
        return None

def inspect(root):
    fb_entries = []
    fb_dir = root / "sys/class/graphics"
    if fb_dir.is_dir():
        for path in sorted(fb_dir.glob("fb[0-9]*")):
            fb_entries.append({
                "name": path.name,
                "virtual_size": read(root, f"/sys/class/graphics/{path.name}/virtual_size"),
                "bits_per_pixel": read(root, f"/sys/class/graphics/{path.name}/bits_per_pixel"),
                "stride_bytes": read(root, f"/sys/class/graphics/{path.name}/stride"),
                "device": read(root, f"/sys/class/graphics/{path.name}/name"),
            })
    input_devices = read(root, "/proc/bus/input/devices") or ""
    blocks = []
    for block in input_devices.split("\n\n"):
        if not block.strip(): continue
        name = next((line[3:].strip() for line in block.splitlines() if line.startswith("N: ")), "")
        handlers = next((line[3:].strip() for line in block.splitlines() if line.startswith("H: ")), "")
        if name.startswith("Name="):
            name = name[len("Name="):].strip().strip(\'"\')
        if handlers.startswith("Handlers="):
            handlers = handlers[len("Handlers="):]
        blocks.append({"name":name, "handlers":handlers})
    model = read(root, "/proc/device-tree/model")
    return {
        "model": model.strip("\x00") if model else None,
        "kernel": read(root, "/proc/sys/kernel/osrelease"),
        "framebuffers": fb_entries,
        "input_devices": blocks,
        "fbink_present": (root / "usr/bin/fbink").exists() or (root / "mnt/onboard/.adds/bin/fbink").exists(),
        "note": "Read-only observation only. No evdev axis ranges, rotation, FBInk runtime or device writes verified."
    }

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path("/"))
    parser.add_argument("--output", type=Path)
    args=parser.parse_args()
    report=inspect(args.root)
    result=json.dumps(report,indent=2,ensure_ascii=False)
    if args.output:
        args.output.parent.mkdir(parents=True,exist_ok=True)
        args.output.write_text(result+"\n",encoding="utf-8")
    print(result)

if __name__ == "__main__":
    main()
