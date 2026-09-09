#!/usr/bin/env python3
import base64
import re
import sys
import unicodedata
import zlib
from pathlib import Path

# Exact union of non-ASCII Unicode code points found in the two cleaned Hungarian
# StarDict dictionaries used for CPHUN-85. Stored compactly so the audit remains
# reproducible without committing the dictionary data itself.
DATA = "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"


def dictionary_codepoints():
    raw = zlib.decompress(base64.b64decode(DATA)).decode("ascii")
    return {int(x, 16) for x in raw.split(",") if x}


def header_codepoints(path):
    text = Path(path).read_text(encoding="utf-8")
    cps = set(int(m.group(1), 16) for m in re.finditer(r"// U\+([0-9A-Fa-f]{4,6})", text))
    # Printable ASCII glyph comments use the literal character rather than U+ notation.
    cps.update(range(0x20, 0x7F))
    return cps


def main():
    root = Path(__file__).resolve().parents[1]
    wanted = dictionary_codepoints()
    if len(wanted) != 1333:
        raise SystemExit(f"Expected 1333 non-ASCII dictionary code points, got {len(wanted)}")

    sets = {}
    for size in (12, 14, 16, 18):
        p = root / f"lib/EpdFont/builtinFonts/notoserif_{size}_regular.h"
        sets[size] = header_codepoints(p)

    common = set.intersection(*(sets[s] for s in sets))
    missing = sorted(wanted - common)

    print(f"dictionary_non_ascii={len(wanted)}")
    for size in (12, 14, 16, 18):
        print(f"notoserif_{size}_glyphs={len(sets[size])} dictionary_present={len(wanted & sets[size])}")
    print(f"missing_from_all_sizes={len(missing)}")
    print()
    print("Key test characters:")
    for ch in "↔→−√∞‰♪":
        cp = ord(ch)
        status = "PRESENT" if cp in common else "MISSING"
        print(f"U+{cp:04X}\t{ch}\t{status}\t{unicodedata.name(ch, '<unnamed>')}")
    print()
    print("Exact missing Unicode list:")
    for cp in missing:
        ch = chr(cp)
        printable = ch if not unicodedata.category(ch).startswith("C") else "<control/format>"
        print(f"U+{cp:04X}\t{printable}\t{unicodedata.name(ch, '<unnamed>')}")


if __name__ == "__main__":
    main()
