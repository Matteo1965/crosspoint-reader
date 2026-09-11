from pathlib import Path

activity_path = Path("src/activities/reader/EpubReaderActivity.cpp")
build_id_path = Path("src/CPHUNBuildId.h")

activity = activity_path.read_text()
old_callback = "[this](const ActivityResult&) { openReaderMenu(); });"
new_callback = "[this](const ActivityResult&) { openReaderMenu(true); });"

count = activity.count(old_callback)
if count != 2:
    raise SystemExit(f"Expected exactly 2 BookInfo return callbacks, found {count}")

activity = activity.replace(old_callback, new_callback)
activity_path.write_text(activity)

build_id = build_id_path.read_text()
old_id = '#define CPHUN_BUILD_ID "CPHUN-260911-96"'
new_id = '#define CPHUN_BUILD_ID "CPHUN-260911-97"'
if old_id not in build_id:
    raise SystemExit("Expected CPHUN-96 build id was not found")
build_id_path.write_text(build_id.replace(old_id, new_id, 1))

print("CPHUN-97: BookInfo returns to Reader Menu with the Book tab selected.")
