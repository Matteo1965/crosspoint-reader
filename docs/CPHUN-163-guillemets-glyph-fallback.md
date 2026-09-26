# CPHUN-163: dictionary quotation marks and EPUB missing glyphs

Base: device-tested CPHUN-162, preserving all CPHUN-157r1/159/160/161/162 fixes.

## Dictionary
Dictionary::cleanWord strips edge U+00AB and U+00BB guillemets, like its existing curly-quote and terminal punctuation behavior. The Beatles passage `»tisztelni«,` now looks up `tisztelni`. Interior characters and source EPUB text are untouched.

## Reader font fallback
Reader-only, per-character decision, identical during width measurement and draw:
1. If the selected font contains the original Unicode codepoint, keep it.
2. If U+2212 (mathematical minus) is missing and the selected font has U+2013, display the font's own en dash. This addresses the provided dialogue passage rendered in Bitter.
3. Otherwise choose the closest loaded Noto Serif (12, 14, 16, 18 pt) face that contains the original codepoint. Keep the original Unicode text, maintain the paragraph baseline, and do not kern across two different font families.
4. When Noto Serif also lacks it, retain the existing replacement glyph.

The fallback is activated when opening an EPUB and disabled when that reader is destroyed. Dictionary-specific fallback remains independent. The visible pagination cache is invalidated (CPHUN-159 version +1), including partial section caches, because actual fallback advances may change line wrapping.

## Validation
New native unit tests cover guillemets, curly quotes, internal punctuation, preservation of native U+2212, and native U+2013 substitution. CI retains previous HU regression suites, ensures legacy patch regeneration preserved the source changes, checks untouched USB/hardware button source, and builds X4 release firmware.

## Device acceptance
Check the Beatles `»tisztelni«,` word selection and lookup; verify the three U+2212 signs in the reported Bitter novel page appear as the Bitter en dash; verify a second font with native minus retains its own minus; try a non-punctuation glyph absent from another font and compare with Noto Serif. Confirm several pages of sorkizárás, optical margins, dialogue spacing, hyphenation, KOReader sync, SD font lapozás and hardware buttons. CI success does not replace X4 device testing.
