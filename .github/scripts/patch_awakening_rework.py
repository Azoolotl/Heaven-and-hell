#!/usr/bin/env python3
import base64
import gzip
from pathlib import Path

here = Path(__file__).resolve().parent
payload = here / "patch_payload" / "gameplay"
payload.mkdir(parents=True, exist_ok=True)

for filename, encoded_name in (
    ("AwakeningService.java", "awakening_service.java.gz.b64"),
    ("AwakenedAbilityService.java", "awakened_ability_service.java.gz.b64"),
):
    encoded = (here / encoded_name).read_bytes()
    (payload / filename).write_bytes(gzip.decompress(base64.b64decode(encoded)))

helper = gzip.decompress(
    base64.b64decode((here / "awakening_rework_impl.py.gz.b64").read_bytes())
).decode("utf-8")
exec(compile(helper, str(here / "awakening_rework_impl.py"), "exec"),
     {"__name__": "__main__", "__file__": str(here / "awakening_rework_impl.py")})
