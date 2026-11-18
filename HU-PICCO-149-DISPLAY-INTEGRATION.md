# HU-PICCO-149 — Beta v4 display integration checklist

Baseline: `agent/hu-picco-148-epd-beta4` (sleep-screen clean reverted; effective sleep code matches HU-PICCO-147).
Upstream display PR: crosspoint-reader/crosspoint-reader#4362, commit `5058eb436b42a33b6ea15d9275703889c5e3f69c`.
Upstream FreeInk SDK associated with that commit: `a8acebf919fdc92b304b80eb0352d203fefc5578` (not yet adopted).

## Target — reading screen only
1. Picco display waveforms and ghosting reduction (SDK panel driver).
2. EPUB image grayscale improvements (reader / renderer / HalDisplay + SDK).
3. Night-mode and EPD performance improvements.
4. Verify portrait/landscape, images/text and suspend/resume on physical Picco.

## Explicitly excluded
- The extra opaque sleep-screen pre-clean from #4362: user reported no visible benefit; reverted in commit `968ade571be44c304b95e476fadb364cbaf82bca`.
- Wholesale upstream overwrite of HU typography, hyphenation, reader menus, or cached .cpfont metrics.
- Unreviewed SDK submodule pointer change before the corresponding callers and Picco host tests are integrated.

## Important dependencies
`ReaderUtils::ReaderRefreshScope`, `HalDisplay::setReaderRefresh`, `HalDisplay::controllerIdle`, retained grayscale overlay, and Picco absolute grayscale support need coordinated SDK + caller changes. A partial transplant can introduce link/build errors or incorrect e-ink waveforms.

## Minimum validation
- Compile Picco target; run Hungarian hyphenation tests and Picco FreeInk SDK host tests.
- Open EPUB chapters with text and grayscale images; inspect waveform behavior.
- Verify Bitter .cpfont 16pt layout/kerning and long chapter transitions remain unchanged.
- Verify night mode, full/partial refresh, ghosting and sleep/wake, without re-introducing the sleep-screen clean.
- No public release until on-device test passes.

Status: integration plan only — EPD driver changes have NOT been ported or built on this branch.

## Development branch policy
Continue HU-PICCO-150 and later preview integrations **on this same branch** (`agent/hu-picco-149-display-beta4`); do not create a separate feature branch. Keep the working HU-PICCO-149 commit identifiable as the rollback point. Each independent EPD/SDK change should be committed and tested separately. Bump the firmware version only when preparing the next test build.
