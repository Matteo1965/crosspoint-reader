# CPHUN-161 — SD-card font-cache fragmentation

Base: Xteink X4 hardware-tested CPHUN-160. Upstream: crosspoint-reader/crosspoint-reader PR #3521, exact source-file port based on matching pre-PR bytes. The previously integrated PR #3527 chapter-entry cache release remains active.

## Changes
- Complete page prewarm replaces the page glyph set instead of accumulating the union of earlier pages. UI title/label prewarm continues accumulating.
- Bitmap arena underuse hysteresis runs on the next cache miss instead of releasing freshly prefetched glyphs when the prewarm scope closes.
- Drop transient glyph mappings before allocating the large bitmap. Release old bitmap and temporary read order before growth; reserve a contiguous bitmap earlier if fragmentation prevents growth and retry after dropping rebuildable advance tables if necessary.
- Preserve existing SD fonts, fallback-glyph handling, Hungarian word-spacing/kerning measurement and extended hyphenation.

## CI release gates
- Assert the four exact upstream-modified font source files survive the CPHUN-152 legacy regeneration process unmodified.
- Reapply and verify the CPHUN-160 cache release and prior CPHUN-159 hidden text/KOReader mapping after legacy source generation.
- Run upstream SD font cache tests for bitmap growth, fresh prewarm retention, incremental UI accumulation, fragmented-heap retry and advance-table eviction.
- Run existing Hungarian regression tests and build X4 firmware.
- Verify hardware-button input files byte-identical with the tested CPHUN-152 input baseline and the USB files unchanged.

## On-device checks
1. Before other checks, verify hardware buttons after idle and wake.
2. Open LiterataBook and another SD-card font, then open several books and alternate between compact and very long chapters.
3. Repeatedly move from the end of one chapter to the start of another and compare page-layout speed and stability to CPHUN-160.
4. Rapidly page forward and back within the same chapter and inspect whether prefetched pages remain smooth rather than repeatedly loading from SD.
5. Confirm short-hyphen fallback, long-word handling, fixed dialogue spacing and optical margins at several settings.
6. Browse long chapter lists and large file folders with SD fonts; labels should remain legible and navigation responsive.
7. Reconfirm KOReader sync and the CPHUN-160 chapter navigation remain correct.

Do not promote on CI alone. X4 hardware and SD-card performance must be validated.
