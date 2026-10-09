# CP-KOBO-041 — Kobo model detection and FBInk init call audit

Pinned FBInk: `886f25f13368859ad8a899b88d04c26e19cda32e`.

**Result: SOURCE REVIEW PASS (scoped); no physical `fbink_init` trial performed.**

## Device identification path (`fbink_device_id.c`)
- `identify_kobo()` at lines 1385–1602 first opens `/mnt/onboard/.kobo/version` with `fopen(..., "re")` (read mode), reads Nickel version string, and extracts the final three digits for the Kobo device model. **Device-side value not yet measured**, so do not assert runtime ID 395.
- If that path cannot be read, it attempts fallback `HWConfig` block devices using `fopen(..., "re")` and reads; it may issue `BLKGETSIZE64` to query storage size. Avoid testing during USB mass storage, where the first path is unavailable.
- For Kobo Clara BW TPV model 395, `set_kobo_quirks()` at 1279–1296 configures `isMTK=true`, 300 DPI, `rotationMap={3,2,1,0}` and the Clara B&W (Spa BW TPV) name. This is a **source-defined** setting; model selection remains to be confirmed on the actual unit.

## Initialization path (`fbink.c`)
- `fbink_open()` at 4066–4071 opens `/dev/fb0` as `O_RDWR | O_CLOEXEC`. The normal FBInk API init is **not read-only**.
- `fbink_init()` at 5605–5609 invokes `initialize_fbink()`.
- `initialize_fbink()` at 4648–5601 contains first-run `identify_device()`, Kobo MTK quirk assignment at 4780–4785, GET-only framebuffer ioctls `FBIOGET_VSCREENINFO` (4858) and `FBIOGET_FSCREENINFO` (4885) for that path.
- Explicit `EPDC_GET_UPDATE_STATE` seen near 4798 is inside a **PocketBook-only compile-time branch**, not the Kobo/MTK path.
- In the inspected initialize function, no direct `FBIOPUT_VSCREENINFO` or `HWTCON_SEND_UPDATE` appears. However, a call-graph audit of all helpers and kernel side effects is still needed; absence of these calls in this one function does not prove all device-side effects absent.
- Separate `hwtcon` renderer contains `HWTCON_SEND_UPDATE` at 3407. That update path should be exercised **only after** device initialization is validated with an independent recovery plan.

## Existing measured framebuffer state
- CP-KOBO-039: 1072x1448; 32 bpp; rotation 3; RGBA channel offsets R0 G8 B16 A24 and lengths 8 each, little-endian.
- For FBInk 32-bpp selection (`fbink.c:5503–5519`), `red.offset == 0` and `transp.length == 8` correspond to `FBINK_PXFMT_RGBA`. This is a **static prediction from measured inputs**, not a device log from `fbink_init()`.

## Important next gate
Before a physical init, confirm the device model ID via **read-only parsing of the Nickel version tag** and complete inspection of init helper calls and Nickel ownership/recovery. This doc does not authorize testing `fbink_init()` or any display refresh.

**No firmware or program deployment produced by CP-KOBO-041.**
