#!/bin/sh
# CP-KOBO-025 diagnostic, never stops Nickel or grabs input.
set -eu
DIR=/mnt/onboard/.adds/crosspoint
LOG="$DIR/logs/clara-bw-raw-events.txt"
mkdir -p "$DIR/logs"
BIN="$DIR/clara-bw-raw-evdev-armhf"
if [ ! -x "$BIN" ]; then
  printf 'ERROR binary missing or not executable: %s\n' "$BIN" > "$LOG"
  exit 3
fi
printf 'CP-KOBO-025 started\n' > "$LOG"
if command -v timeout >/dev/null 2>&1; then
  timeout 35 "$BIN" /dev/input/event1 >> "$LOG" 2>&1 || {
    rc=$?; printf 'exit=%s\n' "$rc" >> "$LOG"; exit "$rc";
  }
else
  "$BIN" /dev/input/event1 >> "$LOG" 2>&1 || {
    rc=$?; printf 'exit=%s\n' "$rc" >> "$LOG"; exit "$rc";
  }
fi
