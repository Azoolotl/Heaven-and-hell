#!/usr/bin/env python3
"""Bump the corrective Awakening build to 0.6.1-dev."""
import sys
from pathlib import Path

path = Path(sys.argv[1]) / "gradle.properties"
text = path.read_text(encoding="utf-8")
old = "mod_version=0.6.0-dev"
new = "mod_version=0.6.1-dev"
if old not in text:
    if new in text:
        print("Version already set to 0.6.1-dev")
        raise SystemExit(0)
    raise SystemExit("Expected mod_version=0.6.0-dev; refusing unexpected version bump")
path.write_text(text.replace(old, new, 1), encoding="utf-8")
print("Set mod_version=0.6.1-dev")
