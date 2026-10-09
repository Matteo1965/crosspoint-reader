#!/bin/sh
L=/mnt/onboard/.adds/crosspoint/logs
F="$L/cp-kobo-051-state.txt"
if [ ! -r "$F" ]; then
  echo '051: NINCS ALLAPOTNAPLO'
  exit 0
fi
if grep -qx 'state=INIT_RETURNED' "$F"; then
  echo '051 INIT RETURNED; Keszulek ellenorzese meg szukseges'
elif grep -qx 'state=INIT_FAILED' "$F"; then
  echo '051 INIT FAILED; nincs ismetles'
elif grep -qx 'state=ATTEMPTED' "$F"; then
  echo '051 UNKNOWN/INTERRUPTED vagy eppen fut; nincs ismetles'
elif grep -qx 'state=PREFLIGHT_FAILED' "$F"; then
  echo '051 PREFLIGHT FAILED'
else
  echo '051 allapot ismeretlen'
fi
[ -e "$L/cp-kobo-051.attempted" ] && echo 'attempt marker: YES'
