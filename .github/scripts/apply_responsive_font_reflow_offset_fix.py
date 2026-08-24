from pathlib import Path

p = Path("src/activities/reader/EpubReaderActivity.cpp")
text = p.read_text(encoding="utf-8")

# Keep the exact visible-text offset as the foreground reflow target. The previous
# responsive patch reset offsetJump and chased the old page number instead, which
# is especially wasteful when switching to a smaller font (e.g. 16pt -> 14pt).
old_offset = '''    if (responsiveFontReflowPending && !explicitOffsetJump) {
      // Exact content-offset remapping is deferred until the section build completes.
      // This avoids a long synchronous scan after any font-size/family change.
      offsetJump.reset();
    }
'''
new_offset = '''    if (responsiveFontReflowPending && !explicitOffsetJump && offsetJump.has_value()) {
      // Keep the exact saved visible-text offset as the target. Page numbers are
      // layout-dependent and can move dramatically after a font-size change, while
      // the visible-text offset remains stable across reflow.
      LOG_DBG("ERS", "Responsive font reflow targeting visible offset %lu",
              static_cast<unsigned long>(*offsetJump));
    }
'''
count = text.count(old_offset)
if count != 1:
    raise SystemExit(f"responsive offset reset block: expected 1 match, found {count}")
text = text.replace(old_offset, new_offset, 1)

# After each one-page foreground slice, return to the event loop whenever the exact
# offset is still not reached. This preserves UI responsiveness without falling back
# to the stale pre-reflow page number.
old_slice = '''            if (responsiveFontReflowPending && !anchorJump && !offsetJump.has_value() &&
                !section->isBuildComplete() && static_cast<int>(section->pageCount) <= target) {
              // Preserve the old page number as the short-term target. renderBook()
              // returns now, so the main loop can process buttons before the next slice.
              section->currentPage = target;
              requestUpdate();
              return;
            }
'''
new_slice = '''            if (responsiveFontReflowPending && !section->isBuildComplete()) {
              const bool responsiveTargetReached =
                  offsetJump.has_value() ? section->buildReachedVisibleTextOffset(*offsetJump)
                                         : (!anchorJump && static_cast<int>(section->pageCount) > target);
              if (!responsiveTargetReached) {
                // One foreground page is enough for this turn. Return immediately so
                // button/menu input can be processed before the next reflow slice.
                requestUpdate();
                return;
              }
            }
'''
count = text.count(old_slice)
if count != 1:
    raise SystemExit(f"responsive foreground slice block: expected 1 match, found {count}")
text = text.replace(old_slice, new_slice, 1)

# Once the exact offset has become available, map directly to its new page before
# clearing the responsive state. This avoids waiting for the full section build.
old_clear = '''  if (responsiveFontReflowPending && section->pageCount > 0 &&
      section->currentPage < static_cast<int>(section->pageCount)) {
    responsiveFontReflowPending = false;
  }
'''
new_clear = '''  if (responsiveFontReflowPending && section->pageCount > 0) {
    bool responsiveTargetReady = false;
    if (cachedVisibleTextOffset.has_value() &&
        section->buildReachedVisibleTextOffset(*cachedVisibleTextOffset)) {
      if (const auto mappedPage = section->getPageForVisibleTextOffset(*cachedVisibleTextOffset)) {
        section->currentPage = *mappedPage;
        responsiveTargetReady = true;
      }
    } else if (!cachedVisibleTextOffset.has_value() &&
               section->currentPage < static_cast<int>(section->pageCount)) {
      responsiveTargetReady = true;
    }
    if (responsiveTargetReady) {
      responsiveFontReflowPending = false;
    }
  }
'''
count = text.count(old_clear)
if count != 1:
    raise SystemExit(f"responsive reflow clear block: expected 1 match, found {count}")
text = text.replace(old_clear, new_clear, 1)

p.write_text(text, encoding="utf-8")
