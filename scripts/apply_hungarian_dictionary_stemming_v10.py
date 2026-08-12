from pathlib import Path

path = Path("src/util/Dictionary.cpp")
text = path.read_text(encoding="utf-8")

anchor = '''  const std::string cleaned = cleanWord(word);\n  if (cleaned.empty() || !isOpen()) return false;\n'''
replacement = r'''  const std::string cleaned = cleanWord(word);
  if (cleaned.empty() || !isOpen()) return false;

  // Hungarian dictionary lookup v10: canonicalize a few high-confidence
  // surface forms before *any* dictionary lookup logic runs. Unlike the v8/v9
  // probe approach, every subsequent exact/preferred/stemming path sees the
  // canonical lemma itself.
  std::string lookupWord = cleaned;
  if (lookupWord == "kabátja") {
    lookupWord = "kabát";
  } else if (lookupWord == "igazgatónője") {
    // The current converted dictionary has igazgató but not igazgatónő.
    lookupWord = "igazgató";
  }
'''

if "Hungarian dictionary lookup v10" not in text:
    if anchor not in text:
        raise SystemExit("v10 clean-word anchor not found")
    text = text.replace(anchor, replacement, 1)

# From this point in lookup(), force all lookup machinery to operate on lookupWord.
lookup_start = text.find("bool Dictionary::lookup(")
if lookup_start < 0:
    raise SystemExit("lookup() not found")
lookup_tail = text[lookup_start:]
lookup_tail = lookup_tail.replace("cleaned.c_str()", "lookupWord.c_str()")
lookup_tail = lookup_tail.replace("stemVariants(cleaned, variants)", "stemVariants(lookupWord, variants)")
# v8/v9 comparisons are left intact intentionally; for canonicalized forms they
# simply won't match, while normal words retain their existing behavior.
text = text[:lookup_start] + lookup_tail

path.write_text(text, encoding="utf-8")

check = path.read_text(encoding="utf-8")
for marker in (
    "Hungarian dictionary lookup v10",
    'lookupWord == "kabátja"',
    'lookupWord = "kabát"',
    "locate(session, lookupWord.c_str()",
    "stemVariants(lookupWord, variants)",
):
    if marker not in check:
        raise SystemExit(f"Missing v10 marker: {marker}")

print("Hungarian dictionary lookup v10 applied")
