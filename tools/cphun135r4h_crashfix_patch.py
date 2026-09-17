from pathlib import Path

p = Path('src/activities/reader/EpubReaderActivity.cpp')
s = p.read_text(encoding='utf-8')

old_case = '''    case EpubReaderMenuActivity::MenuAction::FOOTNOTES: {
      ensureBookFootnotes();
      openFootnotesList(true, true);
      break;
    }'''
new_case = '''    case EpubReaderMenuActivity::MenuAction::FOOTNOTES: {
      // CPHUN-135r4h crash fix: never synchronously scan the whole EPUB from
      // the Reader menu. On X4, ensureBookFootnotes() can exhaust resources
      // while walking many spine items (reproduced with Michelangelo around
      // id_Footnote_132). Use only the already parsed current-page index here.
      openFootnotesList(false, true);
      break;
    }'''

if old_case in s:
    s = s.replace(old_case, new_case, 1)
elif new_case not in s:
    raise SystemExit('CPHUN-135r4h: FOOTNOTES menu action not found')

p.write_text(s, encoding='utf-8')
print('CPHUN-135r4h applied: removed synchronous whole-book footnote scan from Reader menu')
