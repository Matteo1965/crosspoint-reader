from pathlib import Path

p = Path("lib/Epub/Epub/ParsedText.cpp")
text = p.read_text(encoding="utf-8")

old = '''    if (isParagraphFinalLexicalWord && needsHyphen) {
      bool hasLaterAutomaticBreak = false;
      for (const auto& later : breakInfos) {
        if (later.requiresInsertedHyphen && later.byteOffset > offset && later.byteOffset < word.size()) {
          hasLaterAutomaticBreak = true;
          break;
        }
      }
      if (!hasLaterAutomaticBreak) {
        continue;  // Would leave only the final hyphenation piece on the last line.
      }
    }
'''

new = '''    if (isParagraphFinalLexicalWord && needsHyphen) {
      // Protect only very short paragraph-final remainders. Count Unicode codepoints
      // in the lexical remainder, ignoring trailing punctuation tokens because they
      // are outside this word token. A remainder of 1-2 letters is rejected; 3+
      // letters is allowed (e.g. figyel-tem, kötő-dést, írás-szerű, meny-nyire).
      size_t remainderLetterCount = 0;
      const auto* remainderPtr = reinterpret_cast<const unsigned char*>(word.c_str() + offset);
      while (*remainderPtr) {
        const uint32_t cp = utf8NextCodepoint(&remainderPtr);
        if (isWordCharacter(cp)) {
          ++remainderLetterCount;
        }
      }
      if (remainderLetterCount <= 2) {
        continue;
      }
    }
'''

count = text.count(old)
if count != 1:
    raise SystemExit(f"paragraph-final old guard: expected 1 match, found {count}")
text = text.replace(old, new, 1)
p.write_text(text, encoding="utf-8")
