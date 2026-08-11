from pathlib import Path

path = Path("src/util/Dictionary.cpp")
text = path.read_text(encoding="utf-8")

anchor = '''  // Possessive form with internal vowel shortening: fedele -> fedél.\n  if (endsWith("ele")) add(word.substr(0, n - 3) + "él");\n'''

insert = r'''

  // Hungarian dictionary stemming v4: targeted forms found during real-book testing.

  // Personal pronoun with dative suffix: nekem -> én.
  // Keep this explicit rather than treating every -em form as a pronoun.
  if (word == "nekem") add("én");
  if (word == "neked") add("te");
  if (word == "neki") add("ő");

  // Possessive + case suffix: kazánjából -> kazán.
  // The possessive vowel belongs to -ja/-je and disappears together with it.
  for (const char* suffix : {"jából", "jéből", "jába", "jébe", "járól", "jéről",
                              "ján", "jén", "jához", "jéhez", "jéhöz"}) {
    std::string stem;
    if (stripSuffix(word, suffix, stem)) addRestoredForms(stem);
  }

  // Bare 3rd-person possessive: kabátja -> kabát, könyve -> könyv.
  for (const char* suffix : {"ja", "je"}) {
    std::string stem;
    if (stripSuffix(word, suffix, stem)) addRestoredForms(stem);
  }

  // Plural possessed + accusative: széleit -> széle(i)t -> szél.
  // Common variants: -ait/-eit/-jait/-jeit.
  for (const char* suffix : {"jait", "jeit", "ait", "eit"}) {
    std::string stem;
    if (stripSuffix(word, suffix, stem)) {
      addRestoredForms(stem);
      // Restore final long vowel where suffixation shortened it: széleit -> szél.
      if (stem.size() >= 2 && stem.compare(stem.size() - 2, 2, "e") == 0)
        add(stem.substr(0, stem.size() - 1) + "é");
    }
  }
  // Direct common pattern for -leit: széleit -> szél.
  if (endsWith("leit")) add(word.substr(0, n - strlen("leit")) + "l");

  // -val/-vel assimilation after plural stems: drágakövekkel -> drágakő.
  // First remove assimilated -kal/-kel, then restore köve -> kő when applicable.
  for (const char* suffix : {"kal", "kel"}) {
    std::string stem;
    if (stripSuffix(word, suffix, stem)) {
      addRestoredForms(stem);
      if (stem.size() >= strlen("öve") && stem.compare(stem.size() - strlen("öve"), strlen("öve"), "öve") == 0)
        add(stem.substr(0, stem.size() - strlen("öve")) + "ő");
    }
  }
'''

if "Hungarian dictionary stemming v4" not in text:
    if anchor not in text:
        raise SystemExit("v3 anchor not found")
    text = text.replace(anchor, anchor + insert, 1)

path.write_text(text, encoding="utf-8")

check = path.read_text(encoding="utf-8")
for marker in (
    "Hungarian dictionary stemming v4",
    'word == "nekem"',
    '"jából", "jéből"',
    '"jait", "jeit", "ait", "eit"',
    '"kal", "kel"',
):
    if marker not in check:
        raise SystemExit(f"Missing v4 marker: {marker}")

print("Hungarian dictionary stemming v4 applied")
