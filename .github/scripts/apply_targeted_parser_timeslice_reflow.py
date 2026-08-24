from pathlib import Path


def replace_once(path: str, old: str, new: str, label: str):
    p = Path(path)
    text = p.read_text(encoding="utf-8")
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{label}: expected exactly one match, found {count}")
    p.write_text(text.replace(old, new, 1), encoding="utf-8")


# -----------------------------------------------------------------------------
# 1) Section: add a target-aware, time-budgeted parser advance.
#    The normal buildSomeMore(N) yields only after N full pages, which is still too
#    coarse at small fonts: one 12pt page can contain enough text that a single tick
#    blocks input for a noticeable time. This helper yields after a short wall-clock
#    budget even if no whole page completed yet, while still preserving the canonical
#    full-section build from the beginning (no corrupt/mixed cache).
# -----------------------------------------------------------------------------
h = Path("lib/Epub/Epub/Section.h")
htext = h.read_text(encoding="utf-8")
old_h = '''  bool buildSomeMore(int maxPages);\n  bool isBuilding() const { return static_cast<bool>(build_); }\n'''
new_h = '''  bool buildSomeMore(int maxPages);\n  // Advance the active parser toward an exact visible-text offset for at most\n  // budgetMs. Unlike page-count pacing, this may yield between completed pages,\n  // which keeps font-size reflow responsive even when one small-font page is expensive.\n  bool buildTowardVisibleTextOffset(uint32_t offset, unsigned long budgetMs);\n  bool isBuilding() const { return static_cast<bool>(build_); }\n'''
if htext.count(old_h) != 1:
    raise SystemExit(f"Section.h buildSomeMore marker: expected 1, found {htext.count(old_h)}")
h.write_text(htext.replace(old_h, new_h, 1), encoding="utf-8")

cpp = Path("lib/Epub/Epub/Section.cpp")
ctext = cpp.read_text(encoding="utf-8")
marker = '''bool Section::hasHtmlCache() const {\n'''
method = '''bool Section::buildTowardVisibleTextOffset(const uint32_t offset, const unsigned long budgetMs) {\n  if (!build_ || !build_->parser) {\n    LOG_ERR("SCT", "buildTowardVisibleTextOffset with no active build");\n    return false;\n  }\n  if (buildReachedVisibleTextOffset(offset)) return true;\n\n  const unsigned long startMs = millis();\n  do {\n    const auto status = build_->parser->parseStep();\n    if (status == ChapterHtmlSlimParser::ParseStatus::Error) {\n      LOG_ERR("SCT", "Parse error during targeted reflow");\n      abandonBuild();\n      return false;\n    }\n    if (status == ChapterHtmlSlimParser::ParseStatus::Done) {\n      return finalizeBuild();\n    }\n    build_->bytesConsumed = build_->parser->parseBytesConsumed();\n    if (buildReachedVisibleTextOffset(offset)) return true;\n    // parseStep() consumes one small XML buffer. Yield on the first completed\n    // chunk after the budget so input can be serviced between parser chunks,\n    // not only between fully laid-out pages.\n  } while (budgetMs == 0 || millis() - startMs < budgetMs);\n\n  return true;\n}\n\n'''
if ctext.count(marker) != 1:
    raise SystemExit(f"Section.cpp hasHtmlCache marker: expected 1, found {ctext.count(marker)}")
cpp.write_text(ctext.replace(marker, method + marker, 1), encoding="utf-8")


# -----------------------------------------------------------------------------
# 2) Reader: during responsive font reflow, target the exact saved offset with a
#    short parser-time budget instead of waiting for one complete page per slice.
# -----------------------------------------------------------------------------
rh = Path("src/activities/reader/EpubReaderActivity.h")
rhtext = rh.read_text(encoding="utf-8")
old_const = '''  static constexpr int BACKGROUND_BUILD_PAGES_PER_TICK = 1;\n'''
new_const = '''  static constexpr int BACKGROUND_BUILD_PAGES_PER_TICK = 1;\n  // Parser-level budget for target-directed font reflow. A page can be expensive\n  // at 12/14pt, so yielding by time rather than page count is essential for input latency.\n  static constexpr unsigned long RESPONSIVE_REFLOW_PARSE_BUDGET_MS = 12;\n'''
if rhtext.count(old_const) != 1:
    raise SystemExit(f"reader header background pages marker: expected 1, found {rhtext.count(old_const)}")
rh.write_text(rhtext.replace(old_const, new_const, 1), encoding="utf-8")

r = Path("src/activities/reader/EpubReaderActivity.cpp")
rtext = r.read_text(encoding="utf-8")
old_build = '''            if (!section->buildSomeMore(responsiveFontReflowPending ? 1 : BUILD_PAGES_PER_CHUNK)) {\n              LOG_ERR("ERS", "Failed during incremental section build");\n              section.reset();\n              buildPopupPending = false;\n              responsiveFontReflowPending = false;\n              showBuildError();\n              return;\n            }\n'''
new_build = '''            const bool responsiveOffsetBuild = responsiveFontReflowPending && offsetJump.has_value();\n            const bool buildOk =\n                responsiveOffsetBuild\n                    ? section->buildTowardVisibleTextOffset(*offsetJump, RESPONSIVE_REFLOW_PARSE_BUDGET_MS)\n                    : section->buildSomeMore(responsiveFontReflowPending ? 1 : BUILD_PAGES_PER_CHUNK);\n            if (!buildOk) {\n              LOG_ERR("ERS", "Failed during incremental section build");\n              section.reset();\n              buildPopupPending = false;\n              responsiveFontReflowPending = false;\n              showBuildError();\n              return;\n            }\n'''
count = rtext.count(old_build)
if count != 1:
    raise SystemExit(f"reader foreground reflow build block: expected 1, found {count}")
rtext = rtext.replace(old_build, new_build, 1)

# The background loop still used page pacing even while the exact reflow target had
# not yet been reached. During the throttled font-reflow phase, advance by parser-time
# budget instead. After the target is found and responsiveFontReflowPending clears,
# the ordinary one-page/tick background builder resumes to finish the canonical cache.
old_bg = '''      if (!section->buildSomeMore(BACKGROUND_BUILD_PAGES_PER_TICK)) {\n        LOG_ERR("ERS", "Background section build failed");\n        section.reset();\n        requestUpdate();\n      } else if (section->isBuildComplete() && applyDeferredReposition()) {\n        requestUpdate();\n      }\n'''
new_bg = '''      const bool targetDirectedBackground =\n          responsiveFontReflowPending && cachedVisibleTextOffset.has_value() &&\n          !section->buildReachedVisibleTextOffset(*cachedVisibleTextOffset);\n      const bool backgroundBuildOk =\n          targetDirectedBackground\n              ? section->buildTowardVisibleTextOffset(*cachedVisibleTextOffset, RESPONSIVE_REFLOW_PARSE_BUDGET_MS)\n              : section->buildSomeMore(BACKGROUND_BUILD_PAGES_PER_TICK);\n      if (!backgroundBuildOk) {\n        LOG_ERR("ERS", "Background section build failed");\n        section.reset();\n        requestUpdate();\n      } else if (targetDirectedBackground && cachedVisibleTextOffset.has_value() &&\n                 section->buildReachedVisibleTextOffset(*cachedVisibleTextOffset)) {\n        if (const auto mappedPage = section->getPageForVisibleTextOffset(*cachedVisibleTextOffset)) {\n          section->currentPage = *mappedPage;\n          responsiveFontReflowPending = false;\n          requestUpdate();\n        }\n      } else if (section->isBuildComplete() && applyDeferredReposition()) {\n        requestUpdate();\n      }\n'''
count = rtext.count(old_bg)
if count != 1:
    raise SystemExit(f"reader background build block: expected 1, found {count}")
rtext = rtext.replace(old_bg, new_bg, 1)
r.write_text(rtext, encoding="utf-8")
