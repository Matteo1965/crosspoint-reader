#!/usr/bin/env python3
"""CP-KOBO-006: pure host-side Kobo Clara BW viewport + coordinate validation.

This is NOT a Kobo framebuffer or evdev driver. It validates the exact
logical-to-panel transform that such drivers will share.
"""
import argparse
import json
from pathlib import Path

LOGICAL_W, LOGICAL_H = 480, 800
PANEL_W, PANEL_H = 1072, 1448
# Fit height exactly, preserve aspect ratio, center horizontally.
VIEW_H = PANEL_H
VIEW_W = round(LOGICAL_W * PANEL_H / LOGICAL_H)
VIEW_X = (PANEL_W - VIEW_W) // 2
VIEW_Y = (PANEL_H - VIEW_H) // 2


def logical_to_panel(x, y):
    if not (0 <= x < LOGICAL_W and 0 <= y < LOGICAL_H):
        raise ValueError("logical point outside viewport")
    return VIEW_X + (x * VIEW_W) // LOGICAL_W, VIEW_Y + (y * VIEW_H) // LOGICAL_H


def panel_to_logical(x, y):
    if not (VIEW_X <= x < VIEW_X + VIEW_W and VIEW_Y <= y < VIEW_Y + VIEW_H):
        return None
    return min(LOGICAL_W - 1, ((x - VIEW_X) * LOGICAL_W) // VIEW_W), min(LOGICAL_H - 1, ((y - VIEW_Y) * LOGICAL_H) // VIEW_H)


def verify():
    assert (VIEW_X, VIEW_Y, VIEW_W, VIEW_H) == (101, 0, 869, 1448)
    assert panel_to_logical(100, 700) is None
    assert panel_to_logical(970, 700) is None
    for x, y in [(0, 0), (479, 799), (240, 400), (340, 710), (420, 450)]:
        px, py = logical_to_panel(x, y)
        xx, yy = panel_to_logical(px, py)
        assert abs(xx-x) <= 1 and abs(yy-y) <= 1, ((x,y), (xx,yy))
    for py in range(0, PANEL_H, 29):
        for px in range(VIEW_X, VIEW_X + VIEW_W, 23):
            result = panel_to_logical(px, py)
            assert result is not None
            assert 0 <= result[0] < LOGICAL_W and 0 <= result[1] < LOGICAL_H


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, help="CrossPoint 480x800 BMP screenshot")
    parser.add_argument("--output", type=Path, default=Path("qa-clara-bw"))
    args = parser.parse_args()
    verify()
    args.output.mkdir(parents=True, exist_ok=True)
    points = {"home_settings": (340,710), "reader_next": (420,450), "screen_center": (240,400)}
    metadata = {
        "device": "Kobo Clara BW",
        "logical": [LOGICAL_W, LOGICAL_H],
        "panel": [PANEL_W, PANEL_H],
        "viewport": [VIEW_X, VIEW_Y, VIEW_W, VIEW_H],
        "scale": PANEL_H / LOGICAL_H,
        "touch_map": {name:{"logical":[x,y],"panel":list(logical_to_panel(x,y))} for name,(x,y) in points.items()},
        "note": "simulator geometry only; no actual Kobo framebuffer, evdev or rotation verified"
    }
    (args.output/"geometry.json").write_text(json.dumps(metadata,ensure_ascii=False,indent=2),encoding="utf-8")
    if args.source:
        from PIL import Image, ImageOps, ImageDraw
        with Image.open(args.source) as source:
            source=source.convert("RGB")
            assert source.size == (LOGICAL_W,LOGICAL_H), source.size
            canvas=Image.new("RGB",(PANEL_W,PANEL_H),"white")
            scaled=source.resize((VIEW_W, VIEW_H), resample=Image.Resampling.NEAREST)
            canvas.paste(scaled,(VIEW_X,VIEW_Y))
            canvas.save(args.output/"clara-bw-1072x1448.png")
            overlay=canvas.copy()
            draw=ImageDraw.Draw(overlay)
            for x,y in points.values():
                px,py=logical_to_panel(x,y)
                draw.ellipse((px-9,py-9,px+9,py+9),outline="red",width=3)
            overlay.save(args.output/"clara-bw-touch-targets.png")
    print("Clara BW geometry OK: logical 480x800 => viewport", (VIEW_X, VIEW_Y, VIEW_W, VIEW_H), "in panel", (PANEL_W, PANEL_H))

if __name__ == "__main__":
    main()
