#!/usr/bin/env python3
"""Create an original Hungarian multi-page EPUB for Kobo simulator QA."""
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED, ZIP_STORED
from xml.sax.saxutils import escape

out = Path("fs_/books/CP-KOBO-004-magyar-teszt.epub")
out.parent.mkdir(parents=True, exist_ok=True)
paragraphs = [
    "Az olvasó délután egy különösen hosszú, összetett magyar szöveget választott, hogy ellenőrizze az elválasztás és a lapozás működését.",
    "Az árvíztűrő tükörfúrógép kifejezés sokféle ékezetet tartalmaz. A szövegben előfordul még: őszülő, gyönyörűség, összehasonlíthatatlanság és megkülönböztethetetlenség.",
    "A következő oldalon újabb bekezdések jelennek meg. A cél az érintőképernyős lapozás ellenőrzése, nem pedig a sebesség mérésének pontosítása.",
    "Az olvasási folyamat akkor megfelelő, ha a program megnyitja a könyvet, megjeleníti a magyar karaktereket, és a következő oldalra tud lépni.",
]
files = {
    "META-INF/container.xml": """<?xml version="1.0" encoding="UTF-8"?>
<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container"><rootfiles><rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/></rootfiles></container>""",
}
manifest = []
spine = []
nav = []
for c in range(1, 4):
    name = f"chapter{c}.xhtml"
    body = "".join(f"<p>{escape(paragraphs[(i+c)%len(paragraphs)])} ({c}/{i+1})</p>" for i in range(60))
    files[f"OEBPS/{name}"] = (f'<?xml version="1.0" encoding="UTF-8"?>'
      f'<html xmlns="http://www.w3.org/1999/xhtml" xml:lang="hu"><head><title>Fejezet {c}</title></head>'
      f'<body><h1>{c}. fejezet</h1>{body}</body></html>')
    manifest.append(f'<item id="c{c}" href="{name}" media-type="application/xhtml+xml"/>')
    spine.append(f'<itemref idref="c{c}"/>')
    nav.append(f'<navPoint id="n{c}" playOrder="{c}"><navLabel><text>{c}. fejezet</text></navLabel><content src="{name}"/></navPoint>')
files["OEBPS/content.opf"] = ('''<?xml version="1.0" encoding="UTF-8"?>
<package xmlns="http://www.idpf.org/2007/opf" unique-identifier="bookid" version="2.0">
<metadata xmlns:dc="http://purl.org/dc/elements/1.1/">
<dc:identifier id="bookid">urn:uuid:3ac29b19-5f38-4bd8-8d17-8c00acb4d004</dc:identifier>
<dc:title>Magyar lapozási teszt</dc:title><dc:creator>CrossPoint QA</dc:creator>
<dc:language>hu</dc:language></metadata>
<manifest>''' + "".join(manifest) + '''<item id="ncx" href="toc.ncx" media-type="application/x-dtbncx+xml"/></manifest>
<spine toc="ncx">''' + "".join(spine) + '''</spine></package>''')
files["OEBPS/toc.ncx"] = ('''<?xml version="1.0" encoding="UTF-8"?>
<ncx xmlns="http://www.daisy.org/z3986/2005/ncx/" version="2005-1"><head><meta name="dtb:uid" content="urn:uuid:3ac29b19-5f38-4bd8-8d17-8c00acb4d004"/></head><docTitle><text>Magyar lapozási teszt</text></docTitle><navMap>''' + "".join(nav) + '''</navMap></ncx>''')
with ZipFile(out, "w") as z:
    z.writestr("mimetype", "application/epub+zip", compress_type=ZIP_STORED)
    for key, value in files.items():
        z.writestr(key, value.encode("utf-8"), compress_type=ZIP_DEFLATED)
print(f"Created {out} ({out.stat().st_size} bytes)")
