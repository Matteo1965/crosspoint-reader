from pathlib import Path

path = Path("lib/Epub/Epub/ParsedText.cpp")
text = path.read_text(encoding="utf-8")

old = '''  const int punctuationAdvance =
      cachedHangingPunctuationAdvance(renderer, fontId, style, punctuation, word.c_str() + lastStart);
  const int proportionalAdvance = (punctuationAdvance * std::min<int>(percentStep, 4) + 3) / 4;
  return std::min<int>(pixelLimit, proportionalAdvance);
'''

new = '''  const int punctuationAdvance =
      cachedHangingPunctuationAdvance(renderer, fontId, style, punctuation, word.c_str() + lastStart);

  // Character-specific optical-margin ratios. The packed percentage still acts as the
  // on/off gate, while the configured pixel limit remains the hard maximum overhang.
  // Inserted/explicit hyphen: 50%; question/exclamation: 10%; other supported marks: 25%.
  int hangingPercent = 25;
  if (punctuation == '-') {
    hangingPercent = 50;
  } else if (punctuation == '?' || punctuation == '!') {
    hangingPercent = 10;
  }
  const int proportionalAdvance = (punctuationAdvance * hangingPercent + 99) / 100;
  return std::min<int>(pixelLimit, proportionalAdvance);
'''

count = text.count(old)
if count != 1:
    raise SystemExit(f"ParsedText.cpp: expected one hanging allowance block, found {count}")

path.write_text(text.replace(old, new, 1), encoding="utf-8")
