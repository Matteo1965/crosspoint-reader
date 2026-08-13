#!/usr/bin/env python3
import argparse
import struct
from pathlib import Path

SAMPLE_INTERVAL = 256


def ascii_case_key_bytes(b: bytes) -> bytes:
    out = bytearray()
    for x in b:
        if 65 <= x <= 90:
            out.append(x + 32)
        else:
            out.append(x)
    return bytes(out)


def ascii_case_cmp(a: str, b: str) -> int:
    aa = ascii_case_key_bytes(a.encode('utf-8'))
    bb = ascii_case_key_bytes(b.encode('utf-8'))
    return (aa > bb) - (aa < bb)


def read_entries(data: bytes):
    pos = 0
    entry = 0
    while pos < len(data):
        start = pos
        end = data.find(b'\0', pos)
        if end < 0 or end + 9 > len(data):
            raise ValueError(f'Malformed .idx near byte {pos}')
        word = data[pos:end].decode('utf-8', errors='replace')
        offset, size = struct.unpack('>II', data[end+1:end+9])
        yield entry, start, word, offset, size
        entry += 1
        pos = end + 9


def build_samples(entries):
    samples = []
    for entry, start, word, offset, size in entries:
        if entry % SAMPLE_INTERVAL == 0:
            samples.append((entry, start, word))
    return samples


def locate(entries, samples, target):
    lo = 0
    hi = len(samples) - 1
    while lo < hi:
        mid = (lo + hi + 1) // 2
        word = samples[mid][2]
        if ascii_case_cmp(word, target) <= 0:
            lo = mid
        else:
            hi = mid - 1
    start_entry = samples[lo][0] if samples else 0
    for entry, start, word, offset, size in entries[start_entry:start_entry + SAMPLE_INTERVAL + 2]:
        cmp = ascii_case_cmp(word, target)
        if cmp == 0:
            return True, word, entry, start, offset, size, start_entry
        if cmp > 0:
            return False, word, entry, start, None, None, start_entry
    return False, None, None, None, None, None, start_entry


def main():
    ap = argparse.ArgumentParser(description='Simulate CrossPoint Dictionary::locate() against a StarDict .idx file')
    ap.add_argument('idx', type=Path)
    ap.add_argument('terms', nargs='+')
    args = ap.parse_args()

    data = args.idx.read_bytes()
    entries = list(read_entries(data))
    samples = build_samples(entries)
    print(f'entries={len(entries)} samples={len(samples)} interval={SAMPLE_INTERVAL}')

    for term in args.terms:
        found, word, entry, start, offset, size, sample_entry = locate(entries, samples, term)
        print(f'\n=== {term} ===')
        print(f'sample start entry: {sample_entry}')
        print(f'found: {"YES" if found else "NO"}')
        if found:
            print(f'matched: {word}')
            print(f'entry={entry} idx_byte={start} dict_offset={offset} size={size}')
        elif word is not None:
            print(f'scan stopped at: {word} (entry {entry})')


if __name__ == '__main__':
    main()
