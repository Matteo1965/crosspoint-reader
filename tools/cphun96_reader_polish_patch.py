from pathlib import Path


# CPHUN-96 is already integrated on this branch.  The original integration
# script remains available in the branch history; on re-runs we only verify
# that the expected integrated source is present and leave it untouched.
build_id = Path("src/CPHUNBuildId.h").read_text()
book_info = Path("src/activities/reader/BookInfoActivity.cpp").read_text()
reader_menu = Path("src/activities/reader/EpubReaderMenuActivity.cpp").read_text()

required = [
    ("CPHUN-260911-96" in build_id, "CPHUN-96 build id is missing"),
    ('mappedInput.mapLabels("Vissza"' in book_info, "BookInfo footer compile fix is missing"),
    ('breakOffsetsForLanguageExtended(token, false, "hu")' in book_info, "Hungarian BookInfo hyphenation is missing"),
    ('Borító megjelenítése' in reader_menu, "CPHUN-96 reader-menu changes are missing"),
]

for ok, message in required:
    if not ok:
        raise SystemExit(message)

print("CPHUN-96 source is already integrated; no patching required.")
