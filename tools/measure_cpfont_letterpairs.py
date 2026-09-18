#!/usr/bin/env python3
"""Measure optical gaps for Hungarian lowercase letter pairs in a v4 .cpfont.

The metric reproduction matches the Bitter16 reference table exactly:
- 35 lowercase Hungarian letters -> 1225 ordered pairs
- threshold 1 and threshold 2 ink edges
- median gap
- lower Q25/Q10 using floor(p * (n - 1))
- common scanline count
- kerning in pixels
- native cursor step in pixels
"""

from __future__ import annotations

import argparse
import csv
import math
import statistics
import struct
from pathlib import Path

CHARS = "abcdefghijklmnopqrstuvwxyzáéíóöúüőű"
GLYPH_STRUCT = "<BBHhhH2xI"
TOC_STRUCT = "<B3xIIBhhHHBBBI4x"


class CpFont:
    def __init__(self, path: Path, style_id: int = 0):
        self.data = path.read_bytes()
        magic, self.version, self.flags, style_count, _ = struct.unpack_from(
            "<8sHHB19s", self.data, 0
        )
        if magic != b"CPFONT\x00\x00":
            raise ValueError(f"{path}: not a CPFONT file")

        toc = [
            struct.unpack_from(TOC_STRUCT, self.data, 32 + i * 32)
            for i in range(style_count)
        ]
        try:
            (
                _sid,
                interval_count,
                glyph_count,
                self.advance_y,
                self.ascender,
                self.descender,
                kern_l_count,
                kern_r_count,
                kern_l_classes,
                kern_r_classes,
                lig_count,
                pos,
            ) = next(v for v in toc if v[0] == style_id)
        except StopIteration as exc:
            raise ValueError(f"{path}: style {style_id} not found") from exc

        self.intervals = [
            struct.unpack_from("<III", self.data, pos + i * 12)
            for i in range(interval_count)
        ]
        pos += interval_count * 12

        self.glyphs = [
            struct.unpack_from(GLYPH_STRUCT, self.data, pos + i * 16)
            for i in range(glyph_count)
        ]
        pos += glyph_count * 16

        left_entries = [
            struct.unpack_from("<HB", self.data, pos + i * 3)
            for i in range(kern_l_count)
        ]
        pos += kern_l_count * 3
        right_entries = [
            struct.unpack_from("<HB", self.data, pos + i * 3)
            for i in range(kern_r_count)
        ]
        pos += kern_r_count * 3

        matrix_count = kern_l_classes * kern_r_classes
        self.kern_matrix = (
            struct.unpack_from(f"<{matrix_count}b", self.data, pos)
            if matrix_count
            else ()
        )
        pos += matrix_count
        pos += lig_count * 8
        self.bitmap_base = pos

        self.kern_l_classes = kern_l_classes
        self.kern_r_classes = kern_r_classes
        self.left_class = dict(left_entries)
        self.right_class = dict(right_entries)

        self.cp_to_index = {}
        for start, end, offset in self.intervals:
            for cp in range(start, end + 1):
                self.cp_to_index[cp] = offset + cp - start

    def kerning_fp4(self, left: int, right: int) -> int:
        lc = self.left_class.get(left, 0)
        rc = self.right_class.get(right, 0)
        if lc == 0 or rc == 0:
            return 0
        return self.kern_matrix[(lc - 1) * self.kern_r_classes + (rc - 1)]

    def glyph(self, cp: int):
        w, h, adv, left, top, data_len, data_offset = self.glyphs[
            self.cp_to_index[cp]
        ]
        raw = self.data[
            self.bitmap_base + data_offset : self.bitmap_base + data_offset + data_len
        ]
        pixels = []
        for n in range(w * h):
            b = raw[n // 4]
            shift = (3 - (n % 4)) * 2
            pixels.append((b >> shift) & 0x03)
        rows = [pixels[y * w : (y + 1) * w] for y in range(h)]
        return {
            "width": w,
            "height": h,
            "advance_fp4": adv,
            "left": left,
            "top": top,
            "rows": rows,
        }


def lower_quantile(values: list[int], p: float) -> int:
    values = sorted(values)
    return values[int(math.floor(p * (len(values) - 1)))]


def pair_metrics(font: CpFont, pair: str, threshold: int):
    left_cp, right_cp = map(ord, pair)
    left = font.glyph(left_cp)
    right = font.glyph(right_cp)
    kern_fp4 = font.kerning_fp4(left_cp, right_cp)
    cursor_step = (left["advance_fp4"] + kern_fp4 + 8) >> 4

    left_rows = {}
    for row_index, row in enumerate(left["rows"]):
        xs = [left["left"] + x for x, value in enumerate(row) if value >= threshold]
        if xs:
            left_rows[row_index - left["top"]] = (min(xs), max(xs))

    right_rows = {}
    for row_index, row in enumerate(right["rows"]):
        xs = [
            cursor_step + right["left"] + x
            for x, value in enumerate(row)
            if value >= threshold
        ]
        if xs:
            right_rows[row_index - right["top"]] = (min(xs), max(xs))

    common_rows = sorted(set(left_rows) & set(right_rows))
    gaps = [
        right_rows[y][0] - left_rows[y][1] - 1
        for y in common_rows
    ]
    if not gaps:
        raise ValueError(f"No common ink scanlines for pair {pair!r}, threshold={threshold}")

    return {
        "median": statistics.median(gaps),
        "q25": lower_quantile(gaps, 0.25),
        "q10": lower_quantile(gaps, 0.10),
        "overlap_rows": len(gaps),
        "kern_px": kern_fp4 / 16.0,
        "cursor_step_px": cursor_step,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("cpfont", type=Path)
    parser.add_argument("-o", "--output", type=Path, required=True)
    parser.add_argument("--style-id", type=int, default=0)
    args = parser.parse_args()

    font = CpFont(args.cpfont, args.style_id)
    fieldnames = [
        "pair",
        "median_gap_thr1",
        "q25_gap_thr1",
        "q10_gap_thr1",
        "overlap_rows_thr1",
        "kern_px",
        "cursor_step_px",
        "median_gap_thr2",
        "q25_gap_thr2",
        "q10_gap_thr2",
        "overlap_rows_thr2",
        "kern_px_thr2",
        "cursor_step_px_thr2",
    ]

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8", newline="") as out:
        writer = csv.DictWriter(out, fieldnames=fieldnames)
        writer.writeheader()
        for left in CHARS:
            for right in CHARS:
                pair = left + right
                t1 = pair_metrics(font, pair, 1)
                t2 = pair_metrics(font, pair, 2)
                writer.writerow(
                    {
                        "pair": pair,
                        "median_gap_thr1": t1["median"],
                        "q25_gap_thr1": t1["q25"],
                        "q10_gap_thr1": t1["q10"],
                        "overlap_rows_thr1": t1["overlap_rows"],
                        "kern_px": t1["kern_px"],
                        "cursor_step_px": t1["cursor_step_px"],
                        "median_gap_thr2": t2["median"],
                        "q25_gap_thr2": t2["q25"],
                        "q10_gap_thr2": t2["q10"],
                        "overlap_rows_thr2": t2["overlap_rows"],
                        "kern_px_thr2": t2["kern_px"],
                        "cursor_step_px_thr2": t2["cursor_step_px"],
                    }
                )

    print(f"Wrote 1225 pair metrics to {args.output}")


if __name__ == "__main__":
    main()
