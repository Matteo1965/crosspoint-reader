# CP-KOBO-044 — FBInk initialization safety gate and recovery plan

Pinned upstream FBInk: `886f25f13368859ad8a899b88d04c26e19cda32e`.

## Result: NOT CLEARED FOR DEVICE DEPLOYMENT

CP-KOBO-043 validated cross-linking only; not runtime safety. This phase prepares a conservative physical-init gate, with no executable delivered to the Kobo.

### Identified facts
- CP-KOBO-042 physical model code `395` from Nickel's `/mnt/onboard/.kobo/version`: confirmed Clara BW TPV.
- CP-KOBO-039 read `/dev/fb0` via `O_RDONLY` + `FBIOGET_VSCREENINFO`, `FBIOGET_FSCREENINFO`; 1072×1448, 32bpp, native rotation 3, R0/G8/B16/A24.
- `fbink.c:4648–4666`: `initialize_fbink()` obtains framebuffer fd and performs first-run device identification.
- `fbink.c:4681–4785`: for the MTK Kobo path, init assigns wakeup function pointer `wakeup_epdc_kobo_mtk` but does not call that wakeup in the inspected branch; Sunxi accelerometer/I²C setup is in a separate branch.
- `fbink.c:4857–4888`: GET variable and fixed framebuffer metadata.
- `fbink.c:4066–4070`: normal `fbink_open()` opens `/dev/fb0` with `O_RDWR`; opening writable fd alone is not proof of actual write.
- `fbink.c:3309–3410`: separate HWTCON update path exists and must not be invoked in the first init test.
- `fbink.c:5605–5609`: `fbink_init()` delegates to `initialize_fbink()`; no drawing/refresh function is intentionally used by the CP-KOBO-043 probe.

### Safety gaps / no-go conditions
1. Full audit of helper-function call graph (`open_fb_fd_nonblock`, `identify_mainline` fallback, `update_pen_colors`, quirk path and possible libc/kernel side effects) remains incomplete. **Not safe to claim zero side effects.**
2. A process timeout can kill the test process but cannot restore display state if kernel modeset or controller state changes. Do not imply a timeout automatically protects Nickel.
3. Nickel simultaneously owns the display. No verified protocol for sharing framebuffer state with Nickel, or restoration after unexpected effects.
4. No independent recovery mechanism verified on this physical unit. Recovery should rely on normal reboot and a reversible menu-only setup, not destructive operations.
5. Physical test must never auto-run on boot; do not touch KOReader startup or NickelMenu existing entries.
6. Compile-only CP-KOBO-043 source includes a risk-acknowledgment flag but is *not* a safe deployable artifact.

### Proposed first physical initialization test after closure
- New, distinct build artifact with an explicit manual NickelMenu item, separate from firmware updater.
- Validate code 395 before `fbink_open`; log preflight framebuffer metadata and monotonic timing, and flush log before opening device.
- One `fbink_init()` call with zero-initialized `FBInkConfig`, then `fbink_get_state`, close fd, flush results. Never call print/clear/mmap or refresh API.
- Record `device_id`, `is_mtk`, `bpp`, `pixel_format`, `current_rota`, return code and any stderr.
- Guard against repeat attempts via separate marker/status; failure must leave logs intact.
- After test check Nickel main screen, touch navigation and KOReader launch manually before any next test.
- Preserve current public X4/X4 Classic release and Kobo installation.

### Status
CP-KOBO-044 **planning and safety review completed**; physical `fbink_init()` test **deferred** until missing audits/recovery are closed. No device artifact produced.
