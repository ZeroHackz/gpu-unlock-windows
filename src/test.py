#!/usr/bin/env python3
import argparse,subprocess,json,os,hashlib
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--rom',required=True);p.add_argument('--prom',required=True);p.add_argument('--group',choices=['all','core','app'],default='all');a=p.parse_args();rom=str(Path(a.rom).resolve());prom=str(Path(a.prom).resolve())
full=Path(rom).read_bytes();live=Path(prom).read_bytes()
assert len(full)==2048000 and len(live)==1048576
assert hashlib.sha256(full).hexdigest()=='ebb63e82992d07e04da1e22ff78e855ce136c0702ee1909b2fb5d8c1e2f0674a'
assert hashlib.sha256(live).hexdigest()=='43240cdcb3d883b84b8d78292a0bd3e61529a7543e4288a701331133ebc83d6a'
assert live[:0xd6c00]==full[0x9400:0xe0000]
print('RUN04 captured PROM and original ROM view match byte-for-byte; actual PROM used as MMIO fixture.',flush=True)
r=Path(__file__).resolve().parent;os.chdir(r);Path('test-build').mkdir(exist_ok=True)
core=['port','compat','vendor/unlock_610','vendor/prep_610','vendor/layout_610','vendor/vbios_610','vendor/gfw_eval']
flags=['gcc','-std=c11','-fshort-wchar','-O1','-Wall','-Wextra','-Wno-unused-parameter','-Wno-misleading-indentation','-Wno-format','-D__KERNEL__','-DGU_UEFI_PORT','-DGU_TARGET_PCI_ID=0x280510deU','-Iunlock/compat','-Ideps/edk2/MdePkg/Include','-Ideps/edk2/MdePkg/Include/X64']
cmd=flags+['unlock/tests/test_ad102_transaction.c']+['unlock/'+x+'.c' for x in core]+['-o','test-build/core-tests']
if a.group in ['all','core']:
 subprocess.run(cmd,check=True)
 with open('test-build/core-results.txt','w') as f:
  s=subprocess.run(['test-build/core-tests',prom,'USB/RTX4080-EXPERIMENT/ASSETS'],stdout=f,stderr=subprocess.STDOUT)
 print(Path('test-build/core-results.txt').read_text()[-8000:]);s.check_returncode()
app=flags+['-Wno-unused-function','unlock/tests/test_ad103_app.c']+['unlock/'+x+'.c' for x in ['app','app_io','ownership','format','sha256','checks']+core]+['-o','test-build/app-tests']
if a.group in ['all','app']:
 subprocess.run(app,check=True)
 with open('test-build/app-results.txt','w') as f:
  s=subprocess.run(['test-build/app-tests',prom,'USB/RTX4080-EXPERIMENT/ASSETS','fixtures/AD103-pci-config.bin'],stdout=f,stderr=subprocess.STDOUT)
 print(Path('test-build/app-results.txt').read_text()[-8000:]);s.check_returncode()
