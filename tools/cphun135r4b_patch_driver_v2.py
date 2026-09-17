from pathlib import Path
import re
import runpy

# Compatibility entry point for the CPHUN-135r4b build workflow.
# The actual feature/memory patching lives in cphun135r4b_patch_driver.py.
driver = Path(__file__).with_name("cphun135r4b_patch_driver.py")
runpy.run_path(str(driver), run_name="__main__")

# CPHUN-135r4b crash guard:
# Opening the Reader menu must never trigger whole-book footnote indexing.
# Keep ensureBookFootnotes() lazy and reachable only from the FOOTNOTES action.
reader = Path("src/activities/reader/EpubReaderActivity.cpp")
s = reader.read_text(encoding="utf-8")

open_menu = re.compile(
    r'(void EpubReaderActivity::openReaderMenu\(const bool startOnBookTab\)\s*\{\s*'
    r'pendingManualTurn\s*=\s*0\s*;)\s*ensureBookFootnotes\(\)\s*;',
    re.S,
)
s, n = open_menu.subn(r'\1', s, count=1)
if n != 1:
    raise SystemExit(
        f"CPHUN-135r4b: expected one eager ensureBookFootnotes() call in openReaderMenu, found {n}"
    )

# Verify specifically inside openReaderMenu(), while allowing the intended lazy
# call in the FOOTNOTES menu action elsewhere in the file.
menu_body = re.search(
    r'void EpubReaderActivity::openReaderMenu\(const bool startOnBookTab\)\s*\{(.*?)\n\}',
    s,
    re.S,
)
if not menu_body:
    raise SystemExit("CPHUN-135r4b: openReaderMenu() body not found after patching")
if "ensureBookFootnotes();" in menu_body.group(1):
    raise SystemExit("CPHUN-135r4b: eager footnote indexing still present in openReaderMenu()")

reader.write_text(s, encoding="utf-8")
print("CPHUN-135r4b Reader-menu guard applied: footnote indexing remains lazy")
