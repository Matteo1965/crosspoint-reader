from pathlib import Path

path = Path("lib/Epub/Epub/LetterSpacingOptimization.h")
text = path.read_text(encoding="utf-8")

old_step = "constexpr uint8_t STEP_FP4 = 4;"
new_step = "constexpr uint8_t STEP_FP4 = 8;"
old_max = "constexpr uint8_t MAX_EXTRA_PX_PER_LINE = 4;"
new_max = "constexpr uint8_t MAX_EXTRA_PX_PER_LINE = 8;"

if text.count(old_step) != 1:
    raise SystemExit(f"Expected exactly one STEP_FP4 match, found {text.count(old_step)}")
if text.count(old_max) != 1:
    raise SystemExit(f"Expected exactly one MAX_EXTRA_PX_PER_LINE match, found {text.count(old_max)}")

text = text.replace(old_step, new_step, 1)
text = text.replace(old_max, new_max, 1)
path.write_text(text, encoding="utf-8")
