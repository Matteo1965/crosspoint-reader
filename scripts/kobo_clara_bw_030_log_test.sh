#!/bin/sh
# CP-KOBO-030 isolated logging check, no FBInk and no framebuffer access.
set -u
D=/mnt/onboard/.adds/crosspoint
O="$D/logs"
mkdir -p "$O" || exit 2
# Distinct diagnostic names, preserve previous logs.
printf 'CP-KOBO-030 SHELL PRINTF OK\n' > "$O/cp030-a-shell.txt"
sh -c 'printf "CP-KOBO-030 CHILD SHELL OK\n"' > "$O/cp030-b-child.txt"
if [ -x "$D/cp030-arm-write" ]; then
 "$D/cp030-arm-write" "$O/cp030-c-arm.txt"
else
 printf 'CP-KOBO-030 ARM BINARY MISSING\n' > "$O/cp030-c-arm.txt"
fi
# Read back with od rather than reproducing the data through another write.
# Marker output is intentionally a separate, independent file.
{
 printf 'CP-KOBO-030 READBACK\n'
 for f in "$O"/cp030-[abc]-*.txt; do
   [ -f "$f" ] || continue
   printf '%s: ' "${f##*/}"
   wc -c < "$f"
   od -An -tx1 "$f" | head -n 2
 done
 printf 'CP-KOBO-030 DONE\n'
} > "$O/cp030-d-readback.txt"
sync
