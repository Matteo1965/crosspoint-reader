#!/usr/bin/env python3
"""CP-KOBO-032: offline static audit of FBInk source, no device I/O."""
from pathlib import Path
import json
import sys
root=Path(sys.argv[1])
out=Path(sys.argv[2])
hdr=(root/"fbink.h").read_text(errors="replace")
source=(root/"fbink.c").read_text(errors="replace")
device=(root/"fbink_device_id.h").read_text(errors="replace")
make=(root/"Makefile").read_text(errors="replace")
report={
 "source":str(root),
 "clara_bw_tpv_id_declared":"DEVICE_KOBO_CLARA_BW_TPV" in hdr,
 "clara_bw_id_declared":"DEVICE_KOBO_CLARA_BW" in hdr,
 "hwtcon_mentioned": "hwtcon" in source.lower() or "hwtcon" in device.lower(),
 "mtk_mentioned": "mtk" in source.lower() or "mtk" in device.lower(),
 "kobo_target_available":"FBINK_FOR_KOBO" in make,
 "supports_image_feature":"FBINK_WITH_IMAGE" in make,
 "status":"SOURCE_AUDIT_ONLY_NO_DEVICE_TEST",
}
out.parent.mkdir(parents=True,exist_ok=True)
out.write_text(json.dumps(report,indent=2)+"\n")
print(json.dumps(report,indent=2))
if not(report["clara_bw_tpv_id_declared"] and report["kobo_target_available"]):
 sys.exit(2)
