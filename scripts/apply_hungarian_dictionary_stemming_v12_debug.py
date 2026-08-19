from pathlib import Path

path = Path("src/util/Dictionary.cpp")
text = path.read_text(encoding="utf-8")

anchor = '''  } else if (lookupWord == "igazgatónője") {
    // The current converted dictionary has igazgató but not igazgatónő.
    lookupWord = "igazgató";
  }
'''

insert = r'''

  // Hungarian dictionary lookup v12 diagnostic logging.
  // Temporary: print the raw input, cleaned/normalized form and exact UTF-8
  // bytes so EPUB selection/Unicode issues can be diagnosed without guessing.
  const auto huDebugHex = [](const char* s, char* out, size_t outSize) {
    if (!out || outSize == 0) return;
    out[0] = '\0';
    if (!s) return;
    size_t used = 0;
    for (const unsigned char* p = reinterpret_cast<const unsigned char*>(s); *p && used + 4 < outSize; ++p) {
      const int n = snprintf(out + used, outSize - used, "%s%02X", used ? " " : "", static_cast<unsigned>(*p));
      if (n <= 0 || static_cast<size_t>(n) >= outSize - used) break;
      used += static_cast<size_t>(n);
    }
  };
  char huRawHex[192];
  char huCleanHex[192];
  char huLookupHex[192];
  huDebugHex(word, huRawHex, sizeof(huRawHex));
  huDebugHex(cleaned.c_str(), huCleanHex, sizeof(huCleanHex));
  huDebugHex(lookupWord.c_str(), huLookupHex, sizeof(huLookupHex));
  LOG_INF("DICT", "HUDBG raw='%s' rawhex=[%s]", word ? word : "", huRawHex);
  LOG_INF("DICT", "HUDBG cleaned='%s' cleanhex=[%s] lookup='%s' lookuphex=[%s]",
          cleaned.c_str(), huCleanHex, lookupWord.c_str(), huLookupHex);
'''

if "Hungarian dictionary lookup v12 diagnostic" not in text:
    if anchor not in text:
        raise SystemExit("v12 diagnostic anchor not found")
    text = text.replace(anchor, anchor + insert, 1)

# Log the final matched headword immediately after the lookup session closes,
# before definition reading can change the observed outcome.
anchor2 = '''  if (!location.found) {
    // A search that never reached a verdict (couldn't open or seek .idx) is a
'''
insert2 = r'''  if (location.found) {
    LOG_INF("DICT", "HUDBG FOUND headword='%s' for raw='%s' cleaned='%s' lookup='%s'",
            matchedHeadwordOut.c_str(), word ? word : "", cleaned.c_str(), lookupWord.c_str());
  } else {
    LOG_INF("DICT", "HUDBG MISS raw='%s' cleaned='%s' lookup='%s'",
            word ? word : "", cleaned.c_str(), lookupWord.c_str());
  }

'''
if "HUDBG FOUND" not in text:
    if anchor2 not in text:
        raise SystemExit("v12 result anchor not found")
    text = text.replace(anchor2, insert2 + anchor2, 1)

path.write_text(text, encoding="utf-8")

check = path.read_text(encoding="utf-8")
for marker in (
    "Hungarian dictionary lookup v12 diagnostic",
    "HUDBG raw=",
    "HUDBG FOUND",
    "HUDBG MISS",
):
    if marker not in check:
        raise SystemExit(f"Missing v12 marker: {marker}")

print("Hungarian dictionary lookup v12 diagnostics applied")
