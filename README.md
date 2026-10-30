# gpu-unlock-windows

Unlock the full **FP16/BF16 → FP32 tensor issue rate** on consumer NVIDIA RTX 40-series
(Ada) GPUs **on Windows**, by running a small UEFI application *before* the NVIDIA driver
binds the card.

This is a Windows port of the AD106 work in
[gpu-unlock-ada](https://github.com/JustAResearcher/gpu-unlock-ada), itself built on
[Zagitta/gpu-unlock](https://github.com/Zagitta/gpu-unlock) and
[TOTORONG/AD103_win_unlocker](https://huggingface.co/TOTORONG/AD103_win_unlocker).

It was developed and verified on **two Gigabyte RTX 4060 Ti 16 GB** cards, and supports
unlocking **both cards in a single boot**.

## What this does

NVIDIA ships consumer GeForce cards with the FP16/BF16 (and TF32) FMA-into-FP32 tensor
throughput roughly **halved** vs. the professional parts on the same silicon. The speed
selectors are `SS0 = 0x88888888` and `SS1 = 0x8`.

This tool:

1. Finds the target card(s) during UEFI boot.
2. Runs the signed NVIDIA FWSEC firmware (from the card's own VBIOS) and writes the
   four PLM registers (`WPR_CFG`, `FBPA`, `WPR`, `FEAT`).
3. Writes `SS0 = 0x88888888`, `SS1 = 0x8`.
4. Performs a PCIe Function Level Reset (FLR).
5. Hands control to Windows, which loads the **stock, unmodified** NVIDIA driver.

No patched NVIDIA driver, no VBIOS flash, no UEFI application for a specific card.

### Measured result (2× RTX 4060 Ti 16 GB, i.e. AD106)

FP16 → FP32 accumulate GEMM, 8192³, cuBLAS via PyTorch (`allow_fp16_reduced_precision_reduction = False`):

| Setup | Stock | Unlocked | Gain |
|---|---|---|---|
| Single card (RTX 4060 Ti, display) | 46.64 TFLOPS | **77.54 TFLOPS** | **+66%** |
| Dual card, both at once | 46.64 TFLOPS | **77.54 / 77.93 TFLOPS** | **+66% / +67%** |

The raw register-resident issue rate doubles (~92 TF/s); a real GEMM lands lower because
memory bandwidth becomes the limit once compute is doubled. See [docs/BENCHMARKS.md](docs/BENCHMARKS.md).

## ⚠️ Important limitations

- **This repository is board-specific by design.** On this branch the pinned values
  (`bar0`, PCI ROM SHA-256, PROM view SHA-256, `VRAM`, stock `SS1`) belong to **one**
  Gigabyte RTX 4060 Ti 16 GB (`1458:4123`, bus `01`) — see
  [the walkthrough below](#实操记录技嘉-rtx-4060-ti-16gb14584123单卡). **Different cards — even the same
  model with a different VBIOS — will be rejected** until you capture your own values.
  The [capture procedure](#capturing-your-own-card) explains how.
- **It is per-boot.** The unlock is applied during boot and reset on power cycle.
  You must boot the USB and press `U` each time you want it.
- **Windows only** for the driver handoff; the tooling to *build* and capture runs on
  Windows (or WSL/Linux).
- **Secure Boot must be disabled** for the unsigned experimental EFI.
- **Warranty / risk.** This writes GPU registers and resets the device. It can leave a
  card needing a power cycle. Use at your own risk; keep a stock boot path.
- The FP16/BF16 → FP32 path is what is doubled. **Decode-bound** workloads (LLM token
  generation) are memory-bandwidth-bound and will not speed up; **prefill, image
  generation, and LoRA/fine-tune GEMMs** benefit.

## 实操记录：技嘉 RTX 4060 Ti 16GB（1458:4123）单卡

这一节记录本分支在一台真实机器上从零到解锁成功的完整过程。换成别的卡时，按同样的步骤走，只需要把第 3 步和第 6 步里的值换成你自己卡的值。

### 结果

| | 第 1 次 | 第 2 次 | 第 3 次 | 平均 |
|---|---|---|---|---|
| 原厂 | 45.60 | 45.43 | 45.58 | **≈45.5 TFLOPS** |
| 解锁后 | 77.81 | 78.88 | 78.21 | **≈78.3 TFLOPS（+72%）** |

FP16→FP32 GEMM，8192³，`bench/bench_torch.py`，torch 2.14.1+cu130，驱动 610.88。两次测试的 SM 频率都是 2730 MHz，功耗上限都是 165 W。

### 测试环境

| 项目 | 值 |
|---|---|
| 显卡 | 技嘉 RTX 4060 Ti 16GB，`10de:2805`，子系统 `1458:4123`，VBIOS `95.06.30.00.51` |
| PCI 位置 | `0000:01:00.0`，单卡、接显示器 |
| 主板 | 技嘉 B760M GAMING WIFI，BIOS F4，启动菜单键 F12 |
| 系统 | Windows 11 Pro，UEFI 启动，Secure Boot 已关闭 |
| U 盘 | 16GB，FAT32，MBR |

### 第 1 步：确认显卡身份

```powershell
nvidia-smi --query-gpu=index,name,pci.bus_id,pci.device_id,pci.sub_device_id,vbios_version,memory.total --format=csv
```

需要记下三项：设备 ID（`0x280510DE` 即 `2805`）、子系统 ID（`0x41231458`）、总线号（`00000000:01:00.0` 即 `0x01`）。原作者仓库里写死的是子系统 `4112`、总线 `0B`，并且是双卡表。三项都对不上时，程序在 `target` 阶段就会拒绝这张卡。

确认 Secure Boot 已关闭（`0` 表示关闭）：

```powershell
Get-ItemProperty HKLM:\SYSTEM\CurrentControlSet\Control\SecureBoot\State -Name UEFISecureBootEnabled
```

### 第 2 步：准备构建环境（项目内 conda 环境）

所有工具都装在项目目录的 `./venv` 里，不使用系统全局 Python。zig 0.17 可以直接从 conda-forge 安装：

```powershell
conda create -p ./venv -c conda-forge python=3.14 zig=0.17.0 -y
```

`venv` 里自带 `zstd.exe`，位于 `venv\Library\bin`。运行固件脚本前，把它加到 PATH 最前面（见第 7 步）。

### 第 3 步：改成采集版

需要改三个文件：

- `src/unlock/port.h`：`GU_CARD_COUNT` 设为 `1U`；`GU_BOARD_SUBSYSTEM` 设为你的子系统 ID（这里是 `0x41231458U`）。
- `src/unlock/port.c`：`GuCards[]` 只留一项，填设备 ID、总线号和 `is_display=TRUE`；`bar0`、`rom_size`、`vram`、`ss1_stock` 填 `0`，两个哈希填 `""`。
- `src/unlock/app.c`：卡循环按 `GU_CARD_COUNT` 倒序遍历（本分支已改好）。

`0` 或空字符串表示"未知，只记录、不拦截"。空的 PROM 哈希永远匹配不上，所以采集版**一定会在 `prom` 阶段停下**，保存 `PROM.BIN`，**不会**进入按 U 的阶段，也不会写任何寄存器。

```powershell
.\venv\python.exe src\build.py --zig "$PWD\venv\Library\bin\x86_64-w64-mingw32-zig.exe"
```

### 第 4 步：制作采集 U 盘

采集版不需要 NVIDIA 固件，因为固件在 `prom` 之后才加载。但 `make-usb.ps1` 会检查固件是否存在，所以这里改用手动复制。U 盘里只需要 `EFI\BOOT\BOOTX64.EFI` 和一个空的 `RTX4080-EXPERIMENT` 文件夹：

```powershell
New-Item -ItemType Directory -Force src\USB\RTX4080-EXPERIMENT
Copy-Item -Recurse -Force src\USB\* D:\
```

U 盘**不需要安装任何启动项**。UEFI 会自动识别可移动设备上的 `\EFI\BOOT\BOOTX64.EFI`。

### 第 5 步：采集开机（需要人在机器前）

1. 开始菜单 → 关机，等主机完全断电。
2. 开机，连按 **F12**，选择 **`UEFI: <U 盘名>`**，不要选没有 `UEFI:` 前缀的那一项。
3. 屏幕滚动检查信息后，出现 `Preflight stopped before unlock`，按回车返回。
4. 正常进入 Windows。

U 盘上会生成 `RTX4080-EXPERIMENT\RUN00\REPORT.TXT` 和 `PROM.BIN`。如果这个目录是空的，说明根本没有从 U 盘启动，可以用 `(Get-CimInstance Win32_OperatingSystem).LastBootUpTime` 核对开机时间。

正常的 RUN00 中，从 `target` 到 `cold-state` 应该全是 `status=0`，最后停在：

```
CHECK stage=prom status=0x800000000000001b
FINAL status=0x800000000000001b stage=prom attempted=0 driver_release=0 clean=1
```

### 第 6 步：把采集值写回去

从 `REPORT.TXT` 里取下面这些值：

| 字段 | 日志里的位置 | 本卡的值 |
|---|---|---|
| `bar0` | `bar0 descriptor: ... min=` | `0x53000000` |
| `rom_size` | `PCI RomImage size=` | `0x24c00` |
| `rom_sha` | `PCI RomImage bytes=... SHA256=` | `ba9d105f…3023` |
| `vram` | `VRAM register=` | `0x3ffc` |
| `ss1_stock` | `cold state: ... SS1=` | `0x7` |
| `prom_sha` | `PROM verified view [0,0xd6c00) ... SHA256=` | `c99af86f…533a` |

填进 `src/unlock/port.c`，同时把同一个 PROM 视图哈希写进 `src/unlock/prom_profile.h` 的 `GU_PROM_VIEW_SHA256`，然后重新运行第 3 步的 `build.py`。

请把 `PROM.BIN` 备份到 `local/`（已被 gitignore），**不要提交**，那是显卡 VBIOS 的原始内容。

### 第 7 步：准备 NVIDIA 固件

```powershell
$env:PATH = "$PWD\venv\Library\bin;$PWD\venv;" + $env:PATH
.\venv\python.exe -I tools\prepare_assets.py
```

这一步会从 download.nvidia.com 下载 `NVIDIA-kernel-module-source-610.43.03.tar.xz`，从 archive.cachyos.org 下载 `nvidia-utils-610.43.03-1-x86_64_v3.pkg.tar.zst`，下载后先校验 SHA-256，再提取并生成 5 个固件文件，最后对照 `ASSETS-MANIFEST.json` 逐一校验。

本分支修复了一个问题：原脚本不会生成 `v67-ad102-610.43.03-four-plm.bin`，最后一步会报 `FileNotFoundError`。现在由 `ad102_payload.payload()` 直接生成，生成的字节仍要通过清单里固定的哈希校验。

### 第 8 步：制作正式 U 盘

```powershell
.\tools\make-usb.ps1 -Drive D:
```

### 第 9 步（可选）：测原厂速度

```powershell
.\venv\python.exe -m pip install --index-url https://download.pytorch.org/whl/cu130 torch
.\venv\python.exe bench\bench_torch.py
```

### 第 10 步：解锁开机（需要人在机器前）

1. 关机，等主机完全断电；开机连按 F12，选 `UEFI: <U 盘名>`。
2. 检查通过后，屏幕上会出现 `READY: ...` 和 `Press U once ... Esc/30s cancels.`。
3. **30 秒内按一次 `U`。** 屏幕上写的型号是 "RTX 4080"，这是上游代码遗留的文字，可以忽略。
4. 出现 `ARMED` 后，屏幕可能黑屏或卡住几秒，这是显卡在做 FLR 复位，**不要断电、不要拔 U 盘**。
5. 程序会自动启动 Windows。

**踩过的坑：** 第一次解锁时忘了按 U，日志结尾是 `CHECK stage=arming status=0x8000000000000012`（`EFI_TIMEOUT`），并且 `attempted=0`。超时后显卡没有被改动，重新开机再来一次即可。无线或蓝牙键盘在 UEFI 阶段经常用不了，最好用有线键盘，插在主板背板的 USB 口上。

### 第 11 步：确认结果

在新生成的 `RUNxx\REPORT.TXT` 里应该能看到：

```
AD102 PLM final: index=0 target=WPR_CFG value=0xfffff0ff expected=0xfffff0ff matched=1
AD102 PLM final: index=1 target=FBPA value=0xffffff0f expected=0xffffffff matched=0
AD102 PLM final: index=2 target=WPR value=0xffffffff expected=0xffffffff matched=1
AD102 PLM final: index=3 target=FEAT value=0xffffffff expected=0xffffffff matched=1
SELECTOR RESULT: SS0 before=0x25474037 after=0x88888888 expected=0x88888888 matched=1 status=0
SELECTOR RESULT: SS1 before=0x7 after=0x8 expected=0x8 matched=1 status=0
POST-GOP SS0=0x88888888 SS1=0x00000008
FINAL status=0 stage=post-unlock-handoff attempted=1 driver_release=1 clean=1
```

FBPA 显示 `matched=0` 是**预期内的**，程序把它当作非致命项。然后进 Windows 运行 `bench\bench_torch.py`，速度应该接近 78 TFLOPS。

### 日常使用

- 解锁效果在**断电后失效**，重启通常也会失效。每次需要时都从 U 盘启动并按 U；不插 U 盘就是原厂状态。
- 想不按键自动解锁：在 `src/build.py` 的编译参数里加上 `-DGU_AUTO=1`，再把 U 盘设为第一启动项。
- 出现 `STOP`，或黑屏超过 1 分钟：长按电源键关机，等 10 秒，拔掉 U 盘再开机。

## Layout

```
src/            the EFI application + build/test tooling
  unlock/       C sources (app.c, port.c, checks.c, vendor/*, ...)
  deps/edk2/    pinned EDK2 headers
  firmware-tools/  pinned NVIDIA firmware fetch + payload generation
  build.py      zig-based EFI build
tools/          make-usb.ps1, prepare_assets.py, check_rom.py
bench/          bench_torch.py (FP16->FP32 GEMM benchmark)
docs/           BENCHMARKS.md, PORTING-AD106.md
```

## Prerequisites

- Windows x64.
- **Zig** (for `zig cc -target x86_64-uefi`). Tested with 0.17.
- **Python 3.14+** (for the zstd-format firmware inputs).
- **zstd** on PATH (for `generate_v67.py`).
- A FAT32 USB stick.
- Secure Boot **disabled** (test build).

```powershell
scoop install zig zstd
```

## Building

```powershell
cd src
python build.py                 # produces src/USB/EFI/BOOT/BOOTX64.EFI
```

`build.py` downloads nothing by itself; run the firmware-tools first if you do not have
the pinned assets:

```powershell
python tools\prepare_assets.py  # fetches pinned NVIDIA 610.43.03 inputs, verifies SHA-256
```

## Making the USB

```powershell
.\tools\make-usb.ps1 -Drive E:
```

Copies `EFI/BOOT/BOOTX64.EFI` and the pinned assets to the FAT32 drive and verifies the
EFI hash after the copy.

## Boot and unlock

1. Fully power off (not restart).
2. Boot the USB from the UEFI boot menu.
3. Wait for `READY`, press **`U`**.
4. The display may blank/freeze while the card is reset; Windows then loads.

With the two-card card table, the app unlocks the **headless card first**, then the
**display card**, so you press `U` **once per card**.

### Optional: fully automatic (no keypress)

Add `-DGU_AUTO=1` to the `cmd` flags in `src/build.py`. `Arm()` then proceeds after a
2-second grace period instead of waiting for `U` (Esc still cancels). Pair it with a
persistent UEFI boot entry that runs `\EFI\gpu-unlock\BOOTX64.EFI` first, and the unlock
is applied on every boot with no interaction.

If it prints `STOP`, power off with the physical button, wait 10s, and boot Windows normally.

## Capturing your own card

Because the pinned values are per-board, other cards must be captured:

1. Put the capture build on the USB. In `src/unlock/port.c`, the `GuCards[]` table has
   `bar0 = 0`, `rom_size = 0`, empty hashes = "unknown, log it, don't gate on it".
2. Boot it. It will run through the preflight and stop at the `prom` stage, writing the
   real values into `RTX4080-EXPERIMENT/RUNxx/REPORT.TXT` and saving `PROM.BIN`.
3. Copy the captured `bar0`, PCI ROM size+hash, PROM view hash, VRAM register and stock
   `SS1` into `GuCards[]` in `src/unlock/port.c`, rebuild, and re-run.

See [docs/PORTING-AD106.md](docs/PORTING-AD106.md) for the full walkthrough that was used
for these two cards.

## Verification

```powershell
python bench\bench_torch.py
```

Prints FP16→FP32 GEMM TFLOPS per GPU. Compare to the ~46.6 TFLOPS stock baseline for an
RTX 4060 Ti.

## Credits

- [TOTORONG/AD103_win_unlocker](https://huggingface.co/TOTORONG/AD103_win_unlocker) — the
  Windows UEFI reference port and firmware payload integration.
- [JustAResearcher/gpu-unlock-ada](https://github.com/JustAResearcher/gpu-unlock-ada) — the
  Linux module and the AD106 canary reports.
- [Zagitta/gpu-unlock](https://github.com/Zagitta/gpu-unlock) — the original Ampere unlocker.
- NVIDIA's published loader code, Nouveau and envytools.

## License

GPL-2.0-only for the module, packaging and payload integration (as inherited from
gpu-unlock-ada). NVIDIA firmware remains under its own terms. See `src/LICENSES/`.
