import time, torch

# Force FP32 accumulation: this is the tensor issue path the unlock doubles.
torch.backends.cuda.matmul.allow_fp16_reduced_precision_reduction = False

print("torch", torch.__version__, "| cuda", torch.cuda.is_available(), "| n", torch.cuda.device_count())


def bench(idx, N=8192, iters=10):
    dev = torch.device(f"cuda:{idx}")
    torch.cuda.set_device(dev)
    p = torch.cuda.get_device_properties(idx)
    a = torch.randn(N, N, device=dev, dtype=torch.float16)
    b = torch.randn(N, N, device=dev, dtype=torch.float16)
    torch.cuda.synchronize()
    for _ in range(3):
        c = a @ b
    torch.cuda.synchronize()
    t0 = time.perf_counter()
    for _ in range(iters):
        c = a @ b
    torch.cuda.synchronize()
    dt = (time.perf_counter() - t0) / iters
    tf = 2.0 * (N ** 3) / dt / 1e12
    print(f"device {idx}: {p.name}  SMs={p.multi_processor_count}  FP16->FP32  {tf:7.2f} TFLOPS")
    del a, b, c
    torch.cuda.empty_cache()


for i in range(torch.cuda.device_count()):
    bench(i)
