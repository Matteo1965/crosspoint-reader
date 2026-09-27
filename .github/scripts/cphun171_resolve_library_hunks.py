#!/usr/bin/env python3
"""Resolve simple, uniquely anchored upstream Library View hunks without
overwriting Hungarian Edition changes. Refuse ambiguous or missing anchors.
Runs AFTER git apply --reject has applied all nonconflicting hunks.
"""
from __future__ import annotations
from pathlib import Path
import re
import sys

ROOTS = (Path("lib"), Path("src"))
HUNK = re.compile(r"^@@ -\d+(?:,\d+)? \+\d+(?:,\d+)? @@")

def hunks(text):
    block = []
    started = False
    for line in text.splitlines(keepends=True):
        if HUNK.match(line):
            if block:
                yield block
            block = []
            started = True
        elif started and line[:1] in (" ", "-", "+"):
            block.append(line)
        elif not block and line[:1] in (" ", "-", "+"):
            # Only called for .rej; discard header until first @@.
            continue
    if block:
        yield block

def edits(hunk):
    """Each edit is an old/new pair with immediately adjacent context."""
    before = []
    pending_old, pending_new = [], []
    for line in hunk + ["\u0000"]:
        tag = line[:1]
        value = line[1:] if tag != "\u0000" else ""
        if tag == " " or tag == "\u0000":
            if pending_old or pending_new:
                yield (pending_old, pending_new, before[-3:], value if tag == " " else None)
                pending_old, pending_new = [], []
            if tag == " ":
                before.append(value)
        elif tag == "-":
            pending_old.append(value)
        elif tag == "+":
            pending_new.append(value)

def resolve(path):
    target = Path(str(path)[:-4])
    current = target.read_text(encoding="utf-8").splitlines(keepends=True)
    lines = path.read_text(encoding="utf-8")
    failures = []
    applied = 0
    for h_index, hunk in enumerate(hunks(lines), 1):
        for e_index, (old, new, before, after) in enumerate(edits(hunk), 1):
            if old == new:
                continue
            # First try exact old blocks, then uniquely matching old lines
            # ignoring whitespace. Never guess between multiple candidates.
            matches = []
            if old:
                n = len(old)
                matches = [i for i in range(len(current) - n + 1)
                           if current[i:i+n] == old]
                if not matches:
                    matches = [i for i in range(len(current) - n + 1)
                               if [x.strip() for x in current[i:i+n]] ==
                                  [x.strip() for x in old]]
            else:
                # Pure addition: anchor on an adjacent unchanged context line.
                if before:
                    anchor = before[-1]
                    matches = [i+1 for i, x in enumerate(current) if x.strip() == anchor.strip()]
                elif after:
                    matches = [i for i, x in enumerate(current) if x.strip() == after.strip()]
            if len(matches) != 1:
                # If already applied, don't duplicate the insertion.
                if new and len(new) <= len(current) and any(
                    current[i:i+len(new)] == new for i in range(len(current)-len(new)+1)
                ):
                    print(f"already applied: {target} hunk={h_index} edit={e_index}")
                    continue
                failures.append((h_index, e_index, len(matches),
                                 "".join(old).strip()[:150],
                                 "".join(new).strip()[:150]))
                continue
            at = matches[0]
            current[at:at+len(old)] = new
            applied += 1
    if failures:
        print(f"NEEDS MANUAL PORT {target}: {len(failures)} unresolved edit blocks")
        for index, edit, count, old, new in failures:
            print(f"  hunk={index} edit={edit} candidates={count} old={old!r} new={new!r}")
        # Only persist independently verified changes. Keep .rej for diagnosis.
    else:
        path.unlink()
    if applied:
        target.write_text("".join(current), encoding="utf-8")
    return applied, len(failures)

total_applied, total_failed = 0, 0
rejects = sorted(p for base in ROOTS for p in base.rglob("*.rej"))
for reject in rejects:
    a, f = resolve(reject)
    total_applied += a
    total_failed += f
print(f"Library View merge: {total_applied} exact edits applied, {total_failed} ambiguous edits left across {len(rejects)} rejected files.")
sys.exit(0 if total_failed == 0 else 1)
