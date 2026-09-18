from pathlib import Path

p = Path("src/activities/reader/FootnotePopupActivity.cpp")
s = p.read_text(encoding="utf-8")

old = "constexpr int POPUP_HEIGHT = 530;"
new = "constexpr int POPUP_HEIGHT = 580;"
if s.count(old) != 1:
    raise SystemExit(f"CPHUN-140 popup height anchor count={s.count(old)}")
s = s.replace(old, new, 1)

old = '''  const int popupX = POPUP_SIDE_MARGIN;
  const int popupY = (screenH - popupH) / 2;
'''
new = '''  const int popupX = POPUP_SIDE_MARGIN;
  const int popupY = std::max(0, (screenH - popupH) / 2 - 30);
'''
if s.count(old) != 1:
    raise SystemExit(f"CPHUN-140 popup Y anchor count={s.count(old)}")
s = s.replace(old, new, 1)

p.write_text(s, encoding="utf-8")
print("CPHUN-140 applied: footnote popup 580 px and shifted 30 px upward")
