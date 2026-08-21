from pathlib import Path
import re


def patch_sleep_brightness() -> None:
    path = Path("src/activities/boot_sleep/SleepActivity.cpp")
    text = path.read_text()

    text = text.replace('#include "HungarianEditionFeatures.h"\n', "")
    text = text.replace('#include "HungarianImageBrightness.h"\n', "")

    pattern = re.compile(
        r"\n\s*if \(!preserveBackground\) \{\s*"
        r"HungarianImageBrightness::apply\(renderer, 0, 0, pageWidth, pageHeight,\s*"
        r"HungarianEditionFeatures::brightnessPercentForCover\(\)\);\s*"
        r"\}\s*",
        re.MULTILINE,
    )
    text, count = pattern.subn("\n", text)

    if "HungarianImageBrightness::" in text or "HungarianEditionFeatures::brightnessPercentForCover" in text:
        raise SystemExit("leftover sleep brightness hook still present")

    path.write_text(text)
    print(f"Removed {count} leftover sleep brightness hook(s)")


patch_sleep_brightness()
