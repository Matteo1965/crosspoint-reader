#!/usr/bin/env bash
set -euo pipefail

bash tools/build_cphun135r4i.sh
python3 tools/cphun135r4j_footnote_chapter_patch.py

python3 - <<'PY'
from pathlib import Path
import re
bid = Path('src/CPHUNBuildId.h')
b = bid.read_text(encoding='utf-8')
b, n = re.subn(r'#define CPHUN_BUILD_ID "[^"]+"', '#define CPHUN_BUILD_ID "CPHUN-260917-135R4J-EXP"', b, count=1)
if n != 1:
    raise SystemExit('R4J build ID define not found')
bid.write_text(b, encoding='utf-8')
PY

git diff --check
grep -F 'CPHUN-260917-135R4J-EXP' src/CPHUNBuildId.h
grep -F 'preserve the href exactly as it appears' src/activities/reader/EpubReaderActivity.cpp
grep -F 'markerOnLine' lib/Epub/Epub/parsers/ChapterHtmlSlimParser.cpp
grep -F '__cphun_page_' src/activities/reader/EpubReaderActivity.cpp
grep -F '__cphun_page_' src/activities/reader/EpubReaderChapterSelectionActivity.cpp
grep -F 'VirtualChapter' src/activities/reader/EpubReaderChapterSelectionActivity.h

python3 - <<'PY'
from pathlib import Path
import re
reader = Path('src/activities/reader/EpubReaderActivity.cpp').read_text(encoding='utf-8')
parser = Path('lib/Epub/Epub/parsers/ChapterHtmlSlimParser.cpp').read_text(encoding='utf-8')
chapter_h = Path('src/activities/reader/EpubReaderChapterSelectionActivity.h').read_text(encoding='utf-8')
chapter_cpp = Path('src/activities/reader/EpubReaderChapterSelectionActivity.cpp').read_text(encoding='utf-8')
section = Path('lib/Epub/Epub/Section.cpp').read_text(encoding='utf-8')

# The R4I pre-normalizer must be gone: the R4E resolver owns relative-path resolution.
if 'href = item.href + href;' in reader:
    raise SystemExit('R4J: fragment href is still pre-normalized')
if "item.href.substr(0, slash + 1) + href" in reader:
    raise SystemExit('R4J: relative href is still pre-normalized')
if 'readItemContentsToStream(targetHref' not in reader:
    raise SystemExit('R4J: R4E target resolver missing')

# Current-spine safety stays bounded: never restore the whole-book loop.
fn_start = reader.find('void EpubReaderActivity::ensureBookFootnotes()')
fn_end = reader.find('std::string EpubReaderActivity::extractFootnoteText', fn_start)
fn = reader[fn_start:fn_end]
if 'for (int spine = 0;' in fn:
    raise SystemExit('R4J: unsafe whole-book footnote scan returned')
if 'getSpineItem(currentSpineIndex)' not in fn:
    raise SystemExit('R4J: current-spine footnote source missing')

# Visual marker ownership and safe virtual chapter boundaries must both be present.
if 'markerOnLine' not in parser or 'markerLike' not in parser:
    raise SystemExit('R4J: visible marker page ownership missing')
if 'getParagraphIndexForPage' not in reader or 'TARGET_PAGES = 12' not in reader:
    raise SystemExit('R4J: paragraph-safe virtual chapter splitting missing')
if 'virtualChapters' not in chapter_h or 'virtualIndexForRow' not in chapter_cpp:
    raise SystemExit('R4J: virtual chapter UI wiring missing')

m = re.search(r'constexpr uint8_t SECTION_FILE_VERSION = (\d+);', section)
if not m:
    raise SystemExit('R4J: section cache version missing')
print('R4J semantic verification passed; section cache version', m.group(1))
PY
