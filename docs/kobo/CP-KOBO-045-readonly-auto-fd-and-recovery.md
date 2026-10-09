# CP-KOBO-045 — FBInk automatic read-only descriptor and recovery gates

Upstream FBInk revision: `886f25f13368859ad8a899b88d04c26e19cda32e`.

## Key discovery
- `fbink.h:66` defines `FBFD_AUTO=-1`.
- `fbink.h:788` documents that `fbink_init(FBFD_AUTO, &cfg)` opens framebuffer temporarily.
- `fbink.c:4648–4653` uses `open_fb_fd_nonblock()`.
- `fbink.c:4123–4145`: if the fd is `FBFD_AUTO`, that function opens framebuffer using **`O_RDONLY | O_NONBLOCK | O_CLOEXEC`** and records that the descriptor should be closed after init. For the Clara BW MTK branch, the accelerometer/I²C exception is not taken (condition tests `isSunxi`).
- By contrast `fbink_open()` at `fbink.c:4066–4070` uses `O_RDWR`, as does the original CP-KOBO-043 source. **Prefer AUTO for first device-side init, if and only if the complete audit is cleared.**
- `fbink.c:4388–4435` `update_pen_colors()` only calculates/stores in-process pen values with `pack_pixel_from_y8`. It does not request a display refresh in the inspected implementation.
- `fbink.c:4029–4033` `wakeup_epdc_kobo_mtk()` **writes** `fiti_power 1` into `/proc/hwtcon/cmd`. Init at `fbink.c:4780–4785` assigns this function to a pointer, but does **not** invoke it at that site. Any call to `fbink_wakeup_epdc()` in the diagnostic is explicitly prohibited.
- Hardware identification via `identify_kobo()` reads Nickel's version tag (confirmed physical model code 395 in CP-KOBO-042). Hardware fallback paths read block metadata.

## Safety conclusions
1. `FBFD_AUTO` greatly reduces **requested framebuffer permissions** for init compared with `fbink_open()`, but cannot guarantee zero kernel-driver side effects. The framebuffer driver may have side effects on open or GET ioctls.
2. The specific MTK wakeup helper has an explicit **write side effect** if called. Do not invoke it.
3. This is still a source-scoped audit; a complete review of all transitive init dependencies and display ownership has not been completed. Physical `fbink_init()` **remains gated**.

## Planned first manual-only test once cleared
- One standalone diagnostic binary, no automatic boot integration and no firmware flash.
- Read-only preflight: model code must be 395, kernel framebuffer metadata must match CP-KOBO-039. Do not log full Nickel version tag (privacy).
- Open log file on internal storage; flush and sync preflight **before** touching framebuffer.
- `fbink_init(FBFD_AUTO, &cfg)` exactly once, with a fully zero-initialized config. No separate `fbink_open`, no explicit `fbink_close` of the internally managed descriptor.
- `fbink_get_state` for device ID, isMTK, bpp, rotation, pixel-format, dimensions; append success/failure and sync logs.
- For error/timeouts: keep FAILED status and retain logs; do not try to force a refresh or silently restart Nickel.
- After manual test verify Nickel display, touch, page navigation, and KOReader launch. If unexpected display behavior occurs, stop tests and follow the user's normal device reboot/recovery procedure.
- Do not imply that a watchdog can reverse kernel display changes.
- Public X4/X4 Classic release and existing NickelMenu/KOReader untouched.

## Status
**CP-KOBO-045 documented. No deployment binary or device test generated.** The permission reduction is the main actionable source discovery; release of a physical-init binary requires resolving outstanding safety questions.
