# Third-Party Notices

## Hungarian hyphenation patterns

This firmware includes a generated binary trie derived from the Hungarian
hyphenation patterns distributed by the `typst/hypher` project.

- Title: Hyphenation patterns for Hungarian
- Copyright: Copyright (C) 2003 Bence Nagy
- Original author: Bence Nagy
- Source: https://github.com/typst/hypher/blob/main/patterns/hyph-hu.tex
- Source-form license options: MPL 1.1, GPL 2.0, or LGPL 2.1
- License selected for this distribution: Mozilla Public License 1.1
- License text: https://www.mozilla.org/MPL/1.1/

The generated trie is stored at:

`lib/Epub/Epub/hyphenation/generated/hyph-hu.trie.h`

The script used to regenerate it is stored at:

`scripts/update_hyphenation.sh`

No warranty is provided for the Hungarian hyphenation patterns or the
generated trie.
