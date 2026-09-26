# CPHUN-159 — hidden EPUB and precise KOReader synchronization

Baseline: hardware-tested CPHUN-157r1 (button input and USB unchanged). Source upstream: CrossPoint 1.6.5rc PR #3390 (HTML hidden) and PR #3174 (precise KOReader XPath).

## Included
- HTML `hidden` overrides CSS display in the EPUB parser, suppressing whole hidden subtrees.
- Exact zero-based visible-codepoint offsets now resolve to XHTML ancestry and text-node positions for KOReader uploads. On resolver failure, preserve paragraph and approximate-progress fallback.
- Explicitly exclude HTML `hidden` subtrees from both the progress estimator and exact-XPath resolver so the two newly integrated fixes agree.
- Invalidate old section cache after restoring the tested HU source patch chain, because hidden content changes layout.
- Port upstream XPath regression tests plus one HU integration test for nested hidden HTML.
- Preserve CPHUN-157r1 chapter position, end-of-book selection, sleep overlay safety, and the CPHUN-152 export and SD-font glyph fallback.

## Excluded
- Upstream ordered/unordered list rendering and indentation: the HU `Párbeszéd fix` and list-marker handling remain unchanged.
- Short-contact raw ADC and queued selection input patches from the broken CPHUN-157: intentionally reverted.
- USB changes, SDK wholesale upgrades, and Hungarian Edition custom cover grayscale changes.

## Physical acceptance tests
1. X4 front/side buttons immediately after boot, after idle and after waking; reader and list menus.
2. An EPUB with `<p hidden>`, `<span hidden>` and `<div hidden>` should show only non-hidden text, even when hidden elements declare `style="display:block"`. Reindex any old cached section.
3. Upload a KOReader sync position in the middle of an EPUB paragraph; inspect that the saved XPath contains a real `text()[N].offset` and round-trip back to the intended sentence.
4. Repeat sync with accented Hungarian words, nested inline markup and a hidden span; ensure hidden text does not shift the location.
5. Verify Hungarian extended hyphenation, `Párbeszéd fix`, numbered list spacing, SD-font fallback, TSV export notification, chapter navigation and sleep screen remain unchanged.

CI compiles/runs XPath regression cases and the existing project tests. Real KOReader server interoperability and actual X4 button operation require on-device verification.
