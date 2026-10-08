#!/bin/sh
# CP-KOBO-031: NickelMenu cmd_output readable status; no device writes.
S=/mnt/onboard/.adds/crosspoint/logs/clara-bw-display-031.status
if [ ! -f "$S" ]; then echo 'MEG NINCS MERES'; exit 0; fi
case "$(cat "$S")" in
 DONE) echo 'KESZ - USB csatlakoztathato.' ;;
 RUNNING) echo 'FOLYAMATBAN - ne csatlakoztass USB-t.' ;;
 FAILED) echo 'HIBA - ellenorizd a naplot.' ;;
 *) echo 'ISMERETLEN ALLAPOT - ne csatlakoztass USB-t.' ;;
esac
