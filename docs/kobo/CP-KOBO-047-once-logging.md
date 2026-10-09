# CP-KOBO-047 — one-attempt init probe, durable logs (compile only)

Pinned FBInk: `886f25f13368859ad8a899b88d04c26e19cda32e`.

## Result and scope
`scripts/kobo_fbink_047_once_init_probe.c` and a CI-only compiler step were added. **This is NOT permission to run it on Kobo**, and no executable is published in the artifact.

Inherited CP-KOBO-046 checks:
- Requires `--explicit-init-risk-acknowledged`.
- Reads the Nickel model suffix, demands `395`.
- Opens `/dev/fb0` O_RDONLY | O_NONBLOCK for GET-only mode checks: dimensions 1072×1448, 32bpp, rotate 3, R/G/B/A bitfields, stride 4288.
- Candidate `fbink_init(FBFD_AUTO, &cfg)` opens framebuffer in a temporary O_RDONLY context internally; no explicit draw, clear, refresh, EPDC wakeup, or mmap call in the probe.

## Additional controls
- `cp-kobo-047.attempted` is opened with `O_CREAT | O_EXCL`; an existing marker prevents calling init a second time.
- `cp-kobo-047-init.txt` uses append-only open, write, `fsync` for preflight, init entry, init return, and completion.
- Marker created and synced **before** init. It is intentionally left in place after success or failure. Never automatically delete it.
- The program records no full Nickel version string.

## Known limitations and physical-test blockers
1. A log marker prevents re-entry only if the shared directory and file remain intact. It is not a cross-device safety mechanism, and creation of files on onboard storage itself can fail.
2. Current source assumes `/mnt/onboard/.adds/crosspoint/logs` already exists. A future safe launcher must check and create the log directory explicitly and detect writable storage *before* init.
3. `fsync` only improves log durability; it cannot recover a stuck graphics controller or Nickel. A full display-owner and reboot/recovery procedure must be validated separately.
4. Completion status is a log line, not a live on-device NickelMenu status. A future physical package should separate the launch script from the status check and contain no boot hooks.
5. The complete transitive `fbink_init` side-effect review remains open; O_RDONLY is a risk reduction rather than proof of safety.
6. Do not upload the compiled binary to the Kobo yet. CI artifact must contain text-only evidence files.

## Next phase
Review CI compile evidence, review any remaining helper side effects and independent recovery requirements, then decide explicitly whether to package a **manual-only** test. Keep public X4 and X4 Classic firmware and preexisting KOReader/NickelMenu unchanged.
