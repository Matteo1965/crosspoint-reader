#!/usr/bin/env bash
set -euo pipefail

bash tools/build_cphun151_chapter_reindex_exp.sh
python3 tools/cphun152_hyphen_export_patch.py

python3 - <<'PY'
from pathlib import Path

def read(p): return Path(p).read_text(encoding="utf-8")
p = read("lib/Epub/Epub/ParsedText.cpp")
t = read("lib/Epub/Epub/blocks/TextBlock.cpp")
h = read("lib/Epub/Epub/ShortHyphenGlyph.h")
r = read("src/activities/reader/EpubReaderActivity.cpp")
rh = read("src/activities/reader/EpubReaderActivity.h")
assert h.count("getGlyph(0x2011") == 1
assert h.count("getGlyph(0x2010") == 1
assert 'return {"-", 0x002D};' in h
assert "short_hyphen::select(renderer, fontId, style).utf8" in p
assert 'ensureSdCardFontReady(fontId, "\\xE2\\x80\\x91\\xE2\\x80\\x90-", styleMask)' in p
assert "short_hyphen::select(renderer, fontId, style)" in t
assert "trailingShortHyphenInkShift(renderer, fontId, style, shortGlyph)" in t
assert "bool showExportSuccess = false;" in rh
assert "exportSuccessTime >= 2000UL" in r
assert 'GUI.drawPopup(renderer, "Sikeres exportálás.");' in r
assert "if (exportEditsTsv())" in r
assert "Fejezet újraindexelése" in read("src/activities/reader/EpubReaderMenuActivity.cpp")
assert "CPHUN-260925-152-EXP" in read("src/CPHUNBuildId.h")
print("CPHUN-152 glyph / export / chapter-reindex source checks passed")
PY

git diff --check
