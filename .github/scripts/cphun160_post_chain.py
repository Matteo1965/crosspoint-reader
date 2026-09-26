"""Reapply and verify isolated upstream #3527 font-cache fix after HU build regeneration.

The CPHUN-152 legacy patch chain regenerates Section.cpp. Keep its full
Hungarian chapter-layout behavior, and insert only the upstream cache release.
CPHUN-159 hidden-content cache invalidation runs before this script.
"""
from pathlib import Path

p = Path("lib/Epub/Epub/Section.cpp")
s = p.read_text(encoding="utf-8")
if "#include <FontCacheManager.h>" not in s:
    s = s.replace('#include "Section.h"\n', '#include "Section.h"\n\n#include <FontCacheManager.h>\n#include <GfxRenderer.h>\n', 1)
anchor = (
    '    LOG_ERR("SCT", "startBuild called while a build is already active");\n'
    "    return false;\n"
    "  }\n"
)
snippet = (
    "  // CPHUN-160: reclaim rebuildable SD glyph caches before chapter CSS/layout allocations.\n"
    "  // Keep loaded fonts and coverage data; page render can prewarm glyphs again.\n"
    "  if (auto* fontCache = renderer.getFontCacheManager()) {\n"
    "    fontCache->releaseSdFontCaches();\n"
    "  }\n"
)
if s.count(anchor) != 1:
    raise SystemExit("startBuild entry changed; cannot safely apply CPHUN-160")
start = s.index("bool Section::startBuild(")
end = s.find("buildComplete_ = false;", start)
if end < 0:
    raise SystemExit("startBuild allocation boundary missing")
entry = s[start:end]
if "fontCache->releaseSdFontCaches();" not in entry:
    s = s.replace(anchor, anchor + snippet, 1)
    entry = s[s.index("bool Section::startBuild("):s.index("buildComplete_ = false;", start)]
assert entry.index("releaseSdFontCaches()") < entry.index("buildComplete_") if "buildComplete_" in entry else True
if s.count("fontCache->releaseSdFontCaches();") != 1:
    raise SystemExit("Unexpected duplicate font cache release")
assert "#include <FontCacheManager.h>" in s and "#include <GfxRenderer.h>" in s
p.write_text(s, encoding="utf-8")
print("CPHUN-160: SD font caches released before chapter CSS/layout allocation")
