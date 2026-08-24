from pathlib import Path


def replace_once(path: str, old: str, new: str, label: str):
    p = Path(path)
    text = p.read_text(encoding="utf-8")
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{label}: expected exactly one match, found {count}")
    p.write_text(text.replace(old, new, 1), encoding="utf-8")


# -----------------------------------------------------------------------------
# 1) Min. spacing / natural-final-line interaction.
#    When the 50-80% justified layout makes the paragraph appear to fit, but the
#    final line no longer fits at its mandatory natural 100% spacing, retry
#    hyphenation on the final word before moving that whole word to a new line.
# -----------------------------------------------------------------------------
p = Path("lib/Epub/Epub/ParsedText.cpp")
text = p.read_text(encoding="utf-8")
old = '''    if (finalStart < finalEnd && naturalLineWidth(finalStart, finalEnd) > finalPageWidth) {
      size_t correctedBreak = finalEnd;
      // Search backwards: move only the minimum amount of text needed to make the
      // natural-100% final line fit. Searching forwards caused severe early wraps
      // at low Min. spacing values (e.g. 50%).
      for (size_t candidate = finalEnd - 1; candidate > finalStart; --candidate) {
        if (!TokenBoundary::allowsBreak(wordContinues[candidate], wordNoSpaceBefore[candidate])) continue;
        if (naturalLineWidth(candidate, finalEnd) <= pageWidth) {
          correctedBreak = candidate;
          break;
        }
      }
      if (correctedBreak < finalEnd) {
        lineBreakIndices.insert(lineBreakIndices.end() - 1, correctedBreak);
      }
    }
'''
new = '''    if (finalStart < finalEnd && naturalLineWidth(finalStart, finalEnd) > finalPageWidth) {
      bool repairedByHyphenation = false;

      // The compressed-space pass may have accepted the complete final word, so the
      // ordinary greedy overflow path never called hyphenateWordAtIndex(). Before
      // moving that whole word to a new line, give its widest legal prefix the same
      // opportunity it would have received during normal line construction.
      const size_t finalWordIndex = finalEnd - 1;
      int widthBeforeFinalWord = naturalLineWidth(finalStart, finalWordIndex);
      int gapBeforeFinalWord = 0;
      if (finalWordIndex > finalStart) {
        if (wordContinues[finalWordIndex]) {
          gapBeforeFinalWord =
              renderer.getKerning(fontId, lastCodepoint(words[finalWordIndex - 1]), firstCodepoint(words[finalWordIndex]),
                                  wordStyles[finalWordIndex - 1]);
        } else if (!wordNoSpaceBefore[finalWordIndex]) {
          gapBeforeFinalWord = renderer.getSpaceAdvance(fontId, lastCodepoint(words[finalWordIndex - 1]),
                                                        firstCodepoint(words[finalWordIndex]),
                                                        wordStyles[finalWordIndex - 1]);
        }
      }
      const int availableForFinalPrefix = finalPageWidth - widthBeforeFinalWord - gapBeforeFinalWord;
      if (availableForFinalPrefix > 0 &&
          hyphenateWordAtIndex(finalWordIndex, availableForFinalPrefix, renderer, fontId, wordWidths,
                               /*allowFallbackBreaks=*/false)) {
        // hyphenateWordAtIndex inserted the remainder at the old finalEnd index.
        // Keep the prefix on the previous line and make the inserted remainder the
        // new natural-spacing final line.
        lineBreakIndices.back() = finalEnd + 1;
        lineBreakIndices.insert(lineBreakIndices.end() - 1, finalEnd);
        repairedByHyphenation = true;
      }

      if (!repairedByHyphenation) {
        size_t correctedBreak = finalEnd;
        // If the word has no legal fitting split, fall back to the latest whole-word
        // boundary so we still move only the minimum amount of text.
        for (size_t candidate = finalEnd - 1; candidate > finalStart; --candidate) {
          if (!TokenBoundary::allowsBreak(wordContinues[candidate], wordNoSpaceBefore[candidate])) continue;
          if (naturalLineWidth(candidate, finalEnd) <= pageWidth) {
            correctedBreak = candidate;
            break;
          }
        }
        if (correctedBreak < finalEnd) {
          lineBreakIndices.insert(lineBreakIndices.end() - 1, correctedBreak);
        }
      }
    }
'''
if text.count(old) != 1:
    raise SystemExit(f"final-line repair block: expected 1 match, found {text.count(old)}")
text = text.replace(old, new, 1)
p.write_text(text, encoding="utf-8")


# -----------------------------------------------------------------------------
# 2) Responsive font-size reflow.
#    A font change invalidates layout, but must not monopolize renderBook() while
#    rebuilding dozens of pages to the old position. Build one page per foreground
#    slice, return to the event loop, and let the normal background builder finish
#    the rest after the old page number becomes available.
# -----------------------------------------------------------------------------
h = Path("src/activities/reader/EpubReaderActivity.h")
htext = h.read_text(encoding="utf-8")
old_h = '''  bool buildPopupPending = false;
  void showBuildPopup(GfxRenderer& renderer, int& pagesUntilFullRefresh);
'''
new_h = '''  bool buildPopupPending = false;
  // True only while a font-family/size change is rebuilding enough pages to make
  // the previously visible page available again. Foreground work is sliced so
  // input handling remains responsive; the rest continues in the normal background build.
  bool responsiveFontReflowPending = false;
  void showBuildPopup(GfxRenderer& renderer, int& pagesUntilFullRefresh);
'''
if htext.count(old_h) != 1:
    raise SystemExit(f"reader header build popup marker: expected 1, found {htext.count(old_h)}")
h.write_text(htext.replace(old_h, new_h, 1), encoding="utf-8")

r = Path("src/activities/reader/EpubReaderActivity.cpp")
rtext = r.read_text(encoding="utf-8")

# Mark only actual font changes for sliced foreground reflow. Other layout changes
# keep their existing behavior, minimizing risk to navigation/anchor workflows.
old_settings = '''                               if (layoutChanged) {
                                 RenderLock lock;
                                 if (section) {
'''
new_settings = '''                               if (layoutChanged) {
                                 responsiveFontReflowPending = beforeSpec.fontId != afterSpec.fontId;
                                 RenderLock lock;
                                 if (section) {
'''
if rtext.count(old_settings) != 1:
    raise SystemExit(f"text-settings layoutChanged marker: expected 1, found {rtext.count(old_settings)}")
rtext = rtext.replace(old_settings, new_settings, 1)

# For a font reflow, do not synchronously chase the saved visible-text offset.
# Preserve cachedVisibleTextOffset for applyDeferredReposition() after the background
# build completes; use the old page number as the immediate foreground target.
old_offset = '''    const std::optional<uint32_t> offsetJump =
        explicitOffsetJump ? pendingOffsetJump
        : (pendingPageJump.has_value() || !pendingAnchor.empty() || currentSpineIndex != cachedSpineIndex)
            ? std::nullopt
            : cachedVisibleTextOffset;
'''
new_offset = '''    std::optional<uint32_t> offsetJump =
        explicitOffsetJump ? pendingOffsetJump
        : (pendingPageJump.has_value() || !pendingAnchor.empty() || currentSpineIndex != cachedSpineIndex)
            ? std::nullopt
            : cachedVisibleTextOffset;
    if (responsiveFontReflowPending && !explicitOffsetJump) {
      // Exact content-offset remapping is deferred until the section build completes.
      // This avoids a long synchronous scan after any font-size/family change.
      offsetJump.reset();
    }
'''
if rtext.count(old_offset) != 1:
    raise SystemExit(f"offsetJump marker: expected 1, found {rtext.count(old_offset)}")
rtext = rtext.replace(old_offset, new_offset, 1)

# In the initial build loop, one page is enough for each font-reflow foreground slice.
old_build = '''            if (!section->buildSomeMore(BUILD_PAGES_PER_CHUNK)) {
              LOG_ERR("ERS", "Failed during incremental section build");
              section.reset();
              buildPopupPending = false;
              showBuildError();
              return;
            }
'''
new_build = '''            if (!section->buildSomeMore(responsiveFontReflowPending ? 1 : BUILD_PAGES_PER_CHUNK)) {
              LOG_ERR("ERS", "Failed during incremental section build");
              section.reset();
              buildPopupPending = false;
              responsiveFontReflowPending = false;
              showBuildError();
              return;
            }
            if (responsiveFontReflowPending && !anchorJump && !offsetJump.has_value() &&
                !section->isBuildComplete() && static_cast<int>(section->pageCount) <= target) {
              // Preserve the old page number as the short-term target. renderBook()
              // returns now, so the main loop can process buttons before the next slice.
              section->currentPage = target;
              requestUpdate();
              return;
            }
'''
if rtext.count(old_build) != 1:
    raise SystemExit(f"initial foreground build block: expected 1, found {rtext.count(old_build)}")
rtext = rtext.replace(old_build, new_build, 1)

# The two later "current page not built yet" loops can otherwise reintroduce the
# same long blocking behavior on the next render. Slice those loops too.
old_late = '''      if (!section->buildSomeMore(BUILD_PAGES_PER_CHUNK)) {
        LOG_ERR("ERS", "Failed during incremental section build");
        section.reset();
        showBuildError();
        return;
      }
'''
new_late = '''      if (!section->buildSomeMore(responsiveFontReflowPending ? 1 : BUILD_PAGES_PER_CHUNK)) {
        LOG_ERR("ERS", "Failed during incremental section build");
        section.reset();
        responsiveFontReflowPending = false;
        showBuildError();
        return;
      }
      if (responsiveFontReflowPending && !section->isBuildComplete() &&
          section->currentPage >= static_cast<int>(section->pageCount)) {
        requestUpdate();
        return;
      }
'''
late_count = rtext.count(old_late)
if late_count != 2:
    raise SystemExit(f"late build loops: expected 2 matches, found {late_count}")
rtext = rtext.replace(old_late, new_late)

# As soon as the old page number exists, restore normal interactive rendering.
# The section may continue building in EpubReaderActivity::loop(), which already
# limits work to BACKGROUND_BUILD_PAGES_PER_TICK and suppresses idle prewarm while building.
old_apply = '''  applyDeferredReposition();

  renderer.clearScreen();
'''
new_apply = '''  applyDeferredReposition();

  if (responsiveFontReflowPending && section->pageCount > 0 &&
      section->currentPage < static_cast<int>(section->pageCount)) {
    responsiveFontReflowPending = false;
  }

  renderer.clearScreen();
'''
if rtext.count(old_apply) != 1:
    raise SystemExit(f"applyDeferredReposition marker: expected 1, found {rtext.count(old_apply)}")
rtext = rtext.replace(old_apply, new_apply, 1)

r.write_text(rtext, encoding="utf-8")
