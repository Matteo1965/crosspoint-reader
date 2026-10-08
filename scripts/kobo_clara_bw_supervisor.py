#!/usr/bin/env python3
"""CP-KOBO-011: supervised, opt-in CrossPoint launcher prototype.

No auto-start, no firmware changes and no Nickel process manipulation.
The supervisor runs separately from the child and exits after the child
exits or the configured safety deadline expires. A future Kobo-specific
adapter must handle display ownership / Nickel restoration.
"""
import argparse
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

def supervise(command, seconds, grace):
    start = time.monotonic()
    child = subprocess.Popen(command, start_new_session=True)
    timed_out = False
    try:
        child.wait(timeout=seconds)
    except subprocess.TimeoutExpired:
        timed_out = True
        # Terminate child's process group so descendants cannot linger.
        os.killpg(child.pid, signal.SIGTERM)
        try:
            child.wait(timeout=grace)
        except subprocess.TimeoutExpired:
            os.killpg(child.pid, signal.SIGKILL)
            child.wait()
    return {"mode": "timeout" if timed_out else "normal_exit",
            "exit_code": child.returncode,
            "duration_seconds": round(time.monotonic()-start, 3),
            "nickel_restored": False,
            "note": "No automatic Nickel restoration implemented or claimed"}

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--limit", type=float, default=120.0)
    p.add_argument("--grace", type=float, default=2.0)
    p.add_argument("--output", type=Path)
    p.add_argument("--execute", action="store_true", help="Explicitly enable child execution")
    p.add_argument("command", nargs=argparse.REMAINDER, help="Command after --")
    args = p.parse_args()
    if not (0 < args.limit <= 120 and 0 < args.grace <= 10):
        p.error("limit must be (0,120] and grace must be (0,10]")
    command = args.command[1:] if args.command[:1] == ["--"] else args.command
    if not command: p.error("A child program must be specified")
    if not args.execute: p.error("Refusing to launch without --execute")
    report = supervise(command, args.limit, args.grace)
    text = json.dumps(report, indent=2, ensure_ascii=False) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text, encoding="utf-8")
    print(text, end="")
    return 0 if report["mode"] == "normal_exit" and report["exit_code"] == 0 else 1

if __name__ == "__main__":
    sys.exit(main())
