from pathlib import Path

patch = Path(__file__).with_name("cphun135r4b_edit_footnotes_keyboard_patch.py")
text = patch.read_text(encoding="utf-8")
old = '''    count = text.count(old)\n    if count != 1:\n        raise SystemExit(f"CPHUN-135r4b: {path}: expected one match, found {count}: {old[:180]!r}")\n    p.write_text(text.replace(old, new, 1), encoding="utf-8")'''
new = '''    count = text.count(old)\n    if count == 0 and new in text:\n        return\n    if count != 1:\n        raise SystemExit(f"CPHUN-135r4b: {path}: expected one match, found {count}: {old[:180]!r}")\n    p.write_text(text.replace(old, new, 1), encoding="utf-8")'''
if old not in text:
    raise SystemExit("CPHUN-135r4b driver: replace_once helper not found")
text = text.replace(old, new, 1)

# The exact <a href> parser context can differ slightly after earlier CPHUN
# patches. Replace the brittle exact-match block in the generated patch with a
# targeted regex substitution against the post-patch source instead.
frag_old = '''replace_once(\n    "lib/Epub/Epub/parsers/ChapterHtmlSlimParser.cpp",\n    \'\'\'      self->flushPartWordBuffer();\\n      self->nextWordContinues = true;\\n    }\\n    self->insideFootnoteLink = true;\'\'\',\n    \'\'\'      self->flushPartWordBuffer();\\n      // CPHUN-135r4b: a following noteref must not suppress hyphenation of\\n      // the lexical word immediately before the separate <a> node. The\\n      // noteref punctuation still receives zero-space attachment in ParsedText.\\n      self->nextWordContinues = false;\\n    }\\n    self->insideFootnoteLink = true;\'\'\',\n)'''
frag_new = '''p = Path("lib/Epub/Epub/parsers/ChapterHtmlSlimParser.cpp")\ns = p.read_text(encoding="utf-8")\nimport re\npat = re.compile(r'(if \\(self->partWordBufferIndex > 0\\) \\{\\n\\s*self->flushPartWordBuffer\\(\\);\\n)(?:\\s*self->nextWordContinues = true;\\n)(\\s*\\}\\n\\s*self->insideFootnoteLink = true;)')\ns2, n = pat.subn(r'\\1      // CPHUN-135r4b: a following noteref must not suppress hyphenation of\\n      // the lexical word immediately before the separate <a> node.\\n      self->nextWordContinues = false;\\n\\2', s, count=1)\nif n == 0 and "CPHUN-135r4b: a following noteref" not in s:\n    raise SystemExit("CPHUN-135r4b: footnote-link continuation block not found")\np.write_text(s2 if n else s, encoding="utf-8")'''
if frag_old not in text:
    raise SystemExit("CPHUN-135r4b driver: footnote parser patch block not found")
text = text.replace(frag_old, frag_new, 1)

# Earlier patches can reflow the EpubReaderMenuActivity constructor call. Match
# only the semantic boolean argument sequence instead of its indentation.
menu_old = '''replace_once(\n    "src/activities/reader/EpubReaderActivity.cpp",\n    \'\'\'                             SETTINGS.orientation, !currentPageFootnotes.empty(), !cachedBookmarks.empty(), startOnBookTab),\'\'\',\n    \'\'\'                             SETTINGS.orientation, !bookFootnotes.empty(), !cachedBookmarks.empty(), startOnBookTab),\'\'\',\n)'''
menu_new = '''replace_once(\n    "src/activities/reader/EpubReaderActivity.cpp",\n    "!currentPageFootnotes.empty(), !cachedBookmarks.empty(), startOnBookTab",\n    "!bookFootnotes.empty(), !cachedBookmarks.empty(), startOnBookTab",\n)'''
if menu_old not in text:
    raise SystemExit("CPHUN-135r4b driver: reader-menu footnote availability block not found")
text = text.replace(menu_old, menu_new, 1)

patch.write_text(text, encoding="utf-8")
exec(compile(text, str(patch), "exec"), {"__name__": "__main__", "__file__": str(patch)})
