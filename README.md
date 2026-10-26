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

- **This repository is board-specific by design.** The pinned values
  (`bar0`, PCI ROM SHA-256, PROM view SHA-256, `VRAM`, stock `SS1`) belong to the two
  Gigabyte RTX 4060 Ti 16 GB cards used for development. **Different cards — even the same
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
