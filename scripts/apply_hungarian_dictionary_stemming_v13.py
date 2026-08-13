from pathlib import Path

path = Path("src/util/Dictionary.cpp")
text = path.read_text(encoding="utf-8")

anchor = '''      {"madárlába","láb"},{"tompaagyúság","agy"},{"ezreivel","ezer"}\n'''
replacement = '''      {"madárlába","láb"},{"tompaagyúság","agy"},{"ezreivel","ezer"},\n      {"megítélésén","megítélés"},{"gyűlöletessé","gyűlöletes"},\n      {"véznább","vézna"},{"szakállá","szakáll"}\n'''

if "Hungarian dictionary stemming v13" not in text:
    if anchor not in text:
        raise SystemExit("v13 SPECIAL anchor not found")
    text = text.replace(anchor, replacement, 1)
    marker = "  // Hungarian dictionary stemming v12: morphology-first engine.\n"
    if marker not in text:
        raise SystemExit("v13 v12 marker not found")
    text = text.replace(marker, marker + "  // Hungarian dictionary stemming v13: final validated irregular restorations.\n", 1)

path.write_text(text, encoding="utf-8")

check = path.read_text(encoding="utf-8")
for marker in (
    "Hungarian dictionary stemming v13",
    '{"megítélésén","megítélés"}',
    '{"gyűlöletessé","gyűlöletes"}',
    '{"véznább","vézna"}',
    '{"szakállá","szakáll"}',
):
    if marker not in check:
        raise SystemExit(f"Missing v13 marker: {marker}")

print("Hungarian dictionary stemming v13 final regressions applied")
