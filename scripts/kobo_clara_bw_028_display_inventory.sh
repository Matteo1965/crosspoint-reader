#!/bin/sh
# CP-KOBO-028 read-only graphics capability inventory.
# Never execute FBInk drawing commands, stop Nickel, or open framebuffer for writing.
set -u
DIR=/mnt/onboard/.adds/crosspoint
mkdir -p "$DIR/logs" || exit 2
LOG="$DIR/logs/clara-bw-display-inventory.txt"
{
 echo 'CP-KOBO-028 display inventory started'
 echo 'uname:'
 uname -a 2>&1
 echo 'FBInk lookup:'
 for candidate in /usr/bin/fbink /bin/fbink /usr/local/bin/fbink /mnt/onboard/.adds/fbink/fbink; do
   if [ -e "$candidate" ]; then ls -l "$candidate"; else echo "absent: $candidate"; fi
 done
 if command -v fbink >/dev/null 2>&1; then
   echo "fbink resolved: $(command -v fbink)"
   # Do not call fbink itself: some versions initialize the display even with
   # informational flags.
 else
   echo 'fbink not found in PATH'
 fi
 echo 'Framebuffers:'
 for fb in /sys/class/graphics/fb[0-9]*; do
   [ -d "$fb" ] || continue
   echo "device=$fb"
   for item in name virtual_size bits_per_pixel stride modes; do
     if [ -r "$fb/$item" ]; then
       printf '%s=' "$item"
       head -c 200 "$fb/$item" 2>/dev/null
       echo
     fi
   done
 done
 echo 'Relevant device nodes:'
 for node in /dev/fb0 /dev/fb1 /dev/hwtcon /dev/ntx_io /dev/ion; do
   if [ -e "$node" ]; then ls -l "$node"; else echo "absent: $node"; fi
 done
 echo 'CP-KOBO-028 finished (read-only)'
} > "$LOG" 2>&1
