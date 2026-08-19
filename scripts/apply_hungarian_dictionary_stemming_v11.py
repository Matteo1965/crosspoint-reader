from pathlib import Path

path = Path("src/util/Dictionary.cpp")
text = path.read_text(encoding="utf-8")

anchor = '''  std::transform(result.begin(), result.end(), result.begin(),
                 [](unsigned char c) { return c >= 0x80 ? c : static_cast<unsigned char>(std::tolower(c)); });
  return result;
'''

replacement = r'''  std::transform(result.begin(), result.end(), result.begin(),
                 [](unsigned char c) { return c >= 0x80 ? c : static_cast<unsigned char>(std::tolower(c)); });

  // Hungarian dictionary lookup v11: normalize decomposed Unicode sequences
  // commonly found in EPUB text to the precomposed UTF-8 forms normally used
  // by StarDict headwords. For example, visually identical "kabátja"
  // (a + U+0301) must compare equal to "kabátja" (U+00E1).
  struct HuComposePair {
    const char* decomposed;
    const char* composed;
  };
  static const HuComposePair HU_COMPOSE[] = {
      {"a\xCC\x81", "\xC3\xA1"},  // á
      {"e\xCC\x81", "\xC3\xA9"},  // é
      {"i\xCC\x81", "\xC3\xAD"},  // í
      {"o\xCC\x81", "\xC3\xB3"},  // ó
      {"u\xCC\x81", "\xC3\xBA"},  // ú
      {"o\xCC\x88", "\xC3\xB6"},  // ö
      {"u\xCC\x88", "\xC3\xBC"},  // ü
      {"o\xCC\x8B", "\xC5\x91"},  // ő
      {"u\xCC\x8B", "\xC5\xB1"},  // ű
  };
  for (const auto& p : HU_COMPOSE) {
    size_t pos = 0;
    const size_t fromLen = strlen(p.decomposed);
    const size_t toLen = strlen(p.composed);
    while ((pos = result.find(p.decomposed, pos)) != std::string::npos) {
      result.replace(pos, fromLen, p.composed);
      pos += toLen;
    }
  }

  return result;
'''

if "Hungarian dictionary lookup v11" not in text:
    if anchor not in text:
        raise SystemExit("v11 cleanWord anchor not found")
    text = text.replace(anchor, replacement, 1)

path.write_text(text, encoding="utf-8")

check = path.read_text(encoding="utf-8")
for marker in (
    "Hungarian dictionary lookup v11",
    "HU_COMPOSE",
    "HuComposePair",
):
    if marker not in check:
        raise SystemExit(f"Missing v11 marker: {marker}")

print("Hungarian dictionary Unicode normalization v11 applied")
