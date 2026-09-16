from pathlib import Path
import runpy

p = Path('tools/cphun135_word_edit_markers_patch.py')
s = p.read_text(encoding='utf-8')

# Repair the accidental missing newline in the first patch revision.
bad_syntax = 's = p.read_text(encoding="utf-8")n = 0'
good_syntax = 's = p.read_text(encoding="utf-8")\nn = 0'
if bad_syntax in s:
    s = s.replace(bad_syntax, good_syntax, 1)

# CPHUN-135r1: the one-line page->render marker appears three times in
# renderContents (prewarm scan, optional image placeholder path, final BW
# render). Anchor the edit-background insertion to the final BW block only.
old = '''insert_before(
    "src/activities/reader/EpubReaderActivity.cpp",
    "  page->render(renderer, fontId, orientedMarginLeft, orientedMarginTop);\\n",
    ''' + "'''" + '''  if (textEditStore) {
    TextEditRenderer::renderBackground(renderer, *page, fontId, orientedMarginLeft, orientedMarginTop,
                                       currentSpineIndex, *textEditStore);
  }
''' + "'''" + ''',
)
'''
new = '''replace_once(
    "src/activities/reader/EpubReaderActivity.cpp",
    "  page->render(renderer, fontId, orientedMarginLeft, orientedMarginTop);\\n"
    "  renderStatusBar();\\n"
    "  const auto tBwRender = millis();\\n",
    ''' + "'''" + '''  if (textEditStore) {
    TextEditRenderer::renderBackground(renderer, *page, fontId, orientedMarginLeft, orientedMarginTop,
                                       currentSpineIndex, *textEditStore);
  }
  page->render(renderer, fontId, orientedMarginLeft, orientedMarginTop);
  renderStatusBar();
  const auto tBwRender = millis();
''' + "'''" + ''',
)
'''
if old not in s:
    raise SystemExit('CPHUN-135r1: generic render insertion block not found in patch source')
s = s.replace(old, new, 1)

fixed = Path('/tmp/cphun135_word_edit_markers_patch_fixed.py')
fixed.write_text(s, encoding='utf-8')
compile(s, str(fixed), 'exec')
runpy.run_path(str(fixed), run_name='__main__')
