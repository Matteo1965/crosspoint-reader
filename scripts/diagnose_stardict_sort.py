#!/usr/bin/env python3
import argparse
import struct
from pathlib import Path

SAMPLE_INTERVAL = 256


def read_entries(path: Path):
    data = path.read_bytes()
    out = []
    pos = 0
    while pos < len(data):
        end = data.find(b"\0", pos)
        if end < 0 or end + 9 > len(data):
            raise ValueError(f"Malformed StarDict index near byte {pos}")
        raw = data[pos:end]
        word = raw.decode("utf-8", errors="replace")
        offset, size = struct.unpack(">II", data[end + 1:end + 9])
        out.append((word, raw, pos, offset, size))
        pos = end + 9
    return out


def ascii_case_key(raw: bytes):
    return bytes((b + 32 if 65 <= b <= 90 else b) for b in raw)


def locate(entries, target: str, keyfn):
    target_raw = target.encode("utf-8")
    samples = list(range(0, len(entries), SAMPLE_INTERVAL))
    lo, hi = 0, len(samples) - 1
    target_key = keyfn(target_raw)
    while lo < hi:
        mid = (lo + hi + 1) // 2
        idx = samples[mid]
        if keyfn(entries[idx][1]) <= target_key:
            lo = mid
        else:
            hi = mid - 1
    start = samples[lo]
    stop = min(start + SAMPLE_INTERVAL + 1, len(entries))
    for i in range(start, stop):
        wk = keyfn(entries[i][1])
        if wk == target_key:
            return True, start, i, entries[i][0]
        if wk > target_key:
            return False, start, i, entries[i][0]
    return False, start, stop - 1, entries[stop - 1][0]


def first_inversion(entries, keyfn):
    prev = keyfn(entries[0][1])
    for i in range(1, len(entries)):
        cur = keyfn(entries[i][1])
        if cur < prev:
            return i - 1, entries[i - 1][0], i, entries[i][0]
        prev = cur
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("idx", type=Path)
    ap.add_argument("terms", nargs="+", default=["kabát"])
    args = ap.parse_args()
    entries = read_entries(args.idx)
    print(f"entries: {len(entries)}")

    comparators = [
        ("raw-byte", lambda b: b),
        ("ascii-case-insensitive", ascii_case_key),
    ]

    for name, keyfn in comparators:
        inv = first_inversion(entries, keyfn)
        print(f"\n=== comparator: {name} ===")
        if inv:
            a_i, a, b_i, b = inv
            print(f"first ordering inversion: entry {a_i} {a!r} -> entry {b_i} {b!r}")
        else:
            print("index is monotonic under this comparator")
        for term in args.terms:
            found, start, at, word = locate(entries, term, keyfn)
            print(f"{term}: {'FOUND' if found else 'NOT FOUND'}; sample_start={start}; stopped_at={at} {word!r}")

    for term in args.terms:
        exact = [i for i, e in enumerate(entries) if e[0] == term]
        print(f"\nexact physical entry for {term!r}: {exact[0] if exact else 'NONE'}")


if __name__ == "__main__":
    main()
