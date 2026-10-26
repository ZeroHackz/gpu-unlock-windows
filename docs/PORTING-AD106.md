# Porting walkthrough (AD106 / RTX 4060 Ti)

This is the exact sequence used to bring the Windows UEFI unlock to two Gigabyte
RTX 4060 Ti 16 GB cards. It is a template for other boards.

## 0. Identity

Get the device IDs and BDFs from Windows:

```powershell
nvidia-smi --query-gpu=gpu_bus_id,pci.device_id,pci.sub_device_id,name,memory.total --format=csv
```

For example:

| Card | device | subsystem | bus | role |
|---|---|---|---|---|
| display | `10de:2805` | `1458:4112` | `0B` | drives the monitor |
| headless | `10de:2803` | `1458:4112` | `0C` | compute only |

`chip` (PMC_BOOT_0) is read at boot; for AD106 it is `0x196000a1`.

## 1. Chip identity

The transaction itself (AD102-family four-PLM payload, `SS0/SS1`, FLR) is shared across
AD102/AD103/AD104/AD106. Only the identity constants and the *board* values change.

In `src/unlock/port.c`, `GuCards[]` holds one entry per card, and `GU_BOARD_ID` is
derived from `GuCard->device` at runtime. Set `device`, `bus`, `is_display`.

> Note: the display-card requirement. The upstream `DisplayCheck` expects the target to
> be the GPU that owns the UEFI GOP (the display card). The headless card needs
> `is_display = FALSE`, which makes `DisplayCheck` accept 0 GOPs on the target and skip
> other GPUs' GOPs (`if(parent!=Gu.handle)continue;`).

## 2. Capture the board values

Set the card's `bar0 = 0`, `rom_size = 0`, `prom_sha = ""`, `vram = 0`, `ss1 = 0`.
Those zeros mean **"unknown — log it, don't gate on it"**. The checks in
`ConfigCheck`/`BarCheck`/`ColdCheck`/`PromCheck` skip the corresponding gate, while
still logging the actual values:

- `ConfigCheck` logs the full 256-byte PCI config dump.
- `BarCheck` accepts the real BAR0 descriptor and records it.
- `ColdCheck` logs `SS0`, `SS1`, `VRAM`, PLMs.
- `PromCheck` logs the PCI ROM SHA-256, the live PROM SHA-256, the PROM view SHA-256,
  and saves `PROM.BIN`, then stops (safe — no transaction).

Boot that build, then read `RTX4080-EXPERIMENT/RUNxx/REPORT.TXT` and `PROM.BIN`.

## 3. Pin the captured values

Put the captured values back into `GuCards[]`:

```
{ device, bus, bar0, bar0_len, rom_size, rom_sha, vram, ss1_stock, prom_sha, is_display, label }
```

Then rebuild. The card now passes all preflight gates and reaches `READY`.

## 4. Two cards in one boot

`EfiMain` loops over `ordem[]` (headless first, display last):

```c
static const UINTN ordem[2]={1,0};
for(UINTN ci=0;ci<2;ci++) {
  GuCard=&GuCards[ordem[ci]];
  GuInit(St->BootServices,NULL); ...
  status=RunOneCard(St,&attempted,&release_attempted);
  if(EFI_ERROR(status))break;
}
```

`RunOneCard` is the original single-card preflight + arm + release + transaction. The
final handoff (`RestoreDisplayForWindows` + `StartImage(Windows)`) runs once, after both.

## 5. Gotcha that bit us

`unlock_610.c` also uses `GU_TARGET_PCI_ID` for its own identity checks. If you leave it
as a compile-time `-D` value, the *other* card's transaction will fail with
`read_target_plm error=-19`. Make it runtime too:

```c
#define GU_TARGET_PCI_ID (0x10deU | ((UINT32)GuCard->device << 16))
```

and remove `-DGU_TARGET_PCI_ID=...` from `build.py`.

## 6. Verify

Per card, `RUNxx/REPORT.TXT` should contain:

```
SELECTOR RESULT: SS0 ... after=0x88888888 matched=1
SELECTOR RESULT: SS1 ... after=0x8 matched=1
POST-GOP SS0=0x88888888 SS1=0x00000008
FINAL status=0 ... clean=1
```

Then run `bench/bench_torch.py`: ~46.6 TFLOPS stock → ~77 TFLOPS unlocked.
