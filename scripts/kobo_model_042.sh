#!/bin/sh
# CP-KOBO-042 read-only model-ID check. No framebuffer access.
set -u
BASE=/mnt/onboard/.adds/crosspoint
OUT="$BASE/logs"
mkdir -p "$OUT" || { echo 'HIBA: log mappa'; exit 2; }
STATUS="$OUT/cp-kobo-042.status"
LOG="$OUT/cp-kobo-042-model.txt"
printf 'RUNNING\n' > "$STATUS" || exit 3
(
 echo 'CP-KOBO-042 START'
 FILE=/mnt/onboard/.kobo/version
 if [ ! -r "$FILE" ]; then
   echo 'ERROR: Kobo version tag inaccessible'
   exit 4
 fi
 tag=$(cat "$FILE") || exit 5
 # Read only the last three characters; do not log firmware identifiers or serial data.
 code=$(printf '%s' "$tag" | tail -c 3)
 case "$code" in
   ''|*[!0-9]*) echo 'ERROR: invalid model suffix'; exit 6 ;;
 esac
 echo "model_code=$code"
 if [ "$code" = 395 ]; then
   echo 'clara_bw_tpv_match=YES'
 else
   echo 'clara_bw_tpv_match=NO'
 fi
 echo 'fbink_init=NOT_RUN'
 echo 'framebuffer=NOT_OPENED'
 echo 'CP-KOBO-042 FINISHED'
) > "$LOG" 2>&1
rc=$?
if [ "$rc" -eq 0 ] && grep -qx 'clara_bw_tpv_match=YES' "$LOG" && grep -qx 'CP-KOBO-042 FINISHED' "$LOG"; then
 echo DONE > "$STATUS"
 sync
 echo 'CP-KOBO-042 KESZ / 395 IGAZOLT'
 echo 'USB OK'
else
 echo FAILED > "$STATUS"
 sync
 echo 'CP-KOBO-042: modell ellenorzese sikertelen'
 echo 'Ne indits FBInk init-et'
fi
exit "$rc"
