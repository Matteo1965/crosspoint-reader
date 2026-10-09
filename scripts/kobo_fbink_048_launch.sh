#!/bin/sh
# CP-KOBO-048 - manual-only, never invoked on boot.
set -u
BASE=/mnt/onboard/.adds/crosspoint
LOG="$BASE/logs"
mkdir -p "$LOG" || { echo 'CP-KOBO-048: log directory unavailable'; exit 2; }
if [ ! -f "$BASE/fbink-init-048" ]; then
  echo 'CP-KOBO-048: missing executable'
  exit 3
fi
if [ -e "$LOG/cp-kobo-048.attempted" ]; then
  echo 'CP-KOBO-048: ALREADY ATTEMPTED. No second run.'
  exit 4
fi
chmod +x "$BASE/fbink-init-048" || exit 5
echo 'CP-KOBO-048: init test begins; NO DRAW/REFRESH requested'
"$BASE/fbink-init-048" --explicit-init-risk-acknowledged > "$LOG/cp-kobo-048-output.txt" 2>&1
rc=$?
printf 'exit_code=%s\n' "$rc" >> "$LOG/cp-kobo-048-output.txt"
sync
if [ "$rc" -eq 0 ]; then
  echo 'CP-KOBO-048: SUCCESS; verify Nickel and KOReader'
else
  echo "CP-KOBO-048: FAILED ($rc); STOP tests"
fi
echo 'USB OK after Nickel is responsive'
exit "$rc"
