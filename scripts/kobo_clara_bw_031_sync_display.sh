#!/bin/sh
# CP-KOBO-031 synchronous NickelMenu diagnostic. Read-only hardware inventory.
# cmd_output waits for this script and shows its stdout only after completion.
set -u
BASE=/mnt/onboard/.adds/crosspoint
DIR="$BASE/logs"
mkdir -p "$DIR" || { echo 'HIBA: naplomappa nem hozhato letre'; exit 2; }
LOG="$DIR/clara-bw-display-031.txt"
STATUS="$DIR/clara-bw-display-031.status"
TMP="$DIR/.clara-bw-display-031.tmp"
printf 'RUNNING\n' > "$STATUS" || { echo 'HIBA: allapotfajl'; exit 3; }
{
 echo 'CP-KOBO-031 START'
 echo "kernel: $(uname -r) arch: $(uname -m)"
 echo 'FBInk search:'
 for f in /usr/bin/fbink /bin/fbink /usr/local/bin/fbink /mnt/onboard/.adds/fbink/fbink; do
  [ ! -e "$f" ] || ls -l "$f"
 done
 if command -v fbink >/dev/null 2>&1; then
  echo "FBInk path: $(command -v fbink)"
 else
  echo 'FBInk path: not found'
 fi
 for fb in /sys/class/graphics/fb[0-9]*; do
  [ -d "$fb" ] || continue
  echo "framebuffer: $fb"
  for key in name virtual_size bits_per_pixel stride; do
   [ -r "$fb/$key" ] || continue
   printf '%s: ' "$key"
   tr -d '\000' < "$fb/$key" | head -c 90
   printf '\n'
  done
 done
 for node in /dev/fb0 /dev/hwtcon /dev/ntx_io; do
  [ ! -e "$node" ] || ls -l "$node"
 done
 echo 'CP-KOBO-031 FINISHED'
} > "$TMP" 2>&1
rc=$?
if [ "$rc" -ne 0 ] || ! grep -q '^CP-KOBO-031 FINISHED$' "$TMP"; then
 printf 'FAILED\n' > "$STATUS"
 echo 'HIBA: diagnosztika'
 exit 4
fi
mv -f "$TMP" "$LOG" || { printf 'FAILED\n' > "$STATUS"; echo 'HIBA: naplomentes'; exit 5; }
# sync before writing final DONE flag. The user must allow Kobo to fully
# finish this operation before USB export.
sync
printf 'DONE\n' > "$STATUS" || { echo 'HIBA: allapotmentes'; exit 6; }
sync
echo 'DIAGNOSZTIKA KESZ'
echo 'USB csatlakoztathato.'
exit 0
