#!/bin/sh
S=/mnt/onboard/.adds/crosspoint/logs/cp-kobo-042.status
[ -r "$S" ] || { echo 'NINCS TESZT'; exit 0; }
case "$(cat "$S")" in
DONE) echo 'KESZ / USB OK';;
RUNNING) echo 'FOLYAMATBAN';;
FAILED) echo 'SIKERTELEN';;
*) echo 'ISMERETLEN';;
esac
