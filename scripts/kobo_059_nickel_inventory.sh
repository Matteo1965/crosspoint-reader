#!/bin/sh
# CP-KOBO-059: read-only Nickel/display ownership inventory.
# No process signals, stop/start, framebuffer writes, or evdev grabs.
set -u
B=/mnt/onboard/.adds/crosspoint
L="$B/logs"
mkdir -p "$L" || exit 2
M="$L/cp-kobo-059.attempted"
O="$L/cp-kobo-059-inventory.txt"
[ ! -e "$M" ] || exit 3
(umask 077; : > "$M") || exit 4
{
  printf 'CP-KOBO-059 READ ONLY\n'
  date 2>/dev/null || :
  uname -a 2>/dev/null || :
  printf '\n[fb0]\n'
  for p in /sys/class/graphics/fb0/name /sys/class/graphics/fb0/virtual_size /sys/class/graphics/fb0/bits_per_pixel; do
    printf '%s: ' "$p"; cat "$p" 2>/dev/null || echo unavailable
  done
  printf '\n[processes of interest]\n'
  for d in /proc/[0-9]*; do
    [ -d "$d" ] || continue
    pid=${d##*/}
    [ -r "$d/comm" ] || continue
    IFS= read -r comm < "$d/comm" || continue
    case "$comm" in
      nickel|Nickel|nickelmenu|NickelMenu|fbink|koreader|reader.lua|lua|luajit|Qt*) ;;
      *) continue ;;
    esac
    printf '\nPID=%s COMM=%s\n' "$pid" "$comm"
    printf 'CMDLINE='
    tr '\000' ' ' < "$d/cmdline" 2>/dev/null || :
    printf '\nSTATE='
    sed -n '/^State:/p' "$d/status" 2>/dev/null || :
    printf 'PARENT='
    sed -n '/^PPid:/p' "$d/status" 2>/dev/null || :
    printf 'DISPLAY_FDS:\n'
    for f in "$d"/fd/*; do
      [ -L "$f" ] || continue
      target=$(readlink "$f" 2>/dev/null) || continue
      case "$target" in
        *'/dev/fb'*|*'/dev/graphics/'*|*'/dev/input/event'*|*'/dev/dri/'*|*'/dev/disp'*|*'/dev/mxc'*)
          printf '  %s -> %s\n' "${f##*/}" "$target" ;;
      esac
    done
  done
  printf '\n[device nodes]\n'
  ls -l /dev/fb0 /dev/input/event* 2>/dev/null || :
  printf '\nEND CP-KOBO-059\n'
} > "$O" 2>&1
rc=$?
sync
exit "$rc"
