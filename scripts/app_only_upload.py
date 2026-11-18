# Upload only the application image, at the ota_0 offset taken from the
# partition table. For boards that keep their vendor bootloader, partition
# table, otadata and recovery partition (Onyx Picco): pio's default upload
# would also write the Arduino bootloader, partition table and boot_app0.bin.
Import("env")

# The builder has already copied each extra image to UPLOADERFLAGS as
# "<offset> <path>" pairs. Clearing FLASH_EXTRA_IMAGES alone is too late.
extra = {(str(offset), env.subst(path)) for offset, path in env.get("FLASH_EXTRA_IMAGES", [])}
flags = list(env.get("UPLOADERFLAGS", []))
kept = []
removed = set()
i = 0
while i < len(flags):
    pair = (str(flags[i]), env.subst(flags[i + 1])) if i + 1 < len(flags) else None
    if pair in extra:
        removed.add(pair)
        i += 2
        continue
    kept.append(flags[i])
    i += 1

# Fail closed: an extra image left in the upload could overwrite vendor partitions.
missing = extra - removed
if missing:
    raise RuntimeError(f"app_only_upload: extra images still in UPLOADERFLAGS: {sorted(missing)}")

env.Replace(FLASH_EXTRA_IMAGES=[], UPLOADERFLAGS=kept)
