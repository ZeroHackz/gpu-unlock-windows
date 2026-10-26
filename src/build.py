#!/usr/bin/env python3
import argparse,hashlib,json,os,struct,subprocess
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--zig',default='zig');a=p.parse_args()
r=Path(__file__).resolve().parent;os.chdir(r)
sources=['app','app_io','ownership','format','runtime','sha256','checks','port','compat','vendor/unlock_610','vendor/prep_610','vendor/layout_610','vendor/vbios_610','vendor/gfw_eval']
out=Path('USB/EFI/BOOT/BOOTX64.EFI');out.parent.mkdir(parents=True,exist_ok=True)
cmd=[a.zig,'cc','-target','x86_64-uefi','-std=c11','-ffreestanding','-fno-builtin','-fno-stack-protector','-mno-red-zone','-fshort-wchar','-Os','-g0','-Wall','-Wextra','-Werror','-Wno-unused-parameter','-D__KERNEL__','-DGU_UEFI_PORT','-Iunlock/compat','-Ideps/edk2/MdePkg/Include','-Ideps/edk2/MdePkg/Include/X64','-nostdlib']+['unlock/'+x+'.c' for x in sources]+['-o',str(out)]
subprocess.run(cmd,check=True)
b=out.read_bytes();u16=lambda o:struct.unpack_from('<H',b,o)[0];u32=lambda o:struct.unpack_from('<I',b,o)[0]
pe=u32(60);opt=pe+24
assert b[:2]==b'MZ' and b[pe:pe+4]==b'PE\0\0'
assert u16(pe+4)==0x8664 and u16(opt)==0x20b and u16(opt+68)==10
assert u16(opt+70)&0x140==0x140 and u32(opt+112+5*8+4)>0
for i in [1,12,13]:assert b[opt+112+i*8:opt+120+i*8]==b'\0'*8
entry=u32(opt+16);sections=opt+u16(pe+20)
assert any(u32(t+12)<=entry<u32(t+12)+u32(t+8) and u32(t+36)&0x20000000 for t in [sections+40*i for i in range(u16(pe+6))])
report={'version':'0.4.18-experimental','artifact':str(out),'size':len(b),'sha256':hashlib.sha256(b).hexdigest(),'machine':'AMD64','subsystem':'EFI_APPLICATION','relocations':True,'imports':False,'unlock_implemented':True,'hardware_tested':False,'uefi_vm_tested':False,'profile':json.loads(Path('profile.json').read_text()),'zig_version':subprocess.check_output([a.zig,'version'],text=True).strip(),'source_sha256':{str(f):hashlib.sha256(f.read_bytes()).hexdigest() for f in sorted(Path('unlock').rglob('*')) if f.is_file() and f.suffix in ['.c','.h','.inc']}}
Path('build-result.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items() if k!='source_sha256'},indent=2))
