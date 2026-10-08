#!/bin/sh
# CP-KOBO-029: read-only display inventory with safer, fresh logging.
# Writes diagnostic TXT only; never invokes FBInk, stops Nickel, or writes framebuffer.
set -u
DIR=/mnt/onboard/.adds/crosspoint
OUT="$DIR/logs"
mkdir -p "$OUT" || exit 2
LOG="$OUT/clara-bw-display-inventory-029.txt"
TMP="$OUT/.clara-bw-display-inventory-029.tmp"
# A distinct new output name avoids touching the corrupt CP-KOBO-028 log.
: > "$TMP" || exit 3
{
  printf 'CP-KOBO-029 START\n'
  printf 'uname: '; uname -a 2>&1
  printf 'FBInk binaries:\n'
  for f in /usr/bin/fbink /bin/fbink /usr/local/bin/fbink /mnt/onboard/.adds/fbink/fbink; do
    if [ -e "$f" ]; then ls -l "$f"; else printf 'absent: %s\n' "$f"; fi
  done
  if command -v fbink >/dev/null 2>&1; then
    printf 'fbink PATH: %s\n' "$(command -v fbink)"
  else
    printf 'fbink PATH: not found\n'
  fi
  printf 'Framebuffers:\n'
  for fb in /sys/class/graphics/fb[0-9]*; do
    [ -d "$fb" ] || continue
    printf 'framebuffer=%s\n' "$fb"
    for item in name virtual_size bits_per_pixel stride; do
      [ -r "$fb/$item" ] || continue
      printf '%s=' "$item"
      # Ensure sysfs binary/empty files cannot corrupt the text report.
      tr -d '\000' < "$fb/$item" | head -c 100
      printf '\n'
    done
  done
  printf 'Device nodes:\n'
  for node in /dev/fb0 /dev/fb1 /dev/hwtcon /dev/ntx_io /dev/ion; do
    if [ -e "$node" ]; then ls -l "$node"; else printf 'absent: %s\n' "$node"; fi
  done
  printf 'CP-KOBO-029 FINISHED (read-only)\n'
} >> "$TMP" 2>&1
rc=$?
if [ "$rc" -ne 0 ]; then printf 'ERROR report rc=%s\n' "$rc" >> "$TMP"; fi
# Rename only after writing the full report.
mv -f "$TMP" "$LOG" || exit 4
# sync where available, to reduce risk of USB reattachment before writeback.
if command -v sync >/dev/null 2>&1; then sync; fi
exit "$rc"
