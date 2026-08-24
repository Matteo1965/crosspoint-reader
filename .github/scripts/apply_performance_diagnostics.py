from pathlib import Path


def replace_once(path: str, old: str, new: str, label: str):
    p = Path(path)
    text = p.read_text(encoding="utf-8")
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{label}: expected exactly one match, found {count}")
    p.write_text(text.replace(old, new, 1), encoding="utf-8")


# -----------------------------------------------------------------------------
# Header: add a compact diagnostic state. Results are buffered in RAM and written
# to /performance.log only after the measured input has already been handled.
# -----------------------------------------------------------------------------
h = Path("src/activities/reader/EpubReaderActivity.h")
htext = h.read_text(encoding="utf-8")
marker = '''  void showBuildPopup(GfxRenderer& renderer, int& pagesUntilFullRefresh);\n'''
insert = '''  struct PerformanceDiagnostic {\n    bool active = false;\n    bool logPending = false;\n    uint8_t fromPointSize = 0;\n    uint8_t toPointSize = 0;\n    unsigned long startAbsMs = 0;\n    unsigned long reflowReadyMs = 0;\n    unsigned long scanMs = 0;\n    unsigned long prewarmMs = 0;\n    unsigned long bwRenderMs = 0;\n    unsigned long displayMs = 0;\n    unsigned long renderTotalMs = 0;\n    unsigned long pageReadyMs = 0;\n    unsigned long firstInputMs = 0;\n    unsigned long handledMs = 0;\n    unsigned long handledAbsMs = 0;\n    char action[16] = {};\n  } perfDiag;\n  uint8_t perfLastFontPointSize = 0;\n  void perfStartFontChange(uint8_t fromPointSize, uint8_t toPointSize);\n  void perfMarkReflowReady();\n  void perfMarkRender(unsigned long scanMs, unsigned long prewarmMs, unsigned long bwRenderMs,\n                      unsigned long displayMs, unsigned long renderTotalMs);\n  void perfNoteInputSeen();\n  void perfFinishInput(const char* action);\n  void perfFlushLog();\n\n'''
if htext.count(marker) != 1:
    raise SystemExit(f"diagnostic header marker: expected 1, found {htext.count(marker)}")
h.write_text(htext.replace(marker, insert + marker, 1), encoding="utf-8")


# -----------------------------------------------------------------------------
# Reader implementation.
# -----------------------------------------------------------------------------
p = Path("src/activities/reader/EpubReaderActivity.cpp")
text = p.read_text(encoding="utf-8")

# Includes for append-only SD logging and snprintf/strncpy.
old_inc = '''#include <Memory.h>\n#include <esp_system.h>\n\n#include <algorithm>\n'''
new_inc = '''#include <Memory.h>\n#include <SDCardManager.h>\n#include <esp_system.h>\n\n#include <algorithm>\n#include <cstdio>\n#include <cstring>\n'''
if text.count(old_inc) != 1:
    raise SystemExit(f"diagnostic include marker: expected 1, found {text.count(old_inc)}")
text = text.replace(old_inc, new_inc, 1)

# Diagnostic methods. Logging is deliberately deferred until after the user action
# has already been timestamped, so SD latency cannot contaminate input latency.
marker_methods = '''EpubReaderActivity::~EpubReaderActivity() {\n'''
methods = r'''void EpubReaderActivity::perfFlushLog() {
  if (!perfDiag.logPending) return;

  char line[512];
  const unsigned long inputLatency =
      (perfDiag.firstInputMs > 0 && perfDiag.handledMs >= perfDiag.firstInputMs)
          ? perfDiag.handledMs - perfDiag.firstInputMs
          : 0;
  const int n = snprintf(
      line, sizeof(line),
      "font=%u->%u reflow=%lums scan=%lums prewarm=%lums bw_render=%lums display=%lums "
      "render_total=%lums page_ready=%lums input_seen=%lums input_handled=%lums input_latency=%lums action=%s\n",
      static_cast<unsigned>(perfDiag.fromPointSize), static_cast<unsigned>(perfDiag.toPointSize),
      perfDiag.reflowReadyMs, perfDiag.scanMs, perfDiag.prewarmMs, perfDiag.bwRenderMs, perfDiag.displayMs,
      perfDiag.renderTotalMs, perfDiag.pageReadyMs, perfDiag.firstInputMs, perfDiag.handledMs, inputLatency,
      perfDiag.action[0] ? perfDiag.action : "unknown");
  if (n > 0) {
    FsFile f = SdMan.open("/performance.log", O_WRONLY | O_CREAT | O_APPEND);
    if (f) {
      const size_t bytes = static_cast<size_t>(n < static_cast<int>(sizeof(line)) ? n : sizeof(line) - 1);
      f.write(reinterpret_cast<const uint8_t*>(line), bytes);
      f.flush();
      f.close();
    } else {
      LOG_ERR("PERF", "Could not open /performance.log");
    }
  }
  perfDiag.logPending = false;
}

void EpubReaderActivity::perfStartFontChange(const uint8_t fromPointSize, const uint8_t toPointSize) {
  if (perfDiag.logPending) perfFlushLog();
  perfDiag = PerformanceDiagnostic{};
  perfDiag.active = true;
  perfDiag.fromPointSize = fromPointSize;
  perfDiag.toPointSize = toPointSize;
  perfDiag.startAbsMs = millis();
  LOG_INF("PERF", "Font change %u -> %u", static_cast<unsigned>(fromPointSize), static_cast<unsigned>(toPointSize));
}

void EpubReaderActivity::perfMarkReflowReady() {
  if (!perfDiag.active || perfDiag.reflowReadyMs != 0) return;
  perfDiag.reflowReadyMs = millis() - perfDiag.startAbsMs;
}

void EpubReaderActivity::perfMarkRender(const unsigned long scanMs, const unsigned long prewarmMs,
                                        const unsigned long bwRenderMs, const unsigned long displayMs,
                                        const unsigned long renderTotalMs) {
  if (!perfDiag.active) return;
  perfDiag.scanMs = scanMs;
  perfDiag.prewarmMs = prewarmMs;
  perfDiag.bwRenderMs = bwRenderMs;
  perfDiag.displayMs = displayMs;
  perfDiag.renderTotalMs = renderTotalMs;
  perfDiag.pageReadyMs = millis() - perfDiag.startAbsMs;
}

void EpubReaderActivity::perfNoteInputSeen() {
  if (!perfDiag.active || perfDiag.pageReadyMs == 0 || perfDiag.firstInputMs != 0) return;
  perfDiag.firstInputMs = millis() - perfDiag.startAbsMs;
}

void EpubReaderActivity::perfFinishInput(const char* action) {
  if (!perfDiag.active || perfDiag.firstInputMs == 0 || perfDiag.handledMs != 0) return;
  perfDiag.handledMs = millis() - perfDiag.startAbsMs;
  perfDiag.handledAbsMs = millis();
  strncpy(perfDiag.action, action, sizeof(perfDiag.action) - 1);
  perfDiag.action[sizeof(perfDiag.action) - 1] = '\0';
  perfDiag.active = false;
  perfDiag.logPending = true;
}

'''
if text.count(marker_methods) != 1:
    raise SystemExit(f"diagnostic method marker: expected 1, found {text.count(marker_methods)}")
text = text.replace(marker_methods, methods + marker_methods, 1)

# Remember the current point size when a book opens, so the first menu-driven font
# change has a reliable 'from' value without changing TextSettingsActivity itself.
old_load_end = '''  loadCachedBookmarks();\n  return true;\n}\n\nvoid EpubReaderActivity::openReaderMenu() {\n'''
new_load_end = '''  perfLastFontPointSize = SETTINGS.fontPointSize;\n  loadCachedBookmarks();\n  return true;\n}\n\nvoid EpubReaderActivity::openReaderMenu() {\n'''
if text.count(old_load_end) != 1:
    raise SystemExit(f"loadBook diagnostic init marker: expected 1, found {text.count(old_load_end)}")
text = text.replace(old_load_end, new_load_end, 1)

# Mark a menu action as handled. This only fires for an active post-font-change
# diagnostic after a physical input edge has already been observed.
old_menu = '''void EpubReaderActivity::openReaderMenu() {\n  pendingManualTurn = 0;\n'''
new_menu = '''void EpubReaderActivity::openReaderMenu() {\n  perfFinishInput("menu");\n  pendingManualTurn = 0;\n'''
if text.count(old_menu) != 1:
    raise SystemExit(f"menu diagnostic marker: expected 1, found {text.count(old_menu)}")
text = text.replace(old_menu, new_menu, 1)

# Start measurement only for actual font-id changes. The prior typography patch
# creates this marker after comparing beforeSpec/afterSpec.
old_font_change = '''                                 responsiveFontReflowPending = beforeSpec.fontId != afterSpec.fontId;\n'''
new_font_change = '''                                 responsiveFontReflowPending = beforeSpec.fontId != afterSpec.fontId;\n                                 if (responsiveFontReflowPending) {\n                                   perfStartFontChange(perfLastFontPointSize, SETTINGS.fontPointSize);\n                                   perfLastFontPointSize = SETTINGS.fontPointSize;\n                                 }\n'''
if text.count(old_font_change) != 1:
    raise SystemExit(f"font-change diagnostic marker: expected 1, found {text.count(old_font_change)}")
text = text.replace(old_font_change, new_font_change, 1)

# At the top of the reader loop, sample the first physical edge after the newly
# rendered page is ready. wasAnyPressed/Released are non-consuming status queries.
old_loop = '''void EpubReaderActivity::loop() {\n  if (!epub) {\n    finish();\n    return;\n  }\n\n'''
new_loop = '''void EpubReaderActivity::loop() {\n  if (!epub) {\n    finish();\n    return;\n  }\n\n  if (perfDiag.logPending && perfDiag.handledAbsMs != 0 && millis() - perfDiag.handledAbsMs >= 1000) {\n    perfFlushLog();\n  }\n  if (perfDiag.active && perfDiag.pageReadyMs != 0 && perfDiag.firstInputMs == 0 &&\n      (mappedInput.wasAnyPressed() || mappedInput.wasAnyReleased())) {\n    perfNoteInputSeen();\n  }\n\n'''
if text.count(old_loop) != 1:
    raise SystemExit(f"loop diagnostic marker: expected 1, found {text.count(old_loop)}")
text = text.replace(old_loop, new_loop, 1)

# Page turn action handled timestamp.
old_page_turn = '''bool EpubReaderActivity::pageTurn(bool isForwardTurn) {\n  if (!section) return false;\n'''
new_page_turn = '''bool EpubReaderActivity::pageTurn(bool isForwardTurn) {\n  if (!section) return false;\n  perfFinishInput(isForwardTurn ? "page_next" : "page_prev");\n'''
if text.count(old_page_turn) != 1:
    raise SystemExit(f"page-turn diagnostic marker: expected 1, found {text.count(old_page_turn)}")
text = text.replace(old_page_turn, new_page_turn, 1)

# Split scan and prewarm. The existing timer called the combined stage 'prewarm'.
old_scan = '''  page->render(renderer, fontId, orientedMarginLeft, orientedMarginTop);\n  // Scan the status bar too: a CJK book/chapter title redirected to the SD\n  // fallback font joins the page's single batch prewarm instead of triggering\n  // its own SD pass after the scope ends.\n  renderStatusBar();\n  scope.endScanAndPrewarm();\n  const auto tPrewarm = millis();\n'''
new_scan = '''  page->render(renderer, fontId, orientedMarginLeft, orientedMarginTop);\n  // Scan the status bar too: a CJK book/chapter title redirected to the SD\n  // fallback font joins the page's single batch prewarm instead of triggering\n  // its own SD pass after the scope ends.\n  renderStatusBar();\n  const auto tScan = millis();\n  scope.endScanAndPrewarm();\n  const auto tPrewarm = millis();\n'''
if text.count(old_scan) != 1:
    raise SystemExit(f"scan/prewarm diagnostic marker: expected 1, found {text.count(old_scan)}")
text = text.replace(old_scan, new_scan, 1)

# The start of renderContents means target reflow has produced the page that can
# now be rendered. Record this before scan/prewarm begins.
old_render_start = '''  const auto t0 = millis();\n  const int fontId = SETTINGS.getReaderFontId();\n'''
new_render_start = '''  const auto t0 = millis();\n  perfMarkReflowReady();\n  const int fontId = SETTINGS.getReaderFontId();\n'''
# t0 marker appears only in renderContents in this file's current source.
if text.count(old_render_start) != 1:
    raise SystemExit(f"render start diagnostic marker: expected 1, found {text.count(old_render_start)}")
text = text.replace(old_render_start, new_render_start, 1)

# Capture the common metrics after every render path, including AA/grayscale work.
old_render_end = '''  }\n}\n\nvoid EpubReaderActivity::renderStatusBar() const {\n'''
new_render_end = '''  }\n\n  perfMarkRender(tScan - t0, tPrewarm - tScan, tBwRender - tPrewarm, tDisplay - tBwRender, millis() - t0);\n}\n\nvoid EpubReaderActivity::renderStatusBar() const {\n'''
if text.count(old_render_end) != 1:
    raise SystemExit(f"render end diagnostic marker: expected 1, found {text.count(old_render_end)}")
text = text.replace(old_render_end, new_render_end, 1)

p.write_text(text, encoding="utf-8")
