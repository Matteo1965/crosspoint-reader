# CP-KOBO-040 — Clara BW FBInk initialization audit (source-only)

FBInk pinned commit: `886f25f13368859ad8a899b88d04c26e19cda32e`

**Result: PARTIAL SOURCE VALIDATION; device-side `fbink_init()` NOT authorized yet.**

## Confirmed in source
- `fbink_device_id.c:1279–1296`: Clara B&W TPV `DEVICE_KOBO_CLARA_BW_TPV` configures `isMTK=true`, the canonical/native mapping `{3,2,1,0}`, 300 DPI, and Mark 12 device label. Hardware detection on physical device still unconfirmed.
- `fbink.c:4066–4071`: `fbink_open()` requests `O_RDWR | O_CLOEXEC`, therefore *not read-only*.
- `fbink.c:5605–5609`: `fbink_init()` calls `initialize_fbink(...,false)`.
- `fbink.c:4650–4654`: initializer checks/opens framebuffer descriptor.
- `fbink.c:4663–4667`: initializer calls `identify_device()` on first run.
- `fbink.c:4780–4785`: MTK branch selects `wakeup_epdc_kobo_mtk` and enables update-submission wait.
- `fbink.c:4857–4888`: FBIOGET_VSCREENINFO/FBIOGET_FSCREENINFO are present; GET calls are not proof that the *entire* init path is side-effect-free.
- `fbink.c:5503–5519`: pixel type chosen from `vInfo.red.offset`, `vInfo.transp.length` and bpp.
- `fbink.c:3309–3410`: HWTCON_SEND_UPDATE is a distinct display-update pathway; not exercised by CP-KOBO-035/039.

## Physical facts (prior diagnostic results)
- 1072x1448, 32-bpp; native framebuffer `rotate=3`.
- Channel positions R=0/8, G=8/8, B=16/8, A=24/8.
- `mdp_src_format=ABGR32`. Do not conflate this sysfs format with byte-order terminology.
- CP-KOBO-035 showed statically linked FBInk can execute `--help`, **before framebuffer initialization**.
- CP-KOBO-039 queried GET ioctls with `O_RDONLY`; no FBInk initialization.

## Outstanding blockers to physical `fbink_init()`
1. Trace *all* functions invoked by `initialize_fbink()`, including `identify_kobo()`, optional EPDC wakeup, sysfs access, and setup helpers. Audit for PUT/modeset ioctl, write, mmap, sysfs/proc writes, refresh and I2C effects.
2. Confirm Kobo model detection against actual physical config, not solely source device entry.
3. Establish Nickel display ownership policy and an independent recovery mechanism; timeouts alone cannot undo a framebuffer modeset.
4. Prepare explicit opt-in and separate logging; do not mix with public X4/X4 Classic release.

Next proposed probe is a source-scoped audit of `identify_kobo()` and init callees, without new physical tests. No display test binary shipped by this commit.
