from pathlib import Path

p = Path("src/activities/settings/CrossPointVersionActivity.cpp")
s = p.read_text(encoding="utf-8")

# Helper: derive the visible Hungarian Edition version from CPHUN_BUILD_ID.
# Example: CPHUN-260920-146-EXP -> Hungarian Edition v.146
anchor = '''constexpr int SIDE_PADDING = 20;

}  // namespace
'''
helper = '''constexpr int SIDE_PADDING = 20;

std::string hungarianEditionLabel() {
  const std::string buildId = CPHUN_BUILD_ID;
  const size_t firstDash = buildId.find('-');
  const size_t secondDash = firstDash == std::string::npos ? std::string::npos : buildId.find('-', firstDash + 1);
  const size_t thirdDash = secondDash == std::string::npos ? std::string::npos : buildId.find('-', secondDash + 1);

  if (secondDash == std::string::npos || thirdDash == std::string::npos || thirdDash <= secondDash + 1) {
    return "Hungarian Edition";
  }

  return "Hungarian Edition v." + buildId.substr(secondDash + 1, thirdDash - secondDash - 1);
}

}  // namespace
'''
if s.count(anchor) != 1:
    raise SystemExit(f"CPHUN-146 edition helper anchor matches={s.count(anchor)}")
s = s.replace(anchor, helper, 1)

old = '''    drawLabelValue(tr(STR_CROSSPOINT_VERSION), CROSSPOINT_VERSION);
    drawLabelValue(tr(STR_EDITION), "Hungarian Edition");
    drawWrapped(UI_12_FONT_ID, CPHUN_BUILD_ID);
'''
new = '''    drawLabelValue(tr(STR_CROSSPOINT_VERSION), CROSSPOINT_VERSION);
    const std::string editionLabel = hungarianEditionLabel();
    drawLabelValue(tr(STR_EDITION), editionLabel.c_str());
    drawWrapped(UI_12_FONT_ID, CPHUN_BUILD_ID);
'''
if s.count(old) != 1:
    raise SystemExit(f"CPHUN-146 edition line anchor matches={s.count(old)}")
s = s.replace(old, new, 1)

old_updates = '''    const char* updates[] = {
        hu ? "- Magyar billentyűzet" : "- Hungarian keyboard",
        hu ? "- Megjelölés és Szerkesztés mód" : "- Highlight and Edit modes",
        hu ? "- Mód választó: Szótár / Megjelölés / Szerkesztés" : "- Mode selector: Dictionary / Highlight / Edit",
        hu ? "- Szerkesztések exportálása TSV fájlba" : "- Export edits to TSV",
        hu ? "- Továbbfejlesztett lábjegyzet-kezelés" : "- Improved footnote handling",
        hu ? "- Több lábjegyzet kezelése és közvetlen megnyitása" : "- Multiple footnotes and direct opening",
        hu ? "- Alsó gombok: 1× / 2× / Hosszú nyomás" : "- Bottom buttons: 1× / 2× / Long press",
        hu ? "- Automatikus fejezetgenerálás" : "- Automatic chapter generation",
    };'''
new_updates = '''    const char* updates[] = {
        hu ? "- Magyar billentyűzet" : "- Hungarian keyboard",
        hu ? "- Megjelölés és Szerkesztés mód" : "- Highlight and Edit modes",
        hu ? "- Üzemmód választó gomb" : "- Mode selector button",
        hu ? "- Szerkesztések exportálása TSV fájlba" : "- Export edits to TSV",
        hu ? "- Továbbfejlesztett lábjegyzet-kezelés" : "- Improved footnote handling",
        hu ? "- Lábjegyzetek közvetlen megnyitása" : "- Direct footnote opening",
        hu ? "- Alsó gombok 1×/2×/Hosszú nyomás" : "- Bottom buttons 1×/2×/Long press",
        hu ? "- Automatikus fejezetgenerálás" : "- Automatic chapter generation",
    };'''
if s.count(old_updates) != 1:
    raise SystemExit(f"CPHUN-146 page 5 update block matches={s.count(old_updates)}")
s = s.replace(old_updates, new_updates, 1)

old_release = '''    const char* releaseUpdates[] = {
        hu ? "- Éjszakai mód" : "- Night Mode",
        hu ? "- Átlátszó alvóképernyők" : "- Transparent sleep screens",
        hu ? "- Továbbfejlesztett StarDict szótárkezelés" : "- Improved StarDict dictionary handling",
        hu ? "- Stabilitási és hibajavítások" : "- Stability and bug fixes",
    };'''
new_release = '''    const char* releaseUpdates[] = {
        hu ? "- Éjszakai mód" : "- Night Mode",
        hu ? "- Átlátszó alvóképernyők" : "- Transparent sleep screens",
        hu ? "- Jobb StarDict szótárkezelés" : "- Better StarDict dictionary handling",
        hu ? "- Stabilitási és hibajavítások" : "- Stability and bug fixes",
    };'''
if s.count(old_release) != 1:
    raise SystemExit(f"CPHUN-146 CrossPoint 1.6.0 block matches={s.count(old_release)}")
s = s.replace(old_release, new_release, 1)

p.write_text(s, encoding="utf-8")
print("CPHUN-146 applied: dynamic Hungarian Edition build version + revised page 5 text")
