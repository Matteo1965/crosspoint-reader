#!/usr/bin/env python3
import argparse
import struct
from pathlib import Path


def read_idx(path: Path):
    data = path.read_bytes()
    pos = 0
    while pos < len(data):
        end = data.find(b"\0", pos)
        if end < 0 or end + 9 > len(data):
            raise ValueError(f"Malformed StarDict index near byte {pos}")
        word = data[pos:end].decode("utf-8", errors="replace")
        offset, size = struct.unpack(">II", data[end + 1:end + 9])
        yield word, offset, size
        pos = end + 9


def norm(s: str) -> str:
    return s.casefold()


def main():
    ap = argparse.ArgumentParser(description="Inspect actual StarDict .idx headwords")
    ap.add_argument("idx", type=Path, help="Path to StarDict .idx file (not .idx.gz)")
    ap.add_argument("terms", nargs="+", help="Terms/prefixes to inspect")
    ap.add_argument("--contains", action="store_true", help="Match anywhere instead of prefix")
    ap.add_argument("--limit", type=int, default=100)
    args = ap.parse_args()

    terms = [(t, norm(t)) for t in args.terms]
    hits = {t: [] for t, _ in terms}
    exact = {t: False for t, _ in terms}

    for word, offset, size in read_idx(args.idx):
        nw = norm(word)
        for original, nt in terms:
            if nw == nt:
                exact[original] = True
            matched = nt in nw if args.contains else nw.startswith(nt)
            if matched and len(hits[original]) < args.limit:
                hits[original].append((word, offset, size))

    for original, _ in terms:
        print(f"\n=== {original} ===")
        print(f"exact headword: {'YES' if exact[original] else 'NO'}")
        if not hits[original]:
            print("no matching headwords")
            continue
        for word, offset, size in hits[original]:
            marker = " [EXACT]" if norm(word) == norm(original) else ""
            print(f"{word}{marker}\toffset={offset}\tsize={size}")


if __name__ == "__main__":
    main()
