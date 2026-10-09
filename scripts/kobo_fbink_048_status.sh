#!/bin/sh
L=/mnt/onboard/.adds/crosspoint/logs
if [ -f "$L/cp-kobo-048-init.txt" ]; then
  echo 'CP-KOBO-048:'
  tail -n 8 "$L/cp-kobo-048-init.txt"
else
  echo 'CP-KOBO-048: no init log'
fi
[ -e "$L/cp-kobo-048.attempted" ] && echo 'Marker: ATTEMPTED / do not repeat'
