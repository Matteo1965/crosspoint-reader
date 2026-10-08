#!/usr/bin/env python3
"""CP-KOBO-014: reproducible ARM migration inventory for the v224 source tree.

Classification by dependency hints, NOT proof of ARM compatibility.
Does not modify source or create an installable firmware.
"""
import argparse
import json
import re
from collections import Counter
from pathlib import Path

MARKERS = {
    "esp32_specific": re.compile(r"#\s*include\s*[<\"](?:esp_|driver/|freertos/|soc/|esp32|esp_system|nvs_flash)|\bESP\.|\besp_restart\s*\(", re.I),
    "arduino_api": re.compile(r"#\s*include\s*[<\"](?:Arduino\.h|SPI\.h|WiFi\.h|FS\.h|LittleFS\.h|SD\.h)|\b(?:millis|digitalWrite|pinMode)\s*\("),
    "hal_dependent": re.compile(r"#\s*include\s*[<\"](?:Hal[A-Za-z]+\.h|BoardConfig\.h|GfxRenderer\.h|MappedInputManager\.h)"),
    "simulator_guard": re.compile(r"#\s*(?:ifn?def|if|elif).*\bSIMULATOR\b"),
}
def inventory(root):
    rows=[]
    for directory in ("src","lib"):
        base=root/directory
        if not base.exists(): continue
        for file in sorted(base.rglob("*")):
            if not file.is_file() or file.suffix.lower() not in {".cpp",".cc",".c",".h",".hpp"}: continue
            try: text=file.read_text(encoding="utf-8",errors="replace")
            except OSError: continue
            hits={kind:len(regex.findall(text)) for kind,regex in MARKERS.items()}
            if any(hits.values()):
                rows.append({"path":str(file.relative_to(root)),"markers":{k:v for k,v in hits.items() if v}})
    counts=Counter()
    for row in rows:
        for kind in row["markers"]: counts[kind]+=1
    return {"scope":"src/ and lib/ in Hungarian Edition v224 branch",
            "interpretation":"heuristic dependency counts; no CrossPoint ARM build attempted or implied",
            "files_with_markers":len(rows),"categories":dict(sorted(counts.items())),"files":rows}

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--root",type=Path,default=Path("."))
    p.add_argument("--out",type=Path,required=True)
    args=p.parse_args()
    report=inventory(args.root)
    args.out.parent.mkdir(parents=True,exist_ok=True)
    args.out.write_text(json.dumps(report,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    print("CP-KOBO-014 inventory:",report["files_with_markers"],"files:",report["categories"])
    assert any(row["path"]=="src/main.cpp" for row in report["files"])

if __name__=="__main__":main()
