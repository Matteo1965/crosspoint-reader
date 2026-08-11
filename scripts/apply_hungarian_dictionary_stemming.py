from pathlib import Path

path = Path("src/util/Dictionary.cpp")
text = path.read_text(encoding="utf-8")

start = text.index("void Dictionary::stemVariants(const std::string& word, std::vector<std::string>& out) {")
end = text.index("\nbool Dictionary::lookup(", start)

replacement = r'''void Dictionary::stemVariants(const std::string& word, std::vector<std::string>& out) {
  out.clear();
  out.reserve(24);
  const size_t n = word.size();
  constexpr size_t MAX_STEM_VARIANTS = 24;

  const auto add = [&out](std::string v) {
    if (v.size() < 2 || out.size() >= MAX_STEM_VARIANTS) return;
    if (std::find(out.begin(), out.end(), v) == out.end()) out.push_back(std::move(v));
  };

  const auto endsWith = [&word, n](const char* suffix) {
    const size_t len = strlen(suffix);
    return n > len && word.compare(n - len, len, suffix) == 0;
  };

  static constexpr const char* HU_CASE_SUFFIXES[] = {
      "képpen", "ként",
      "ból", "ből", "tól", "től", "ról", "ről",
      "hoz", "hez", "höz", "nál", "nél",
      "ban", "ben", "nak", "nek", "ért",
      "ba", "be", "ra", "re", "on", "en", "ön",
      "ig", "kor", "ul", "ül", "vá", "vé",
      "at", "et", "ot", "öt", "t",
  };

  static constexpr const char* HU_INNER_SUFFIXES[] = {
      "atok", "etek", "otok", "ötök",
      "unk", "ünk",
      "am", "em", "om", "öm",
      "ad", "ed", "od", "öd",
      "ja", "je", "uk", "ük", "juk", "jük",
      "ak", "ek", "ok", "ök", "k",
      "a", "e",
  };

  const auto stripSuffix = [](const std::string& s, const char* suffix, std::string& stem) {
    const size_t len = strlen(suffix);
    if (s.size() <= len || s.compare(s.size() - len, len, suffix) != 0) return false;
    stem.assign(s, 0, s.size() - len);
    return !stem.empty();
  };

  const auto addHungarianInnerForms = [&add, &stripSuffix](const std::string& form) {
    for (const char* suffix : HU_INNER_SUFFIXES) {
      std::string stem;
      if (stripSuffix(form, suffix, stem)) add(std::move(stem));
    }
  };

  for (const char* suffix : HU_CASE_SUFFIXES) {
    std::string outerStem;
    if (!stripSuffix(word, suffix, outerStem)) continue;
    add(outerStem);
    addHungarianInnerForms(outerStem);
  }

  addHungarianInnerForms(word);

  if (endsWith("'s")) add(word.substr(0, n - 2));
  if (endsWith("\\xE2\\x80\\x99s")) add(word.substr(0, n - 4));
  if (endsWith("ies")) add(word.substr(0, n - 3) + "y");
  if (endsWith("es")) add(word.substr(0, n - 2));
  if (endsWith("s")) add(word.substr(0, n - 1));
  if (endsWith("ed")) {
    add(word.substr(0, n - 2));
    add(word.substr(0, n - 1));
    if (n >= 4 && word[n - 3] == word[n - 4]) add(word.substr(0, n - 3));
  }
  if (endsWith("ing")) {
    add(word.substr(0, n - 3));
    add(word.substr(0, n - 3) + "e");
    if (n >= 5 && word[n - 4] == word[n - 5]) add(word.substr(0, n - 4));
  }
}
'''

updated = text[:start] + replacement + text[end:]
path.write_text(updated, encoding="utf-8")

check = path.read_text(encoding="utf-8")
for marker in ("HU_CASE_SUFFIXES", "HU_INNER_SUFFIXES", "MAX_STEM_VARIANTS"):
    if marker not in check:
        raise SystemExit(f"Missing marker after rewrite: {marker}")

print("Hungarian dictionary stemming applied to src/util/Dictionary.cpp")
