#!/usr/bin/env python3
from __future__ import annotations

import argparse
import ast
import csv
import math
import re
from pathlib import Path

SIZES = (12, 14, 16, 18)
THRESHOLDS = (50, 55, 60, 65, 70, 75)
WEIGHTS = {
    "q25": 0.34,
    "median": 0.26,
    "q10": 0.16,
    "overlap": 0.14,
    "kern": 0.10,
}

def read_rows(path: Path):
    with path.open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))

def mean2(row, a, b):
    return (float(row[a]) + float(row[b])) / 2.0

def percentile_ranks(values):
    order = sorted(range(len(values)), key=lambda i: values[i])
    ranks = [0.0] * len(values)
    i = 0
    n = len(values)
    while i < n:
        j = i + 1
        while j < n and values[order[j]] == values[order[i]]:
            j += 1
        avg_rank = ((i + (j - 1)) / 2.0) / max(1, n - 1)
        for k in range(i, j):
            ranks[order[k]] = avg_rank
        i = j
    return ranks

def normalized_raw(rows, size):
    # Scale-invariant optical features. Gap dimensions are normalized by pt size.
    feats = {"q25": [], "median": [], "q10": [], "overlap": [], "kern": []}
    for r in rows:
        feats["q25"].append(mean2(r, "q25_gap_thr1", "q25_gap_thr2") / size)
        feats["median"].append(mean2(r, "median_gap_thr1", "median_gap_thr2") / size)
        feats["q10"].append(mean2(r, "q10_gap_thr1", "q10_gap_thr2") / size)
        feats["overlap"].append(
            mean2(r, "overlap_rows_thr1", "overlap_rows_thr2") / size
        )
        # Near-zero native kerning is treated as safer to perturb than a strongly
        # designed pair. Negative absolute value means closer to zero ranks higher.
        feats["kern"].append(-abs(float(r["kern_px"])) / size)

    ranks = {name: percentile_ranks(vals) for name, vals in feats.items()}
    raw = []
    for i in range(len(rows)):
        raw.append(sum(WEIGHTS[name] * ranks[name][i] for name in WEIGHTS))
    return raw

def legacy_bitter16_pairs(path: Path):
    text = path.read_text(encoding="utf-8")
    m = re.search(r"ELIGIBLE_PAIRS\s*=\s*(\[[\s\S]*?\])\s*\npacked\s*=", text)
    if not m:
        raise SystemExit("Cannot locate ELIGIBLE_PAIRS in CPHUN-119 patch")
    pairs = ast.literal_eval(m.group(1))
    if len(pairs) != 655 or len(set(pairs)) != 655:
        raise SystemExit(f"Expected 655 legacy Bitter16 pairs, got {len(pairs)}")
    return set(pairs)

def map_group(indices, raw, lo, hi):
    # Rank within a legacy side of the 60 boundary.
    ordered = sorted(indices, key=lambda i: (raw[i], i))
    out = {}
    n = len(ordered)
    for rank, idx in enumerate(ordered):
        frac = rank / max(1, n - 1)
        out[idx] = int(round(lo + frac * (hi - lo)))
    return out

def clamp(v, lo=0, hi=100):
    return max(lo, min(hi, int(round(v))))

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--metrics-dir", type=Path, required=True)
    ap.add_argument("--legacy-patch", type=Path,
                    default=Path("tools/cphun119_fixedpoint_pair_tuning_patch.py"))
    ap.add_argument("--csv-out", type=Path, required=True)
    ap.add_argument("--header-out", type=Path, required=True)
    args = ap.parse_args()

    rows_by_size = {}
    raw_by_size = {}
    for size in SIZES:
        path = args.metrics_dir / f"Bitter{size}_letterpair_optical_gaps.csv"
        rows = read_rows(path)
        if len(rows) != 1225:
            raise SystemExit(f"{path}: expected 1225 rows, got {len(rows)}")
        rows_by_size[size] = rows
        raw_by_size[size] = normalized_raw(rows, size)

    pairs = [r["pair"] for r in rows_by_size[16]]
    for size in SIZES:
        if [r["pair"] for r in rows_by_size[size]] != pairs:
            raise SystemExit(f"Pair order mismatch at {size} pt")

    legacy = legacy_bitter16_pairs(args.legacy_patch)
    eligible = [i for i, p in enumerate(pairs) if p in legacy]
    ineligible = [i for i, p in enumerate(pairs) if p not in legacy]
    if len(eligible) != 655:
        raise SystemExit(f"Legacy calibration mismatch: {len(eligible)} eligible")

    # 16 pt calibration:
    # - legacy ineligible remain strictly below 60
    # - legacy eligible are at least 60
    # - raw optical safety ranks within each side give useful 50..75 testing spread
    score16 = [0] * len(pairs)
    for idx, score in map_group(ineligible, raw_by_size[16], 35, 59).items():
        score16[idx] = score
    for idx, score in map_group(eligible, raw_by_size[16], 60, 85).items():
        score16[idx] = score

    scores = {16: score16}
    for size in (12, 14, 18):
        vals = []
        # Optical movement relative to the same pair at 16 pt.
        # The explicit size term accounts for the perceptual strength of a real
        # emitted +1 px: slightly stricter below 16 pt, slightly looser above.
        size_adjust = 8.0 * (size / 16.0 - 1.0)
        for i in range(len(pairs)):
            optical_delta = 28.0 * (raw_by_size[size][i] - raw_by_size[16][i])
            vals.append(clamp(score16[i] + optical_delta + size_adjust))
        scores[size] = vals

    # Hard geometry guardrail only for clearly overlapping dark-ink tails.
    # This avoids allowing an extreme pair at the low 50 test threshold.
    for size in SIZES:
        rows = rows_by_size[size]
        for i, r in enumerate(rows):
            q10_dark = float(r["q10_gap_thr1"])
            q25_dark = float(r["q25_gap_thr1"])
            if q10_dark < 0 and q25_dark <= 1:
                scores[size][i] = min(scores[size][i], 49)

    # Verify exact legacy boundary at 16 pt / threshold 60.
    selected16 = {pairs[i] for i, s in enumerate(scores[16]) if s >= 60}
    if selected16 != legacy:
        missing = sorted(legacy - selected16)[:10]
        extra = sorted(selected16 - legacy)[:10]
        raise SystemExit(
            f"16pt/60 calibration failed: selected={len(selected16)} "
            f"missing={missing} extra={extra}"
        )

    args.csv_out.parent.mkdir(parents=True, exist_ok=True)
    with args.csv_out.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["pair", "score12", "score14", "score16", "score18"])
        for i, pair in enumerate(pairs):
            w.writerow([pair, scores[12][i], scores[14][i], scores[16][i], scores[18][i]])

    packed = []
    for i, pair in enumerate(pairs):
        key = (ord(pair[0]) << 16) | ord(pair[1])
        packed.append((key, scores[12][i], scores[14][i], scores[16][i], scores[18][i], pair))
    packed.sort(key=lambda x: x[0])

    lines = []
    for key, s12, s14, s16, s18, pair in packed:
        lines.append(
            f"    {{0x{key:08X}u, {s12}, {s14}, {s16}, {s18}}},  // {pair}"
        )

    header = f'''#pragma once
#include <cstddef>
#include <cstdint>

namespace BitterSpacingScores {{

struct PairScore {{
  uint32_t key;
  uint8_t score12;
  uint8_t score14;
  uint8_t score16;
  uint8_t score18;
}};

constexpr PairScore PAIRS[] = {{
{chr(10).join(lines)}
}};

static_assert(sizeof(PAIRS) / sizeof(PAIRS[0]) == 1225,
              "Bitter score table must contain 1225 ordered pairs");

inline uint8_t scoreForPair(const uint32_t left, const uint32_t right,
                            const uint8_t pointSize) {{
  if (left > 0xFFFFu || right > 0xFFFFu) return 0;
  const uint32_t key = (left << 16) | right;
  size_t lo = 0;
  size_t hi = sizeof(PAIRS) / sizeof(PAIRS[0]);
  while (lo < hi) {{
    const size_t mid = lo + (hi - lo) / 2;
    if (PAIRS[mid].key < key)
      lo = mid + 1;
    else
      hi = mid;
  }}
  if (lo >= sizeof(PAIRS) / sizeof(PAIRS[0]) || PAIRS[lo].key != key) return 0;
  switch (pointSize) {{
    case 12: return PAIRS[lo].score12;
    case 14: return PAIRS[lo].score14;
    case 18: return PAIRS[lo].score18;
    case 16:
    default: return PAIRS[lo].score16;
  }}
}}

}}  // namespace BitterSpacingScores
'''
    args.header_out.parent.mkdir(parents=True, exist_ok=True)
    args.header_out.write_text(header, encoding="utf-8")

    print("Bitter normalized score counts:")
    for size in SIZES:
        counts = [sum(1 for s in scores[size] if s >= t) for t in THRESHOLDS]
        print(f"  {size} pt: " + ", ".join(
            f">={t}:{count}" for t, count in zip(THRESHOLDS, counts)
        ))

if __name__ == "__main__":
    main()
