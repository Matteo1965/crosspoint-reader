#!/usr/bin/env python3
"""CP-KOBO-010 Clara BW Variant A: FBInk PNG handoff, dry-run by default.

Requires an EXISTING 1072x1448 rendered PNG (e.g. CP-KOBO-006 output).
It does not yet stream live CrossPoint frames or own Kobo's display lifecycle.
"""
import argparse
import json
import os
from pathlib import Path
import shutil
import struct
import subprocess

PANEL = (1072, 1448)
PNG_HEADER = b"\x89PNG\r\n\x1a\n"

def png_dimensions(path):
    with path.open("rb") as f:
        header = f.read(24)
    if len(header) < 24 or header[:8] != PNG_HEADER or header[12:16] != b"IHDR":
        raise ValueError("Expected PNG image with IHDR header")
    return struct.unpack(">II", header[16:24])

def make_command(fbink, image):
    # FBInk CLI supports -i PATH; -W AUTO lets device select refresh waveform.
    return [str(fbink), "-W", "AUTO", "-i", str(image)]

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--image", required=True, type=Path)
    parser.add_argument("--fbink", default="fbink")
    parser.add_argument("--display", action="store_true", help="Request framebuffer display (requires --allow-write)")
    parser.add_argument("--allow-write", action="store_true", help="Explicit opt-in to modifying the displayed image")
    parser.add_argument("--output", type=Path, help="Optional JSON manifest path")
    args = parser.parse_args()
    image = args.image.resolve(strict=True)
    dimensions = png_dimensions(image)
    if dimensions != PANEL:
        parser.error(f"Clara BW screen image must be {PANEL[0]}x{PANEL[1]}, got {dimensions}")
    if args.display != args.allow_write:
        parser.error("Actual display requires BOTH --display and --allow-write; omit both for dry-run")
    executable = shutil.which(args.fbink) if args.display else (shutil.which(args.fbink) or args.fbink)
    if args.display and not executable:
        parser.error("FBInk executable not found. No display action attempted.")
    cmd = make_command(executable, image)
    report = {"device":"Kobo Clara BW", "variant":"A", "image":str(image),
              "dimensions":list(dimensions), "command":cmd, "mode":"display" if args.display else "dry-run",
              "warning":"Not a running CrossPoint app; Kobo framebuffer availability and rotation unverified"}
    if args.output:
        args.output.parent.mkdir(parents=True,exist_ok=True)
        args.output.write_text(json.dumps(report,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    print(json.dumps(report,ensure_ascii=False,indent=2))
    if args.display:
        subprocess.run(cmd,check=True,timeout=30)

if __name__=="__main__":
    main()
