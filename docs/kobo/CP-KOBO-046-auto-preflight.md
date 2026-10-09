# CP-KOBO-046 — Guarded FBFD_AUTO initialization candidate

Pinned FBInk rev `886f25f13368859ad8a899b88d04c26e19cda32e`.

## Scope

This phase creates **compile-only** source `scripts/kobo_fbink_046_auto_init_probe.c`. GitHub CI links it against ARM static FBInk, checks architecture and absence of an ELF interpreter, and publishes **only evidence reports, not the executable**. No device-side testing, framebuffer modifications or refresh.

## Preflight guards

- Requires explicit CLI option `--explicit-init-risk-acknowledged`. This alone is NOT a safety guarantee.
- Reads `/mnt/onboard/.kobo/version`, validates 3-digit model suffix `395`. Does not print the full tag.
- Opens `/dev/fb0` temporarily with `O_RDONLY | O_NONBLOCK | O_CLOEXEC`, makes only `FBIOGET_VSCREENINFO` and `FBIOGET_FSCREENINFO` ioctl calls. Closes descriptor.
- Verifies resolution 1072×1448, 32bpp, native rotation 3, 8-bit color offsets 0/8/16/24, and line length 4288 against CP-KOBO-039.
- Flushes pre-init logs before calling **`fbink_init(FBFD_AUTO, &cfg)`**, with zeroed config. Automatic fd path independently opens framebuffer read-only and closes it afterward.
- Only if init succeeds, reads `FBInkState` for model, MediaTek flag, bpp, pixel-format enum, native rotation, dimensions.
- No print, clear, wakeup, explicit mmap, or refresh API is requested.

## Remaining gates / known limitations

1. The complete transitive FBInk init call graph and kernel-driver effects remain incompletely audited; physical testing is not authorized solely because the descriptor requests read-only access.
2. The current program logs to stdout/stderr but has **not yet implemented** an on-device run-once lock, durable marker, NickelMenu script, timeout supervision, or verified rollback path. Do not distribute this source-built ELF to the Kobo.
3. A timeout cannot undo a kernel display state change. Nickel and KOReader post-init operation must be verified when testing is approved.
4. `fbink_wakeup_epdc()` on MTK writes `fiti_power 1` to `/proc/hwtcon/cmd`; it is not called by this probe.
5. Hardware measurements may differ after a future firmware update or device rotation; mismatch causes the candidate to abort before FBInk init.

## Next

Check CI results for code correctness, then resolve init ownership/recovery and single-attempt logging before producing any device artifact. Do not modify public X4/X4 Classic release.
