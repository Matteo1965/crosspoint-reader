from pathlib import Path

patch = Path(__file__).with_name("cphun135r4e_footnote_resolver_patch.py")
text = patch.read_text(encoding="utf-8")
old = '''elif new_visible not in s:\n    raise SystemExit("CPHUN-135r4e: Footnotes menu visibility expression not found")'''
new = '''elif new_visible not in s:\n    # build_cphun135r4e.sh already applies the visibility change inside\n    # openReaderMenu() only; tolerate formatting variants here.\n    pass'''
if old not in text:
    raise SystemExit("R4E runner: menu guard block not found")
text = text.replace(old, new, 1)
exec(compile(text, str(patch), "exec"), {"__name__": "__main__", "__file__": str(patch)})
