from pathlib import Path

# CPHUN-135r4k2f11
# Move "Szerkesztések exportálása" on Könyv tab:
# "Oldal QR-kódként" -> "Szerkesztések exportálása" -> "Olvasási pozíció szinkronja"

p = Path("src/activities/reader/EpubReaderMenuActivity.cpp")
s = p.read_text(encoding="utf-8")

export_row = '      {MenuAction::EXPORT_EDITS, StrId::STR_TEXT_SETTINGS, "Szerkesztések exportálása"},\n'
if s.count(export_row) != 1:
    raise SystemExit(f"R4K2F11: expected one EXPORT_EDITS row, found {s.count(export_row)}")

# Remove from its previous position.
s = s.replace(export_row, "", 1)

qr_row = '      {MenuAction::DISPLAY_QR, StrId::STR_DISPLAY_QR},\n'
sync_row = '      {MenuAction::SYNC, StrId::STR_SYNC_PROGRESS},\n'
if qr_row not in s or sync_row not in s:
    raise SystemExit("R4K2F11: QR or SYNC menu row not found")

# Insert directly after QR; SYNC must already follow QR in the Book menu.
qr_pos = s.find(qr_row)
sync_pos = s.find(sync_row, qr_pos)
if sync_pos < 0:
    raise SystemExit("R4K2F11: SYNC row not found after QR row")

s = s.replace(qr_row, qr_row + export_row, 1)

# Verify exact ordering within buildMoreItems.
start = s.find("std::vector<EpubReaderMenuActivity::MenuItem> EpubReaderMenuActivity::buildMoreItems")
end = s.find("const std::vector<EpubReaderMenuActivity::MenuItem>&", start)
book = s[start:end]
q = book.find("MenuAction::DISPLAY_QR")
e = book.find("MenuAction::EXPORT_EDITS")
y = book.find("MenuAction::SYNC")
if not (0 <= q < e < y):
    raise SystemExit("R4K2F11: requested QR -> EXPORT_EDITS -> SYNC ordering failed")

p.write_text(s, encoding="utf-8")
print("CPHUN-135r4k2f11 applied: export menu moved between QR and sync")
