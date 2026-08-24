from pathlib import Path


def replace_once(path: str, old: str, new: str, label: str):
    p = Path(path)
    text = p.read_text(encoding="utf-8")
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{label}: expected exactly one match, found {count}")
    p.write_text(text.replace(old, new, 1), encoding="utf-8")


# Keep font-change reflow interactive even after the saved visible-text offset has
# been reached. The section can continue to build, but it must behave as low-priority
# background work until that build is actually complete.
h = Path("src/activities/reader/EpubReaderActivity.h")
htext = h.read_text(encoding="utf-8")
old_h = '''  static constexpr int BACKGROUND_BUILD_PAGES_PER_TICK = 2;
  static constexpr size_t BACKGROUND_BUILD_MIN_FREE_HEAP = 32 * 1024;
'''
new_h = '''  // Background pagination must never monopolize the reader event loop. One page
  // per tick keeps individual stalls bounded, especially at smaller font sizes.
  static constexpr int BACKGROUND_BUILD_PAGES_PER_TICK = 1;
  static constexpr unsigned long BACKGROUND_BUILD_IDLE_MS = 250;
  static constexpr size_t BACKGROUND_BUILD_MIN_FREE_HEAP = 32 * 1024;
'''
if htext.count(old_h) != 1:
    raise SystemExit(f"background build constants: expected 1 match, found {htext.count(old_h)}")
htext = htext.replace(old_h, new_h, 1)

old_flag = '''  bool responsiveFontReflowPending = false;
  void showBuildPopup(GfxRenderer& renderer, int& pagesUntilFullRefresh);
'''
new_flag = '''  bool responsiveFontReflowPending = false;
  // Remains true after the saved position is found, until the section build itself
  // finishes. While true, background pagination yields aggressively to reader input.
  bool fontReflowBackgroundThrottled = false;
  void showBuildPopup(GfxRenderer& renderer, int& pagesUntilFullRefresh);
'''
if htext.count(old_flag) != 1:
    raise SystemExit(f"responsive reflow flag marker: expected 1 match, found {htext.count(old_flag)}")
htext = htext.replace(old_flag, new_flag, 1)
h.write_text(htext, encoding="utf-8")

r = Path("src/activities/reader/EpubReaderActivity.cpp")
rtext = r.read_text(encoding="utf-8")

# A real font-size/family change enables both the foreground offset seeker and the
# longer-lived low-priority background scheduler mode.
old_set = '''                                 responsiveFontReflowPending = beforeSpec.fontId != afterSpec.fontId;
                                 RenderLock lock;
'''
new_set = '''                                 responsiveFontReflowPending = beforeSpec.fontId != afterSpec.fontId;
                                 fontReflowBackgroundThrottled = responsiveFontReflowPending;
                                 RenderLock lock;
'''
if rtext.count(old_set) != 1:
    raise SystemExit(f"font reflow activation marker: expected 1 match, found {rtext.count(old_set)}")
rtext = rtext.replace(old_set, new_set, 1)

# Background work begins only after a short idle window following the last completed
# render, and never on a loop iteration that already contains a physical button edge.
# This gives menu/page-turn input priority over pagination work.
old_bg = '''  if (section && section->isBuilding() && !RenderLock::peek() &&
      (section->isPartial() || static_cast<int>(section->pageCount) < section->currentPage + BUILD_WINDOW_AHEAD) &&
      buildTickHeapGate()) {
    RenderLock lock;
    if (section->isBuilding() && buildTickHeapGate()) {
      if (!section->buildSomeMore(BACKGROUND_BUILD_PAGES_PER_TICK)) {
        LOG_ERR("ERS", "Background section build failed");
        section.reset();
        requestUpdate();
      } else if (section->isBuildComplete() && applyDeferredReposition()) {
        requestUpdate();
      }
    }
  }
'''
new_bg = '''  const bool readerInputPending = mappedInput.wasAnyPressed() || mappedInput.wasAnyReleased();
  const bool backgroundBuildIdle =
      !fontReflowBackgroundThrottled ||
      (lastRenderCompleteMs != 0 && millis() - lastRenderCompleteMs >= BACKGROUND_BUILD_IDLE_MS);
  if (section && section->isBuilding() && !RenderLock::peek() && !readerInputPending && backgroundBuildIdle &&
      (section->isPartial() || static_cast<int>(section->pageCount) < section->currentPage + BUILD_WINDOW_AHEAD) &&
      buildTickHeapGate()) {
    RenderLock lock;
    if (section->isBuilding() && !mappedInput.wasAnyPressed() && !mappedInput.wasAnyReleased() && buildTickHeapGate()) {
      if (!section->buildSomeMore(BACKGROUND_BUILD_PAGES_PER_TICK)) {
        LOG_ERR("ERS", "Background section build failed");
        section.reset();
        responsiveFontReflowPending = false;
        fontReflowBackgroundThrottled = false;
        requestUpdate();
      } else if (section->isBuildComplete()) {
        fontReflowBackgroundThrottled = false;
        responsiveFontReflowPending = false;
        if (applyDeferredReposition()) requestUpdate();
      }
    }
  }
'''
if rtext.count(old_bg) != 1:
    raise SystemExit(f"background build block: expected 1 match, found {rtext.count(old_bg)}")
rtext = rtext.replace(old_bg, new_bg, 1)

# The normal zero-delay fast loop is useful for non-interactive indexing, but after a
# font change it starves reader input. Keep the ordinary loop cadence until reflow
# background work has completed.
old_skip = '''bool EpubReaderActivity::skipLoopDelay() {
  return section && section->isBuilding() && !buildHeapPaused &&
         (section->isPartial() || static_cast<int>(section->pageCount) < section->currentPage + BUILD_WINDOW_AHEAD);
}
'''
new_skip = '''bool EpubReaderActivity::skipLoopDelay() {
  if (fontReflowBackgroundThrottled) return false;
  return section && section->isBuilding() && !buildHeapPaused &&
         (section->isPartial() || static_cast<int>(section->pageCount) < section->currentPage + BUILD_WINDOW_AHEAD);
}
'''
if rtext.count(old_skip) != 1:
    raise SystemExit(f"skipLoopDelay block: expected 1 match, found {rtext.count(old_skip)}")
rtext = rtext.replace(old_skip, new_skip, 1)

r.write_text(rtext, encoding="utf-8")
