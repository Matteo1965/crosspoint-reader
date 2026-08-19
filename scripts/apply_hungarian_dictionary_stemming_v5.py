from pathlib import Path

path = Path("src/util/Dictionary.cpp")
text = path.read_text(encoding="utf-8")

anchor = '''  const auto stripSuffix = [](const std::string& s, const char* suffix, std::string& stem) {\n    const size_t len = strlen(suffix);\n    if (s.size() <= len || s.compare(s.size() - len, len, suffix) != 0) return false;\n    stem.assign(s, 0, s.size() - len);\n    return !stem.empty();\n  };\n'''

insert = r'''

  // Hungarian dictionary stemming v5: high-priority rules from real-book tests.
  // These intentionally run before the broad v3/v4 fallbacks so useful lemmas
  // cannot be crowded out by MAX_STEM_VARIANTS.

  const auto addCompoundTailsV5 = [&add](const std::string& form, size_t minCodepoints = 3) {
    size_t cpCount = 0;
    for (size_t i = 0; i < form.size(); ++i)
      if ((static_cast<unsigned char>(form[i]) & 0xC0) != 0x80) cpCount++;
    size_t seen = 0;
    for (size_t i = 0; i < form.size(); ++i) {
      if ((static_cast<unsigned char>(form[i]) & 0xC0) == 0x80) continue;
      const size_t remaining = cpCount - seen;
      if (seen > 0 && remaining >= minCodepoints) add(form.substr(i));
      seen++;
    }
  };

  const auto addVerbPrefixFallbackV5 = [&add](const std::string& form) {
    static constexpr const char* PREFIXES[] = {
        "vissza", "össze", "szét", "bele", "meg", "el", "ki", "be", "fel", "le", "át", "rá"};
    for (const char* prefix : PREFIXES) {
      const size_t len = strlen(prefix);
      if (form.size() > len && form.compare(0, len, prefix) == 0) add(form.substr(len));
    }
  };

  // Bare possessive forms: kabátja -> kabát; madárlába -> madárláb -> láb.
  for (const char* suffix : {"ja", "je", "a", "e"}) {
    std::string stem;
    if (stripSuffix(word, suffix, stem)) {
      add(stem);
      addCompoundTailsV5(stem);
    }
  }

  // Plural possessive: farktollai -> farktoll.
  for (const char* suffix : {"jai", "jei", "ai", "ei"}) {
    std::string stem;
    if (stripSuffix(word, suffix, stem)) {
      add(stem);
      addCompoundTailsV5(stem);
    }
  }

  // Possessor + accusative: segítségeteket -> segítség.
  for (const char* suffix : {"eteket", "atokat", "otokat", "ötöket"}) {
    std::string stem;
    if (stripSuffix(word, suffix, stem)) add(stem);
  }

  // Privative adjective + plural: arctalanok -> arc.
  for (const char* suffix : {"talanok", "telenek"}) {
    std::string stem;
    if (stripSuffix(word, suffix, stem)) add(stem);
  }

  // Subjunctive / imperative: cipeljen -> cipel.
  for (const char* suffix : {"jen", "jön"}) {
    std::string stem;
    if (stripSuffix(word, suffix, stem)) add(stem);
  }

  // Irregular linking vowel in compounds: hegyormok -> hegyorom.
  if (endsWith("ormok")) add(word.substr(0, n - strlen("ormok")) + "orom");

  // Compound nouns after a case suffix: sziklahasadékból -> hasadék;
  // tóparton -> part; kertkapun -> kertkapu/kapu.
  for (const char* suffix : {"ból", "ből", "ról", "ről", "tól", "től", "ban", "ben",
                              "on", "en", "ön", "n"}) {
    std::string stem;
    if (stripSuffix(word, suffix, stem)) {
      add(stem);
      addCompoundTailsV5(stem);
    }
  }

  // közepén -> közép.
  if (endsWith("epén")) add(word.substr(0, n - strlen("epén")) + "ép");

  // Prefix + adverbial participle: beleüvöltve -> üvölt.
  for (const char* suffix : {"va", "ve"}) {
    std::string stem;
    if (stripSuffix(word, suffix, stem)) {
      add(stem);
      addVerbPrefixFallbackV5(stem);
    }
  }

  // Past participle used adverbially: megkönnyebbülten -> megkönnyebbül.
  for (const char* suffix : {"tan", "ten"}) {
    std::string stem;
    if (stripSuffix(word, suffix, stem)) {
      add(stem);
      addVerbPrefixFallbackV5(stem);
    }
  }

  // Nominalization + possessive accusative: viszolygását -> viszolyog.
  for (const char* suffix : {"ását", "ését"}) {
    std::string stem;
    if (stripSuffix(word, suffix, stem)) {
      add(stem);
      if (!stem.empty() && stem.back() == 'g') {
        const std::string base = stem.substr(0, stem.size() - 1);
        add(base + "og");
        add(base + "eg");
        add(base + "ög");
      }
    }
  }

  // -val/-vel after plural: lényekkel -> lény; drágakövekkel -> drágakő.
  for (const char* suffix : {"kal", "kel"}) {
    std::string plural;
    if (!stripSuffix(word, suffix, plural)) continue;
    add(plural);
    for (const char* ps : {"ak", "ek", "ok", "ök"}) {
      std::string stem;
      if (!stripSuffix(plural, ps, stem)) continue;
      add(stem);
      // drágaköv -> drágakő
      if (stem.size() >= strlen("öv") && stem.compare(stem.size() - strlen("öv"), strlen("öv"), "öv") == 0)
        add(stem.substr(0, stem.size() - strlen("öv")) + "ő");
    }
  }

  // Derived abstract noun with instrumental: veszedelmességgel -> veszedelmes.
  for (const char* suffix : {"séggel", "sággal"}) {
    std::string stem;
    if (stripSuffix(word, suffix, stem)) add(stem);
  }

  // Compound quality noun: tompaagyúság -> tompaagy -> agy.
  for (const char* suffix : {"úság", "űség"}) {
    std::string stem;
    if (stripSuffix(word, suffix, stem)) {
      add(stem);
      addCompoundTailsV5(stem);
    }
  }

  // 2nd-person singular present: készülsz -> készül.
  {
    std::string stem;
    if (stripSuffix(word, "sz", stem)) add(stem);
  }

  // Subjunctive of esik: beleessen -> beleesik -> esik.
  if (endsWith("essen")) {
    std::string prefix = word.substr(0, n - strlen("essen"));
    add(prefix + "esik");
    add("esik");
  }

  // Comparative + translative: furcsábbá -> furcsa.
  for (const char* suffix : {"bbá", "bbé"}) {
    std::string stem;
    if (stripSuffix(word, suffix, stem)) {
      if (stem.size() >= strlen("á") && stem.compare(stem.size() - strlen("á"), strlen("á"), "á") == 0)
        add(stem.substr(0, stem.size() - strlen("á")) + "a");
      if (stem.size() >= strlen("é") && stem.compare(stem.size() - strlen("é"), strlen("é"), "é") == 0)
        add(stem.substr(0, stem.size() - strlen("é")) + "e");
      add(stem);
    }
  }

  // Adverb from -ős/-ós adjective: remegősen -> remeg.
  for (const char* suffix : {"ősen", "ósan"}) {
    std::string stem;
    if (stripSuffix(word, suffix, stem)) add(stem);
  }

  // Derived verb in past tense: függönyözött -> függöny.
  for (const char* suffix : {"özött", "ozott", "ezett"}) {
    std::string stem;
    if (stripSuffix(word, suffix, stem)) add(stem);
  }
'''

if "Hungarian dictionary stemming v5" not in text:
    if anchor not in text:
        raise SystemExit("v5 anchor not found")
    text = text.replace(anchor, anchor + insert, 1)

path.write_text(text, encoding="utf-8")

check = path.read_text(encoding="utf-8")
for marker in (
    "Hungarian dictionary stemming v5",
    "addCompoundTailsV5",
    "addVerbPrefixFallbackV5",
    '"eteket", "atokat"',
    '"talanok", "telenek"',
    'endsWith("ormok")',
    'endsWith("epén")',
    '"séggel", "sággal"',
    'endsWith("essen")',
    '"özött", "ozott", "ezett"',
):
    if marker not in check:
        raise SystemExit(f"Missing v5 marker: {marker}")

print("Hungarian dictionary stemming v5 applied")
