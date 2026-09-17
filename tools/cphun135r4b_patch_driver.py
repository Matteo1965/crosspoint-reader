from pathlib import Path

patch = Path(__file__).with_name("cphun135r4b_edit_footnotes_keyboard_patch.py")
text = patch.read_text(encoding="utf-8")
old = '''    count = text.count(old)\n    if count != 1:\n        raise SystemExit(f"CPHUN-135r4b: {path}: expected one match, found {count}: {old[:180]!r}")\n    p.write_text(text.replace(old, new, 1), encoding="utf-8")'''
new = '''    count = text.count(old)\n    if count == 0 and new in text:\n        return\n    if count != 1:\n        raise SystemExit(f"CPHUN-135r4b: {path}: expected one match, found {count}: {old[:180]!r}")\n    p.write_text(text.replace(old, new, 1), encoding="utf-8")'''
if old not in text:
    raise SystemExit("CPHUN-135r4b driver: replace_once helper not found")
text = text.replace(old, new, 1)
patch.write_text(text, encoding="utf-8")
exec(compile(text, str(patch), "exec"), {"__name__": "__main__", "__file__": str(patch)})
