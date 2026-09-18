from pathlib import Path

# CPHUN-135r4k2f10
# Excel compatibility for TSV export:
# prepend UTF-8 BOM so Windows Excel detects UTF-8 automatically.

p = Path("src/activities/reader/EpubReaderActivity.cpp")
s = p.read_text(encoding="utf-8")

old = '''  const std::string header =
      "version\\tid\\ttype\\tbook_path\\tbook_file\\tbook_title\\tbook_author\\txhtml\\tspine\\tvisible_offset\\tlength\\t"
      "original\\treplacement\\tcontext_before\\tcontext_after\\n";
  bool ok = writeText(header);
'''
new = '''  // UTF-8 BOM: Windows Excel otherwise often opens a .tsv using the
  // current ANSI code page and displays Hungarian accented characters incorrectly.
  const uint8_t utf8Bom[] = {0xEF, 0xBB, 0xBF};
  bool ok = out.write(utf8Bom, sizeof(utf8Bom)) == static_cast<int>(sizeof(utf8Bom));

  const std::string header =
      "version\\tid\\ttype\\tbook_path\\tbook_file\\tbook_title\\tbook_author\\txhtml\\tspine\\tvisible_offset\\tlength\\t"
      "original\\treplacement\\tcontext_before\\tcontext_after\\n";
  if (ok) ok = writeText(header);
'''

if old not in s:
    raise SystemExit("R4K2F10: TSV header block not found")
s = s.replace(old, new, 1)

p.write_text(s, encoding="utf-8")
print("CPHUN-135r4k2f10 applied: UTF-8 BOM added to TSV export for Excel")
