# Hungarian Edition: materialize the pinned Hypher Hungarian trie before compilation.
# The binary is verified against its Git blob SHA-1 to prevent silent upstream changes.
Import("env")

from pathlib import Path
from urllib.request import urlopen
import hashlib
import subprocess
import sys

ROOT = Path(env["PROJECT_DIR"])
TARGET = ROOT / "lib/Epub/Epub/hyphenation/generated/hyph-hu.trie.h"
BINARY = ROOT / ".pio/hypher/hu.bin"
COMMIT = "d81cc506416bffef2a75ee2dc969d4b41bc36613"
BLOB_SHA = "9bb66be36b8fd7e600abd754d86231720a851e86"
URL = f"https://raw.githubusercontent.com/typst/hypher/{COMMIT}/tries/hu.bin"

if not TARGET.exists():
    BINARY.parent.mkdir(parents=True, exist_ok=True)
    if not BINARY.exists():
        print("HU-PICCO: retrieving pinned Hungarian Hypher trie...")
        with urlopen(URL, timeout=60) as response:
            data = response.read()
        actual = hashlib.sha1(b"blob " + str(len(data)).encode() + b"\\0" + data).hexdigest()
        if actual != BLOB_SHA:
            raise RuntimeError(f"Hungarian trie checksum mismatch: {actual}")
        BINARY.write_bytes(data)
    else:
        data = BINARY.read_bytes()
        actual = hashlib.sha1(b"blob " + str(len(data)).encode() + b"\\0" + data).hexdigest()
        if actual != BLOB_SHA:
            raise RuntimeError(f"Cached Hungarian trie checksum mismatch: {actual}")
    subprocess.run([
        sys.executable, str(ROOT / "scripts/generate_hyphenation_trie.py"),
        "--input", str(BINARY),
        "--output", str(TARGET),
    ], check=True)
