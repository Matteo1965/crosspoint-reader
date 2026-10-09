# CP-KOBO-049 — Init probe safety review and explicit go/no-go gates

FBInk pinned revision: `886f25f13368859ad8a899b88d04c26e19cda32e`.

## Review of actual CP-KOBO-048 sources

Reviewed `scripts/kobo_fbink_048_manual_init_probe.c` and `scripts/kobo_fbink_048_launch.sh` on `feature/kobo-v224`.

### Confirmed safeguards
- Explicit launch argument and model suffix `395`.
- GET-only O_RDONLY framebuffer preflight (1072x1448 32bpp, rotation=3, R/G/B/A=0/8/16/24, stride=4288).
- `fbink_init(FBFD_AUTO, ...)` instead of opening with `fbink_open()`; FBInk's FBFD_AUTO path requests O_RDONLY.
- Exclusive creation of attempt marker using `O_EXCL`, and `fsync` calls.
- No explicit drawing/refresh/wakeup calls.

### Correctness and recovery issues that remain
1. The launcher redirects program stdout/stderr into a separate `output.txt`. An abrupt termination can leave the durable init checkpoint at `INIT ENTER` and no exit code; this is **UNKNOWN**, not success/failure.
2. The attempt marker can remain on disk if marker creation succeeds but its write or directory `fsync` fails. This is an intentional fail-closed condition, not grounds for deleting the marker and retrying.
3. Launcher `chmod +x` changes file metadata at runtime; prefer installing permissions in CI and treating a missing executable bit as a deployment error. No auto repairs should be performed by the launcher.
4. The version parser uses a fixed 256-byte buffer, then tests its last three characters. A truncated tag could produce a misleading parse. Future probe should verify the entire version-file length and exact allowed suffix before init.
5. Preflight checks only selected framebuffer fields, not all fixed/variable details. In particular `f.smem_len`, virtual size and offsets are currently omitted.
6. The durable log's `write()` is not retried on `EINTR`/partial writes, and errors in logging after init may obscure whether init itself succeeded.
7. The single marker prevents repeated calls *by this binary* but does not prevent a different executable, manual terminal command or a copied binary from initiating FBInk.
8. `cmd_output:9000` is not an independent verified recovery mechanism. User can observe a hung Nickel UI; watchdog timeout cannot restore a kernel graphics controller.
9. A source inspection plus static ARM build does **not** demonstrate that the Nickel-owned display is safe for concurrent FBInk initialization.
10. Full transitive initialization-call-chain audit and physical rollback verification remain open. **The build is experimental, not certified risk-free.**

## Required state model (not yet implemented)
`NOT_STARTED` → `PREFLIGHT_FAILED` (no marker) OR `ATTEMPTED` (marker created before init) → `INIT_FAILED` / `INIT_RETURNED` / `UNKNOWN_INTERRUPTED`.

`INIT_RETURNED` is *not* `DEVICE_VERIFIED`. Device verification is manual: Nickel main UI, touch, book navigation, KOReader launch, and normal return to Nickel must all remain functional.

Any `ATTEMPTED`, `INIT_FAILED` or `UNKNOWN_INTERRUPTED` outcome must prevent automatic repeats. Preserve log and marker.

## Deployment decision
**NO-GO** for a new physical init test until an independent safe recovery procedure and missing call-graph/driver side effects are addressed. Do not instruct installation/run of CP-KOBO-048 solely on the basis of successful static compilation.

No source code or existing Kobo / X4 firmware is modified by this document. The next revision should implement fail-closed logging and status reporting in source and CI-check them before considering any physical test.
