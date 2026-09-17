from pathlib import Path

# CPHUN-135r4b driver v2
#
# The previous driver removed the Reader-menu availability replacement with a
# DOTALL regex beginning at the first EpubReaderActivity.cpp replace_once().
# That regex was too broad: it could delete the intervening point 4/5 editing
# changes and dictionary-name truncation from the generated feature patch.
# Keep the proven memory-fix driver, but replace only that unsafe source-text
# rewrite before executing it.

driver = Path(__file__).with_name("cphun135r4b_patch_driver.py")
text = driver.read_text(encoding="utf-8")

old_block = '''# Do not change the reader-menu availability boolean here. More importantly,
# never build the whole-book footnote index merely to open the Reader menu.
# The index is built lazily only after the user selects Lábjegyzetek.
menu_block = re.compile(
    r'replace_once\\(\\n\\s*"src/activities/reader/EpubReaderActivity\\.cpp",\\n'
    r'.*?!currentPageFootnotes\\.empty\\(\\).*?!bookFootnotes\\.empty\\(\\).*?\\n\\)\\n', re.S)
text, n_menu = menu_block.subn('', text, count=1)
if n_menu != 1:
    raise SystemExit("CPHUN-135r4b driver: reader-menu availability patch block not found")
'''

new_block = '''# Remove only the exact Reader-menu availability mutation from the generated
# feature patch. Do not use a DOTALL expression beginning at an earlier
# EpubReaderActivity.cpp replacement: that would erase unrelated point 4/5 and
# dictionary patches as collateral damage.
availability_patch = """replace_once(
    \"src/activities/reader/EpubReaderActivity.cpp\",
    '''                             SETTINGS.orientation, !currentPageFootnotes.empty(), !cachedBookmarks.empty(), startOnBookTab),''',
    '''                             SETTINGS.orientation, !bookFootnotes.empty(), !cachedBookmarks.empty(), startOnBookTab),''',
)
"""
if availability_patch not in text:
    raise SystemExit("CPHUN-135r4b driver: exact reader-menu availability patch block not found")
text = text.replace(availability_patch, "", 1)
'''

if old_block not in text:
    raise SystemExit("CPHUN-135r4b driver v2: unsafe menu-block rewrite not found")
text = text.replace(old_block, new_block, 1)

exec(compile(text, str(driver), "exec"), {"__name__": "__main__", "__file__": str(driver)})
