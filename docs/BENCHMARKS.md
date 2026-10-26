# Benchmarks — proof

Measured on Windows 11 with two Gigabyte RTX 4060 Ti 16 GB (AD106) cards, stock NVIDIA
driver (617.42), power limits at default (165 W each), room temperature.

## Method

`bench/bench_torch.py`, run in a CUDA PyTorch venv:

```python
torch.backends.cuda.matmul.allow_fp16_reduced_precision_reduction = False
# 8192^3 FP16 matmul, 3 warmups, 10 timed iterations, time.perf_counter
```

`allow_fp16_reduced_precision_reduction = False` forces **FP32 accumulation**, which is
exactly the path the unlock doubles. This is a real cuBLAS GEMM, not a synthetic
instruction-rate probe, so the number is *lower* than the raw issue rate (~92 TF/s).

## Stock baseline

| GPU | FP16→FP32 GEMM |
|---|---|
| RTX 4060 Ti 16 GB (display card, stock) | 46.64 TFLOPS |

## Unlocked, single card

| GPU | Before | After | Gain |
|---|---|---|---|
| RTX 4060 Ti 16 GB (`SS0=0x88888888 SS1=0x8`) | 46.64 TFLOPS | **77.54 TFLOPS** | **+66%** |

`RUN04` in the UEFI log: `SELECTOR RESULT: SS0 before=0x4045116 after=0x88888888 matched=1`,
`SS1 before=0x3 after=0x8 matched=1`, `POST-GOP SS0=0x88888888 SS1=0x00000008`,
`FINAL status=0`.

## Unlocked, both cards at once

| GPU | FP16→FP32 GEMM |
|---|---|
| RTX 4060 Ti (display, `0B`) | **77.54 TFLOPS** |
| RTX 4060 Ti (headless, `0C`) | **77.93 TFLOPS** |

`RUN08` in the UEFI log: two transactions, one per card, both
`result=0 FLR=1`, both `SS0=0x88888888 SS1=0x8`, `FINAL status=0 … clean=1`.

## Interpreting this

- The unlock doubles the **issue rate**; a real GEMM gains ~+66% here because the
  128-bit memory bus (288 GB/s) becomes the limiter once compute is doubled.
- `INT8`, `dp4a`, scalar FP32 and (mostly) `FP8` are unchanged — this is the
  FP16/BF16/TF32-into-FP32 path only.
- LLM **decode** is bandwidth-bound → little/no gain. **Prefill, diffusion, LoRA** benefit.

## Reproduce

```powershell
# any CUDA-enabled PyTorch venv
$env:CUDA_DEVICE_ORDER = 'PCI_BUS_ID'
python bench\bench_torch.py
```

A stock RTX 4060 Ti 16 GB should report ~46.6 TFLOPS; an unlocked one ~75–80 TFLOPS.
