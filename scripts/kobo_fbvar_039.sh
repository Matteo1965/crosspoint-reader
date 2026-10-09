#!/bin/sh
# CP-KOBO-039: run only an O_RDONLY GET-ioctl probe, never FBInk.
set -u
BASE=/mnt/onboard/.adds/crosspoint
DIR="$BASE/logs"
mkdir -p "$DIR" || { echo 'HIBA: log mappa'; exit 2; }
ST="$DIR/cp-kobo-039.status"
LOG="$DIR/cp-kobo-039-framebuffer.txt"
printf 'RUNNING\n' > "$ST" || exit 3
if [ ! -f "$BASE/fbvar-039" ]; then
  printf 'FAILED\n' > "$ST"
  sync
  echo 'HIBA: fbvar-039 hianyzik'
  exit 4
fi
# /bin/sh may invoke ELF without an executable-bit requirement via direct execution only
chmod +x "$BASE/fbvar-039" || { printf 'FAILED\n' > "$ST"; sync; echo 'HIBA: chmod'; exit 5; }
"$BASE/fbvar-039" > "$LOG" 2>&1
rc=$?
if [ "$rc" -eq 0 ] && grep -qx 'CP-KOBO-039 FINISHED' "$LOG"; then
  printf 'DONE\n' > "$ST"
  sync
  echo 'CP-KOBO-039 KESZ'
  echo 'Csak olvasasi teszt. USB OK.'
else
  printf 'FAILED\n' > "$ST"
  sync
  echo "CP-KOBO-039 HIBA rc=$rc"
fi
exit "$rc"
