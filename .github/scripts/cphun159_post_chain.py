"""CPHUN-159 post-chain safety checks and chapter-cache invalidation.

Run after the legacy CPHUN-152 patch chain, which recreates many Hungarian
source changes, and after the CPHUN-157r1 chapter-position adapter.
"""
from pathlib import Path
import re

parser = Path("lib/Epub/Epub/parsers/ChapterHtmlSlimParser.cpp").read_text(encoding="utf-8")
resolver = Path("lib/KOReaderSync/ChapterXPathResolver.cpp").read_text(encoding="utf-8")
mapper = Path("lib/KOReaderSync/ProgressMapper.cpp").read_text(encoding="utf-8")
for filename, content, anchors in [
    ("EPUB hidden handling", parser, [
        'strcmp(atts[i], "hidden")',
        "cssStyle.display = CssDisplay::None;",
        "cssStyle.defined.display = 1;",
    ]),
    ("Precise KOReader XPath", resolver, [
        "findXPathForVisibleTextOffset(",
        "BoundaryMode::Inclusive",
        "XML_SetCommentHandler",
        "XML_SetProcessingInstructionHandler",
        "XML_SetCdataSectionHandler",
        "VisibleTextUtils::isNonVisibleElement",
    ]),
    ("KOReader upload mapping", mapper, [
        "if (pos.hasVisibleTextOffset)",
        "ChapterXPathResolver::findXPathForVisibleTextOffset(",
        "if (result.xpath.empty() && pos.hasParagraphIndex",
    ]),
]:
    for anchor in anchors:
        if anchor not in content:
            raise SystemExit(f"CPHUN-159 {filename} missing: {anchor}")

# Hidden HTML elements change the emitted pages; do not reuse older persisted
# pagination. Keep the Hungarian Edition's current cache version as the source
# of truth and advance it by one after the complete legacy feature chain.
file = Path("lib/Epub/Epub/Section.cpp")
source = file.read_text(encoding="utf-8")
if "CPHUN-159: HTML hidden attribute changes section layout." not in source:
    pattern = r"(?m)^(constexpr uint8_t SECTION_FILE_VERSION = )(\d+)(;.*)$"
    match = re.search(pattern, source)
    if not match:
        raise SystemExit("CPHUN-159 could not identify Section cache version")
    version = int(match.group(2))
    if version >= 220:
        raise SystemExit("CPHUN-159 section cache version out of safe range")
    source = source[:match.start()] + (
        "// CPHUN-159: HTML hidden attribute changes section layout.\n"
        + match.group(1) + str(version + 1) + match.group(3)
    ) + source[match.end():]
    file.write_text(source, encoding="utf-8")
    print(f"CPHUN-159 section cache version {version} -> {version+1}")
print("CPHUN-159 hidden EPUB, KOReader exact XPath and cache checks passed")
