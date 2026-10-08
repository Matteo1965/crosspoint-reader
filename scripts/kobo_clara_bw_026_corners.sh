#!/bin/sh
# CP-KOBO-026 calibrated BTN_TOUCH release. Read-only, no EVIOCGRAB.
set -eu
DIR=/mnt/onboard/.adds/crosspoint
BIN="$DIR/clara-bw-touch-corners-026-armhf"
LOG="$DIR/logs/clara-bw-touch-corners-026.txt"
mkdir -p "$DIR/logs"
if [ ! -x "$BIN" ]; then
  printf 'ERROR missing or nonexecutable %s\n' "$BIN" > "$LOG"
  exit 3
fi
printf 'CP-KOBO-026 started; tap TOP_LEFT, TOP_RIGHT, BOTTOM_LEFT, BOTTOM_RIGHT.\n' > "$LOG"
if command -v timeout >/dev/null 2>&1; then
  timeout 110 "$BIN" /dev/input/event1 >> "$LOG" 2>&1 || {
    rc=$?; printf 'exit=%s\n' "$rc" >> "$LOG"; exit "$rc";
  }
else
  "$BIN" /dev/input/event1 >> "$LOG" 2>&1 || {
    rc=$?; printf 'exit=%s\n' "$rc" >> "$LOG"; exit "$rc";
  }
fi
