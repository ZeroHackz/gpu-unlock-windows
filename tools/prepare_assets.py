#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-only
"""Locally fetch hash-pinned stock inputs and populate USB; never upload outputs."""
import json,subprocess,sys
from pathlib import Path
r=Path(__file__).resolve().parents[1];f=r/'src/firmware-tools';cache=r/'local/cache';out=r/'src/USB/RTX4080-EXPERIMENT/ASSETS'
m=json.loads((f/'artifacts-610.43.03.json').read_text());entries=m['source_artifacts']
if sys.version_info<(3,14):raise SystemExit('Use Python 3.14+ for upstream tar.zst extraction. Your benchmark Python environment can remain unchanged.')
def run(*a):subprocess.run([sys.executable,*map(str,a)],check=True)
run(f/'fetch_artifacts.py',cache)
run(f/'generate_v67.py',cache/entries[2]['filename'],out)
run(f/'extract_boot_assets.py',cache/entries[0]['filename'],out,'--arch','ad102','--gsp',out/'gsp_ga10x.bin')
(out/'v67-ga102-610.43.03.bin').unlink(missing_ok=True)
# The four-PLM payload is a fixed byte layout; ad102_payload.main() also needs an
# envydis listing for its audit, so write payload() directly. The manifest hash
# check below still pins the exact bytes.
sys.path.insert(0,str(f));from ad102_payload import payload
(out/'v67-ad102-610.43.03-four-plm.bin').write_bytes(payload())
import hashlib
spec=json.loads((r/'ASSETS-MANIFEST.json').read_text())
for name,entry in spec.items():
 if isinstance(entry,dict) and 'sha256' in entry and 'bytes' in entry:
  b=(out/name).read_bytes()
  assert len(b)==entry['bytes'] and hashlib.sha256(b).hexdigest()==entry['sha256'],name
print('Local stock assets ready. Keep them out of public uploads.')
