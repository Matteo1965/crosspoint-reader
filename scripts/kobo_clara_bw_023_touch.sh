#!/bin/sh
# CP-KOBO-023 read-only event1 ABS axis query. Does not grab input.
set -eu
DIR=/mnt/onboard/.adds/crosspoint
BIN="$DIR/clara-bw-evdev-axes-armhf"
mkdir -p "$DIR/logs"
LOG="$DIR/logs/clara-bw-touch-axes.txt"
if [ ! -x "$BIN" ]; then
  printf 'ERROR: missing or nonexecutable: %s\n' "$BIN" > "$LOG"
  exit 3
fi
if command -v timeout >/dev/null 2>&1; then
  timeout 15 "$BIN" /dev/input/event1 > "$LOG" 2>&1 || {
    code=$?
    printf 'probe_exit=%s\n' "$code" >> "$LOG"
    exit "$code"
  }
else
  "$BIN" /dev/input/event1 > "$LOG" 2>&1 || {
    code=$?
    printf 'probe_exit=%s\n' "$code" >> "$LOG"
    exit "$code"
  }
fi
