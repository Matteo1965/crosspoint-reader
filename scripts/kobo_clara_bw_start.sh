#!/bin/sh
# CP-KOBO-012: NickelMenu-compatible *staging* launcher.
# No auto-start, Nickel termination or service changes.
# Not intended for use on-device until Kobo ARM executable and lifecycle
# restoration have been validated.
set -eu

APP_DIR=${CROSSPOINT_APP_DIR:-/mnt/onboard/.adds/crosspoint}
APP_BIN="$APP_DIR/crosspoint-kobo"
LOG_DIR="$APP_DIR/logs"
LIMIT=${CROSSPOINT_TEST_LIMIT:-120}

case "$LIMIT" in
  ''|*[!0-9]*) echo "Invalid test limit" >&2; exit 2 ;;
esac
if [ "$LIMIT" -lt 1 ] || [ "$LIMIT" -gt 120 ]; then
    echo "Test limit must be between 1 and 120 seconds" >&2
    exit 2
fi
if [ ! -x "$APP_BIN" ]; then
    echo "CrossPoint Kobo ARM binary missing; refusing to alter Nickel" >&2
    exit 3
fi
if [ "${CROSSPOINT_ENABLE_KOBO_LAUNCH:-0}" != "1" ]; then
    echo "Kobo launch disabled until lifecycle integration has been verified" >&2
    exit 4
fi
if ! command -v python3 >/dev/null 2>&1; then
    echo "Python 3 supervisor unavailable: launch refused" >&2
    exit 5
fi
if [ ! -f "$APP_DIR/supervisor.py" ]; then
    echo "Supervisor missing: launch refused" >&2
    exit 6
fi

mkdir -p "$LOG_DIR"
# Nickel remains untouched. We will not call KOReader's nickel.sh because
# that script assumes KOReader already stopped Nickel.
exec python3 "$APP_DIR/supervisor.py" --execute --limit "$LIMIT" \
    --output "$LOG_DIR/last-run.json" -- "$APP_BIN"
