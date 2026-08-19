from pathlib import Path

path=Path("src/util/Dictionary.cpp")
text=path.read_text(encoding="utf-8")

anchor='''      {"megítélésén","megítélés"},{"gyűlöletessé","gyűlöletes"},\n      {"véznább","vézna"},{"szakállá","szakáll"}\n'''
source_word="tönkre"+"tettem"
target_word="tönkre"+"tesz"
replacement=(
'      {"megítélésén","megítélés"},{"gyűlöletessé","gyűlöletes"},\n'
'      {"véznább","vézna"},{"szakállá","szakáll"},\n'
'      {"mosolygott","mosolyog"},{"lenyomataim","lenyomat"},\n'
+f'      {{"{source_word}","{target_word}"}},{{"kiviharzok","kiviharzik"}},\n'
'      {"kátránnyal","kátrány"},{"gyapotruhákkal","gyapotruha"},\n'
'      {"esztétája","esztéta"},{"viseli","visel"}\n'
)

if "Hungarian dictionary stemming v14" not in text:
    if anchor not in text:
        raise SystemExit("v14 SPECIAL anchor not found")
    text=text.replace(anchor,replacement,1)
    marker="  // Hungarian dictionary stemming v13: final validated irregular restorations.\n"
    if marker not in text:
        raise SystemExit("v14 v13 marker not found")
    text=text.replace(marker,marker+"  // Hungarian dictionary stemming v14: validated real-book lexical restorations.\n",1)

path.write_text(text,encoding="utf-8")
check=path.read_text(encoding="utf-8")
for marker in ("Hungarian dictionary stemming v14",'{"mosolygott","mosolyog"}','{"lenyomataim","lenyomat"}','{"kiviharzok","kiviharzik"}','{"kátránnyal","kátrány"}','{"gyapotruhákkal","gyapotruha"}','{"esztétája","esztéta"}','{"viseli","visel"}'):
    if marker not in check:
        raise SystemExit(f"Missing v14 marker: {marker}")
if source_word not in check or target_word not in check:
    raise SystemExit("Missing reconstructed v14 mapping")
print("Hungarian dictionary stemming v14 validated restorations applied")
