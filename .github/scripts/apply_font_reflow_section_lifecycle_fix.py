from pathlib import Path

p = Path("src/activities/reader/EpubReaderActivity.cpp")
text = p.read_text(encoding="utf-8")

marker = "responsiveFontReflowPending = beforeSpec.fontId != afterSpec.fontId;"
pos = text.find(marker)
if pos < 0:
    raise SystemExit("font reflow activation marker not found")

reset_pos = text.find("section.reset();", pos)
if reset_pos < 0 or reset_pos - pos > 2200:
    raise SystemExit("font reflow section.reset marker not found in expected window")

replacement = '''if (responsiveFontReflowPending && section && section->isBuilding()) {
                                   // The in-progress layout belongs to the OLD font/render spec.
                                   // Persisting it as a partial cache during a font change is both
                                   // useless and unsafe: the next Section immediately rejects it as
                                   // parameter-mismatched, and the destructor-side suspend/commit
                                   // path can run while the reader is transitioning render state.
                                   // Abort it explicitly before destroying Section so no stale
                                   // old-font partial cache is committed.
                                   LOG_DBG("ERS", "Font reflow: abandoning old-spec active build before section reset");
                                   section->abandonBuild();
                                 }
                                 section.reset();'''

text = text[:reset_pos] + replacement + text[reset_pos + len("section.reset();"):]

# Guard against accidentally leaving the diagnostics-only SD logger in this source.
if "/performance.log" in text or "PerformanceDiagnostic" in text:
    raise SystemExit("diagnostic instrumentation unexpectedly present before lifecycle patch")

p.write_text(text, encoding="utf-8")
