# CP-KOBO-048 — First manual-only FBInk init diagnostic candidate

FBInk pinned commit `886f25f13368859ad8a899b88d04c26e19cda32e`.

## What this package does
- Manual NickelMenu launch, not an autostart or firmware updater.
- Static ARM hard-float binary `fbink-init-048`; shell scripts `launch-048.sh`, `status-048.sh`.
- Device model must be 395, and framebuffer must match CP-KOBO-039: 1072×1448, 32-bpp, rotation 3, 8-bit offsets R0 G8 B16 A24, line length 4288.
- Preflight uses O_RDONLY / GET-only ioctl. FBInk initialization calls `fbink_init(FBFD_AUTO, &cfg)` with a zero-initialized config; automatic fd is opened O_RDONLY and closed inside library.
- Explicit argument gate, O_EXCL persisted attempt marker, fsync on marker, enclosing directory fsync, and separate append-only durable log.
- Does not intentionally invoke screen drawing, clear, E Ink refresh, or EPDC wakeup.

## Dangers / caveats
- This is an experimental *hardware init*, not harmless like CP-KOBO-039/042. O_RDONLY reduces requested privileges but does not prove that driver open / ioctl / library init cannot change controller or Nickel state.
- The launcher's timeout in NickelMenu cannot undo kernel display effects. **Only run if prepared to reboot manually if Nickel becomes unresponsive.**
- Not yet physically validated; a successful GitHub build proves compilation only.
- First run creates `.adds/crosspoint/logs/cp-kobo-048.attempted`; do not remove to retry. A preflight error will not create that marker.
- Shell stdout/stderr is captured in `cp-kobo-048-output.txt`; durable checkpoint log is `cp-kobo-048-init.txt`; marker text is `cp-kobo-048.attempted`.
- No full version/serial is written to logs. No public X4/X4 Classic firmware or Nickel/KOReader configs should be modified or overwritten.

## On-device installation after CI success
1. Extract the GitHub Actions artifact, then extract the enclosed ZIP if present.
2. Copy `crosspoint/fbink-init-048`, `crosspoint/launch-048.sh`, `crosspoint/status-048.sh` into `KOBOeReader/.adds/crosspoint/`.
3. Add the two separate lines from `nickelmenu-entry.txt` as a **new** NickelMenu configuration under `.adds/nm/`.
4. Safely eject USB. Only then manually select **Clara BW FBInk Init 048** once.
5. Check Nickel main UI navigation, touch, and KOReader launch. If any issue, do not rerun.
6. Reconnect USB only when Nickel is functional; upload both logs and marker.

## Recovery
No destructive or automatic recovery mechanism is implemented. If device UI hangs, stop testing and use the normal hardware reboot/power-button procedure. The project explicitly does not claim that the process, NickelMenu timeout or O_RDONLY access guarantees recovery.
