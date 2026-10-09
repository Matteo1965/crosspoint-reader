#!/bin/sh
# CP-KOBO-035: FBInk --help only. Verified CLI path exits before fbink_open().
set -u
BASE=/mnt/onboard/.adds/crosspoint
LOGDIR="$BASE/logs"
BIN="$BASE/fbink-035"
mkdir -p "$LOGDIR" || { echo 'HIBA: log directory'; exit 2; }
STATUS="$LOGDIR/cp-kobo-035.status"
LOG="$LOGDIR/cp-kobo-035-help.txt"
TMP="$LOGDIR/.cp-kobo-035-help.tmp"
printf 'RUNNING\n' > "$STATUS" || exit 3
if [ ! -x "$BIN" ]; then
  printf 'FAILED\n' > "$STATUS"
  sync
  echo 'HIBA: FBInk binary missing or not executable'
  exit 4
fi
# Only --help: no fbink_open, no framebuffer access or E Ink update.
"$BIN" --help > "$TMP" 2>&1
rc=$?
if [ "$rc" -ne 0 ]; then
  printf 'FAILED\n' > "$STATUS"
  mv -f "$TMP" "$LOG"
  sync
  echo "HIBA: FBInk --help rc=$rc"
  exit 5
fi
if ! grep -q 'FBInk' "$TMP"; then
  printf 'FAILED\n' > "$STATUS"
  mv -f "$TMP" "$LOG"
  sync
  echo 'HIBA: unexpected FBInk help output'
  exit 6
fi
mv -f "$TMP" "$LOG" || { printf 'FAILED\n' > "$STATUS"; sync; exit 7; }
sync
printf 'DONE\n' > "$STATUS"
sync
echo 'FBINK HELP OK - DIAGNOSZTIKA KESZ'
echo 'USB csatlakoztathato.'
exit 0
