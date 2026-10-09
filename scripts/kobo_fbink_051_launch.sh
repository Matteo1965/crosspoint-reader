#!/bin/sh
# CP-KOBO-051: manual NickelMenu launch only; no boot hooks.
set -u
BASE=/mnt/onboard/.adds/crosspoint
LOG="$BASE/logs"
mkdir -p "$LOG" || { echo '051 HIBA: logs mappa'; exit 2; }
if [ -e "$LOG/cp-kobo-051.attempted" ]; then
  echo '051 MAR FUTOTT: ujrainditas letiltva'
  exit 3
fi
if [ ! -x "$BASE/fbink-init-051" ]; then
  echo '051 HIBA: binaris hianyzik vagy nem futtathato'
  exit 4
fi
printf '%s\n' '051: FBInk init indul (nincs rajzolas/frissites)'
"$BASE/fbink-init-051" --explicit-init-risk-acknowledged > "$LOG/cp-kobo-051-output.txt" 2>&1
rc=$?
printf 'exit_code=%s\n' "$rc" >> "$LOG/cp-kobo-051-output.txt"
sync
if [ "$rc" -eq 0 ]; then
  echo '051: INIT RETURNED - ellenorizd Nickel + KOReader!'
else
  echo "051: ERROR rc=$rc - ne probald ujra"
fi
exit "$rc"
