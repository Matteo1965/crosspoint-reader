#!/bin/sh
ST=/mnt/onboard/.adds/crosspoint/logs/cp-kobo-039.status
[ -f "$ST" ] || { echo 'NINCS MERES'; exit 0; }
case "$(cat "$ST")" in
 DONE) echo 'KESZ / USB OK' ;;
 RUNNING) echo 'FOLYAMATBAN' ;;
 FAILED) echo 'HIBA' ;;
 *) echo 'ISMERETLEN' ;;
esac
