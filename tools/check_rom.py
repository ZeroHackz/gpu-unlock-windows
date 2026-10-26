#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-only
"""Read-only check of a locally exported ROM; does not dump or flash hardware."""
import argparse,hashlib,json
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('rom',type=Path);a=p.parse_args();b=a.rom.read_bytes()
sha=hashlib.sha256(b).hexdigest();match=sha=='ebb63e82992d07e04da1e22ff78e855ce136c0702ee1909b2fb5d8c1e2f0674a'
print(json.dumps({'bytes':len(b),'sha256':sha,'matches_demonstrated_board_rom':match,'pci_rom_signature':b[:2].hex(),'view_sha256':hashlib.sha256(b[0x9400:0xe0000]).hexdigest() if len(b)>=0xe0000 else None},indent=2))
if not match:raise SystemExit('NOT MATCHED: the distributed EFI profile is not validated for this ROM. Do not bypass its identity/hash gates.')
