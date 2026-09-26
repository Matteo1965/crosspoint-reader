# CPHUN-157 — Four selective 1.6.5rc repairs, USB excluded

Source baseline: same tracked src/lib tree as the last successful CPHUN-152 branch. The CPHUN-157 workflow restores the successful CPHUN-152 patch/build chain from that branch before regression testing and firmware compilation. The developer branch was originally forked from CPHUN-156, which shares the tracked src/lib baseline but not the same build scripts.

## Implementation

- [x] Short button taps: 50 ms low-power delay now divided into 10 ms slices and interrupted on raw input contact (HalGPIO and main loop); requires real X4 debounce tests.
- [x] List redraw input: normal single-list button navigation queues requested selections atomically while the renderer holds its render lock, including a post-refresh re-request if input arrives during display; tab-list navigation retains its prior implementation.
- [x] Sleep-overlay safety: the existing sleep-screen pipeline checks each BMP rewind and avoids committing a partially prepared frame. **Do not reuse, call, or move the Hungarian Edition's custom grayscale cover-rendering pipeline into SleepActivity.** The custom pipeline is reserved exclusively for the **Könyv > Borítókép** function. Keep SleepActivity on its independent existing/upstream-compatible sleep rendering path; any upstream alpha/transparency fix must be adapted there without copying cover-rendering code. Transparent PNG/BGRA BMP support remains intact.
- [x] Chapter position: cached page/total remain available while section is released, and progress is bounded; end-of-book menu selection uses atomic cross-task state.
- [ ] CI and physical X4 verification (do not mark complete solely on source checks).

## Explicit exclusions

- USB connection and forced disconnect are OUT OF SCOPE: no changes to existing Hungarian Edition USB handler or HalStorage.
- No blanket merge of upstream 1.6.5rc or its FreeInk SDK dependency; protect Hungarian hyphenation and custom typography.
- Hungarian Edition-specific grayscale cover handling applies only to **Könyv > Borítókép**, never to the sleep screen.

## Build

Workflow: .github/workflows/build-cphun-157-four-fixes.yml
Firmware name: CPHUN-260926-157-FOUR-FIXES-X4
Pipeline: restore tested CPHUN-152 tools, apply all CPHUN-152 source patches, static checks, CMake regression tests, PlatformIO gh_release firmware compilation, upload artifact.

## X4 regression checklist

1. Rapid short Up/Down/Confirm/Back after long idle and immediately after wake.
2. Repeated Up/Down/Confirm while a long file list is being repainted. Repeat with RoundedRaff dense rows and tabbed Settings lists.
3. Transparent PNG / BGRA BMP sleep overlays over light and dark text, white and grayscale overlay pixels, corrupt-BMP fallback; confirm sleep rendering does not invoke the Hungarian Edition custom cover grayscale path and Könyv > Borítókép retains its existing quality.
4. First / middle / final chapter pages, during and after reindex, end-of-book navigation and rapid Confirm.
5. Hungarian extended hyphenation, letter-spacing profiles, SD card fonts, existing successful export notification, chapter reindex and settings persistence.
6. Existing USB behavior unchanged (smoke check only, no new USB-disconnect handling).

This is a test build, not a tested release.
