from pathlib import Path

# CPHUN-49 on top of CPHUN-48:
# Treat paragraph/mid-sentence en/em dashes that are glued to a word as surrounding
# punctuation for hyphenation analysis. The rendered source text stays untouched;
# only the processing copy passed to the language hyphenator is trimmed.

p = Path('lib/Epub/Epub/hyphenation/HyphenationCommon.cpp')
s = p.read_text(encoding='utf-8')

anchor = '''    case 0x00AB:  // «\n    case 0x00BB:  // »\n    case 0x2018:  // ‘\n'''
replacement = '''    case 0x00AB:  // «\n    case 0x00BB:  // »\n    // CPHUN-49: dialogue/narrative dashes may be glued directly to a word in EPUB source\n    // (e.g. U+2013 + "incselkedett"). Trim them only from the hyphenation processing copy.\n    case 0x2013:  // – en dash\n    case 0x2014:  // — em dash\n    case 0x2018:  // ‘\n'''

if anchor not in s:
    raise SystemExit('CPHUN-49 punctuation anchor missing')

s = s.replace(anchor, replacement, 1)
p.write_text(s, encoding='utf-8')
