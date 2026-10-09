# CP-KOBO-038 — FBInk v886f25f1 init/display source audit

Scope: **source only**, no physical device test, framebuffer open, mode change, or display update.

## Verified in pinned NiLuJe/FBInk source

- `fbink_cmd.c:2028–2033`: `--help` exits before `fbink_open()`, confirming CP-KOBO-035 tested CLI execution rather than hardware initialization.
- `fbink.c:4066–4070`: `fbink_open()` opens framebuffer with `O_RDWR|O_CLOEXEC`; **not a read-only probe**.
- `fbink.c:5605–5609`: `fbink_init()` calls `initialize_fbink(..., false)`.
- `fbink.c:4648–4653`: initialization opens/uses the framebuffer fd and proceeds to device-specific handling.
- `fbink.c:4780–4785`: MTK quirk branch enables wait-for-submission and selects `wakeup_epdc_kobo_mtk`.
- `fbink.c:4857–4888`: initialization fetches variable/fixed framebuffer information using GET ioctls; the complete function's side effects have **not been proven absent**.
- `fbink.c:5503–5519`: 32-bpp pixel rendering classification depends on the actual `fb_var_screeninfo` **red/transparency bitfields**, not sysfs `mdp_src_format` alone.
- `fbink.c:3309–3410`: MTK `hwtcon_update_data` is issued through `HWTCON_SEND_UPDATE` in the render/update pathway; hardware refresh remains UNTESTED.
- `fbink_device_id.c:1279`: code path for Kobo Clara BW TPV exists; **actual runtime device identification remains unverified**.

## Safety gates before first device-side init

1. Inspect the **entire** `initialize_fbink` call graph for writes, modeset ioctls, I2C, EPDC wakeup and other side effects; no sign-off based on a few GET calls.
2. Avoid treating `--eval` or `--verbose` as a read-only probe: they enter the init path.
3. For a first framebuffer experiment, isolate it from Nickel ownership; plan physical reboot/recovery and retain KOReader/NickelMenu untouched.
4. Use a separate, explicit-user-triggered test after audit sign-off, with timeouts, logging, and *no* mass-storage reconnection before completion.
5. Do not infer ABGR32 framebuffer channel offsets from `mdp_src_format=ABGR32`; query fb variable bitfields first without altering the mode.

**CP-KOBO-038 result: SOURCE_PATH_REVIEW_IN_PROGRESS — NOT AUTHORIZED TO RUN FBINK_INIT ON DEVICE.**

Source pinned: https://github.com/NiLuJe/FBInk/tree/886f25f13368859ad8a899b88d04c26e19cda32e
