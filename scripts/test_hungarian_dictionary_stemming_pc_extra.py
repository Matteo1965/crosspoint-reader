#!/usr/bin/env python3
"""Extra regression cases layered on the main Hungarian stemming PC test.

This keeps the core test harness stable while adding newly reported real-book
forms. Run exactly like the main test:

    python scripts/test_hungarian_dictionary_stemming_pc_extra.py path/to/dictionary.idx
"""

import test_hungarian_dictionary_stemming_pc as base

EXTRA_TESTS = {
    "kikérdezésen": "kikérdez",
    "szakembereken": "szakember",
    "emlékeznek-e": "emlékezik",
    "mentorok": "mentor",
}

_base_transforms = base.transforms


def transforms(word):
    """Add high-confidence rules needed by the new regression cases."""
    out = []
    seen = set()

    def add(candidate, rule):
        candidate = base.norm(candidate)
        if candidate and candidate != word and candidate not in seen:
            seen.add(candidate)
            out.append((candidate, rule))

    # Hungarian interrogative particle: emlékeznek-e -> emlékeznek.
    # Handle both ASCII hyphen and common Unicode dash/hyphen variants.
    for suffix in ("-e", "‐e", "‑e", "–e"):
        if word.endswith(suffix) and len(word) > len(suffix):
            add(word[:-len(suffix)], "interrogative -e")

    # Present-tense 3rd person plural of many -ik verbs:
    # emlékeznek -> emlékezik. The candidate still has to exist as a StarDict
    # headword, so noun datives ending in -nek do not win unless stem+ik exists.
    if word.endswith("nek") and len(word) > 3:
        add(word[:-3] + "ik", "verb -nek→-ik")

    for candidate, rule in _base_transforms(word):
        if candidate not in seen:
            seen.add(candidate)
            out.append((candidate, rule))
    return out


base.transforms = transforms
base.TESTS.update(EXTRA_TESTS)

if __name__ == "__main__":
    base.main()
