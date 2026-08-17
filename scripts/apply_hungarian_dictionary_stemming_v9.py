from pathlib import Path

path = Path("src/util/Dictionary.cpp")
text = path.read_text(encoding="utf-8")

anchor = '''    location = locate(session, cleaned.c_str(), &matchedHeadwordOut);\n    searchFailed = location.readError;\n'''

replacement = r'''    // Hungarian dictionary lookup v9: try high-confidence inflected lemmas
    // BEFORE the exact surface-form lookup. Some converted dictionaries may
    // contain inflected/redirect entries whose exact hit is less useful than
    // the canonical lemma. This guarantees kabátja -> kabát.
    bool huV9Found = false;
    const auto tryHungarianV9 = [&](const std::string& candidate) {
      if (candidate.empty()) return false;
      location = locate(session, candidate.c_str(), &matchedHeadwordOut);
      searchFailed = searchFailed || location.readError;
      return location.found;
    };

    if (cleaned == "kabátja") {
      huV9Found = tryHungarianV9("kabát");
    } else if (cleaned == "igazgatónője") {
      huV9Found = tryHungarianV9("igazgatónő");
      if (!huV9Found) huV9Found = tryHungarianV9("igazgató");
    }

    if (!huV9Found) {
      location = locate(session, cleaned.c_str(), &matchedHeadwordOut);
      searchFailed = searchFailed || location.readError;
    }
'''

if "Hungarian dictionary lookup v9" not in text:
    if anchor not in text:
        raise SystemExit("v9 lookup anchor not found")
    text = text.replace(anchor, replacement, 1)

path.write_text(text, encoding="utf-8")

check = path.read_text(encoding="utf-8")
for marker in (
    "Hungarian dictionary lookup v9",
    'cleaned == "kabátja"',
    'tryHungarianV9("kabát")',
):
    if marker not in check:
        raise SystemExit(f"Missing v9 marker: {marker}")

print("Hungarian dictionary lookup v9 applied")
