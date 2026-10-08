#!/bin/sh
# CP-KOBO-024: opt-in, read-only four-corner touch capture.
set -eu
DIR=/mnt/onboard/.adds/crosspoint
BIN="$DIR/clara-bw-touch-corners-armhf"
LOG_DIR="$DIR/logs"
mkdir -p "$LOG_DIR"
LOG="$LOG_DIR/clara-bw-touch-corners.txt"
if [ ! -x "$BIN" ]; then
  printf 'ERROR missing or nonexecutable %s\n' "$BIN" > "$LOG"
  exit 3
fi
printf 'CP-KOBO-024 started. Tap TOP_LEFT, TOP_RIGHT, BOTTOM_LEFT, BOTTOM_RIGHT, once each.\n' > "$LOG"
# The ARM program has a 25-second per-corner timeout. An external timeout
# provides an additional upper bound on devices where it is available.
if command -v timeout >/dev/null 2>&1; then
  timeout 110 "$BIN" /dev/input/event1 >> "$LOG" 2>&1 || {
    code=$?
    printf 'exit=%s\n' "$code" >> "$LOG"
    exit "$code"
  }
else
  "$BIN" /dev/input/event1 >> "$LOG" 2>&1 || {
    code=$?
    printf 'exit=%s\n' "$code" >> "$LOG"
    exit "$code"
  }
fi
