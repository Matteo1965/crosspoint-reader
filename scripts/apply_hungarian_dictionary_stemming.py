from pathlib import Path

path = Path("src/util/Dictionary.cpp")
text = path.read_text(encoding="utf-8")

start = text.index("void Dictionary::stemVariants(const std::string& word, std::vector<std::string>& out) {")
end = text.index("\nbool Dictionary::lookup(", start)

replacement = r'''void Dictionary::stemVariants(const std::string& word, std::vector<std::string>& out) {
  out.clear();
  out.reserve(64);
  const size_t n = word.size();
  constexpr size_t MAX_STEM_VARIANTS = 64;

  const auto add = [&out](std::string v) {
    if (v.size() < 2 || out.size() >= MAX_STEM_VARIANTS) return;
    if (std::find(out.begin(), out.end(), v) == out.end()) out.push_back(std::move(v));
  };

  const auto endsWith = [&word, n](const char* suffix) {
    const size_t len = strlen(suffix);
    return n > len && word.compare(n - len, len, suffix) == 0;
  };

  const auto stripSuffix = [](const std::string& s, const char* suffix, std::string& stem) {
    const size_t len = strlen(suffix);
    if (s.size() <= len || s.compare(s.size() - len, len, suffix) != 0) return false;
    stem.assign(s, 0, s.size() - len);
    return !stem.empty();
  };

  // Add common Hungarian stem restorations caused by suffixation.
  const auto addRestoredForms = [&add](const std::string& form) {
    add(form);

    // Possessive vowel lengthening before a case suffix: zsebébe/zsebéből -> zseb,
    // árnyékából -> árnyék.
    if (form.size() >= 2 && form.compare(form.size() - 2, 2, "á") == 0) {
      std::string v = form.substr(0, form.size() - 2);
      add(v + "a");
      add(v);
    }
    if (form.size() >= 2 && form.compare(form.size() - 2, 2, "é") == 0) {
      std::string v = form.substr(0, form.size() - 2);
      add(v + "e");
      add(v);
    }

    // Plural/oblique stem alternations: pálmafák -> pálmafa,
    // drágakövek... -> drágakő.
    if (form.size() >= 3 && form.compare(form.size() - 3, 3, "ák") == 0)
      add(form.substr(0, form.size() - 3) + "a");
    if (form.size() >= 3 && form.compare(form.size() - 3, 3, "ék") == 0)
      add(form.substr(0, form.size() - 3) + "e");
    if (form.size() >= 6 && form.compare(form.size() - 6, 6, "övek") == 0)
      add(form.substr(0, form.size() - 6) + "ő");
    if (form.size() >= 4 && form.compare(form.size() - 4, 4, "ovak") == 0)
      add(form.substr(0, form.size() - 4) + "ó");

    // Short-vowel lengthening in a few very common accusative stems:
    // utat -> út, kezet -> kéz. Candidate existence in the dictionary is still
    // required before it can win.
    if (form.size() >= 2) {
      const size_t p = form.size() - 2;
      const unsigned char c = static_cast<unsigned char>(form[p]);
      std::string v = form;
      if (c == 'a') { v.replace(p, 1, "á"); add(v); }
      if (c == 'e') { v.replace(p, 1, "é"); add(v); }
      if (c == 'i') { v.replace(p, 1, "í"); add(v); }
      if (c == 'o') { v.replace(p, 1, "ó"); add(v); }
      if (c == 'u') { v.replace(p, 1, "ú"); add(v); }
    }
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

  const auto addHungarianInnerForms = [&add, &stripSuffix, &addRestoredForms](const std::string& form) {
    for (const char* suffix : HU_INNER_SUFFIXES) {
      std::string stem;
      if (stripSuffix(form, suffix, stem)) addRestoredForms(stem);
    }
  };

  // Noun/adjective: stem + plural/possessive + case suffix.
  for (const char* suffix : HU_CASE_SUFFIXES) {
    std::string outerStem;
    if (!stripSuffix(word, suffix, outerStem)) continue;
    addRestoredForms(outerStem);
    addHungarianInnerForms(outerStem);
  }
  addHungarianInnerForms(word);

  // -val/-vel, including vowel-final possessive forms and consonant assimilation.
  // ollóval -> olló; ujjával -> ujj; szultánnal -> szultán;
  // mozdulattal -> mozdulat; drágakövekkel -> drágakő.
  for (const char* suffix : {"val", "vel", "ával", "ével"}) {
    std::string stem;
    if (stripSuffix(word, suffix, stem)) addRestoredForms(stem);
  }
  if (word.size() >= 4 &&
      (word.compare(word.size() - 2, 2, "al") == 0 || word.compare(word.size() - 2, 2, "el") == 0)) {
    const size_t c2 = word.size() - 3;
    const size_t c1 = word.size() - 4;
    if (static_cast<unsigned char>(word[c1]) < 0x80 && word[c1] == word[c2])
      addRestoredForms(word.substr(0, word.size() - 3));
  }

  // Possessive + accusative forms: monokliját -> monokli, könyvét -> könyv.
  for (const char* suffix : {"ját", "jét", "át", "ét"}) {
    std::string stem;
    if (stripSuffix(word, suffix, stem)) addRestoredForms(stem);
  }

  // Adverbs and comparative forms: óvatosan/nyájasan -> óvatos/nyájas;
  // közelebb -> közel.
  for (const char* suffix : {"an", "en", "abb", "ebb", "obb"}) {
    std::string stem;
    if (stripSuffix(word, suffix, stem)) addRestoredForms(stem);
  }

  // Infinitive: igazgatni -> igazgat.
  {
    std::string stem;
    if (stripSuffix(word, "ni", stem)) addRestoredForms(stem);
  }

  // Adverbial participle: csodálkozva -> csodálkoz -> csodálkozik,
  // gyanakodva -> gyanakod -> gyanakodik.
  for (const char* suffix : {"va", "ve"}) {
    std::string stem;
    if (stripSuffix(word, suffix, stem)) {
      add(stem + "ik");
      addRestoredForms(stem);
    }
  }

  // Present participle: kiáramló -> kiáramlik. Try the -ik dictionary form first.
  for (const char* suffix : {"ó", "ő"}) {
    std::string stem;
    if (stripSuffix(word, suffix, stem)) {
      add(stem + "ik");
      addRestoredForms(stem);
    }
  }

  // Common derivational noun suffixes: elterelés -> elterel.
  for (const char* suffix : {"ás", "és"}) {
    std::string stem;
    if (stripSuffix(word, suffix, stem)) addRestoredForms(stem);
  }

  // Common past-tense personal endings. Try an -ik lemma before the raw stem so
  // kártyázott -> kártyázik and halászták -> halászik, while vagdalták still
  // falls through to vagdal because vagdalik is not a dictionary headword.
  static constexpr const char* HU_PAST_SUFFIXES[] = {
      "ottam", "ettem", "öttem", "tam", "tem",
      "ottál", "ettél", "öttél", "tál", "tél",
      "ottunk", "ettünk", "öttünk", "tunk", "tünk",
      "ottatok", "ettetek", "öttetek", "tatok", "tetek",
      "ottak", "ettek", "öttek", "tak", "tek",
      "ták", "ték",
      "otta", "ette", "ötte", "ta", "te",
      "ott", "ett", "ött",
  };
  for (const char* suffix : HU_PAST_SUFFIXES) {
    std::string stem;
    if (stripSuffix(word, suffix, stem)) {
      add(stem + "ik");
      addRestoredForms(stem);
    }
  }

  // Possessive form with internal vowel shortening: fedele -> fedél.
  if (endsWith("ele")) add(word.substr(0, n - 3) + "él");

  // Negative/privative derivation fallback: láthatatlan -> lát.
  if (endsWith("hatatlan")) add(word.substr(0, n - strlen("hatatlan")));

  // Compound fallback, deliberately last: if the full compound is absent from
  // this dictionary, try UTF-8-safe suffix components of at least five codepoints
  // (e.g. atyavilág -> világ). Earlier morphology candidates always take priority.
  size_t cpCount = 0;
  for (size_t i = 0; i < word.size(); ++i)
    if ((static_cast<unsigned char>(word[i]) & 0xC0) != 0x80) cpCount++;
  if (cpCount >= 8) {
    size_t seen = 0;
    for (size_t i = 0; i < word.size() && out.size() < MAX_STEM_VARIANTS; ++i) {
      if ((static_cast<unsigned char>(word[i]) & 0xC0) == 0x80) continue;
      const size_t remaining = cpCount - seen;
      if (seen > 0 && remaining >= 5) add(word.substr(i));
      seen++;
    }
  }

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
for marker in (
    "HU_CASE_SUFFIXES",
    "HU_INNER_SUFFIXES",
    "HU_PAST_SUFFIXES",
    "MAX_STEM_VARIANTS = 64",
    "addRestoredForms",
    '"val", "vel", "ával", "ével"',
    '"an", "en", "abb", "ebb", "obb"',
    '"ták", "ték"',
    'endsWith("hatatlan")',
    "Compound fallback",
):
    if marker not in check:
        raise SystemExit(f"Missing marker after rewrite: {marker}")

print("Hungarian dictionary stemming v3 applied to src/util/Dictionary.cpp")
