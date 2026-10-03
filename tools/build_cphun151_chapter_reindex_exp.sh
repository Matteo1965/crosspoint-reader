#!/usr/bin/env bash
set -euo pipefail

# Retain CPHUN-150's no-op menu-return checks and the previous build chain.
bash tools/build_cphun150_cache_resume_exp.sh
python3 tools/cphun151_chapter_reindex_patch.py

python3 - <<'PY'
from pathlib import Path
menu_h = Path("src/activities/reader/EpubReaderMenuActivity.h").read_text(encoding="utf-8")
menu_cpp = Path("src/activities/reader/EpubReaderMenuActivity.cpp").read_text(encoding="utf-8")
reader_h = Path("src/activities/reader/EpubReaderActivity.h").read_text(encoding="utf-8")
reader_cpp = Path("src/activities/reader/EpubReaderActivity.cpp").read_text(encoding="utf-8")
section = Path("lib/Epub/Epub/Section.cpp").read_text(encoding="utf-8")
assert "REINDEX_CHAPTER," in menu_h
book = menu_cpp[menu_cpp.index("EpubReaderMenuActivity::buildMoreItems()"):]
assert book.index("MenuAction::REINDEX_CHAPTER") > book.index("MenuAction::DELETE_CACHE")
assert "Fejezet újraindexelése" in book
assert "bool forceChapterReindex = false" in reader_h
assert "section->abandonBuild();" in reader_cpp
assert "cleared = section->clearCache();" in reader_cpp
assert "forceChapterReindex = true" in reader_cpp
assert "const bool needsFullBuild = pendingPercentJump || forceChapterReindex;" in reader_cpp
assert "forceChapterReindex = false;" in reader_cpp
assert "rememberCurrentContentOffset();" in reader_cpp
assert "offsetJump.has_value()" in reader_cpp
assert "Section::~Section() { suspendBuild(); }" in section
assert "bool Section::clearCache() const" in section
print("CPHUN-151 static chapter-reindex checks passed")
PY

git diff --check
