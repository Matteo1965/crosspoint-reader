#!/bin/sh
# CP-KOBO-022: one-shot, read-only Clara BW probe.
# Invoke from NickelMenu; never stop/restart Nickel or grab input devices.
set -eu
APP_DIR=/mnt/onboard/.adds/crosspoint
PROBE="$APP_DIR/clara-bw-probe-static-armhf"
LOG_DIR="$APP_DIR/logs"
if [ ! -x "$PROBE" ]; then
  exit 3
fi
mkdir -p "$LOG_DIR"
# No root, no firmware edits, no framebuffer writes. Timeout guards hangs.
# Output is captured in an ordinary user-visible file.
if command -v timeout >/dev/null 2>&1; then
  timeout 15 "$PROBE" > "$LOG_DIR/clara-bw-hardware.txt" 2>&1
else
  "$PROBE" > "$LOG_DIR/clara-bw-hardware.txt" 2>&1
fi
