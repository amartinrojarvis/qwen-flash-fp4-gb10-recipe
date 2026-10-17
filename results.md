# GB10 FP4 serving benchmark — measured results

Run: 2026-10-17. Healthy, already-loaded backend; cold means a fresh prompt prefix, not cold weight loading. Default reasoning off. Single measurements are not statistical guarantees.

| Workload | Requests | Input / output tokens per request | Median visible TTFT (ms) | End-to-end output tok/s | Approx. per-request decode tok/s |
|---|---:|---:|---:|---:|---:|
| pp512_tg128 | 1 | 512 / 128 | 442.1 | 32.48 | 36.35 |
| pp512_tg128_warm | 1 | 512 / 128 | 84.8 | 35.56 | 36.13 |
| c1_1024 | 3 | 1024 / 256 | 661.2 | 32.70 | 35.62 |
| c1_1024_warm | 3 | 1024 / 256 | 56.9 | 33.84 | 33.93 |
| c2_8192 | 2 | 8192 / 256 | 5903.2 | 32.65 | 26.46 |
| c4_8192 | 4 | 8192 / 256 | 12517.9 | 40.01 | 20.19 |
| c1_32768 | 1 | 32768 / 128 | 13041.7 | 7.69 | 35.23 |
| c1_8192_cold | 1 | 8192 / 256 | 3364.6 | 25.03 | 37.16 |
| c1_8192_warm | 1 | 8192 / 256 | 196.3 | 36.17 | 37.06 |

Concurrency rates are aggregate completed output tokens divided by complete client wave wall time, including prefill. Decode is approximate (SSE/speculative chunk coalescing); do not compare it to raw llama-bench/kernel numbers. The 8K C1 baseline was measured afterward, once, so this is descriptive, not a causal scaling study.

MTP draft-token acceptance: 39.96%; active speculation is demonstrated, not its causal speedup. Preemption delta: 0. Minimum available system memory: 16.41 GiB. No service-ready record change during the main run.

JSON, exact tool-call arguments and source-only/unknown-date grounding: three basic fixtures passed. One simple OCR image passed after load; not broad vision quality evidence.

- c2_8192: 8.75 seconds with all streams visibly decoding and 54 native running=N/waiting=0 samples in that interval.
- c4_8192: 10.16 seconds with all streams visibly decoding and 63 native running=N/waiting=0 samples in that interval.

## Limitations
- Not four full 200K windows
- Not MMLU or model quality certification
- Synthetic alpha-filler prompts; forced output length
- Decode TPS approximate because SSE may coalesce speculative tokens
- Cache-hit count unknown unless API/native counters provide evidence
- The per-request cached-token field was unavailable; immediate exact replays showed native prefix-cache hit counter increments.
- No full 4×200K context trial, broad model-accuracy suite, long soak or MTP-off baseline was run.
- Other host services remained running; the production router showed no external requests in the main measured waves.

## Exact run identity and artifacts

Image, model revision and runtime pins are in [identity.json](identity.json); the actual template SHA-256 was `e57684bae4156211a55473c5a63be976a405a37ab5be5ae0e5abf1df5349c4b2`. Hardware: NVIDIA GB10, driver 580.178.04, Linux arm64.

- [Machine-readable summary](benchmarks/runs/2026-10-17/summary.json)
- [Main report](benchmarks/runs/2026-10-17/report.json) and [matched 8K C1 supplement](benchmarks/runs/2026-10-17/supplement/report.json)
- [Decode overlap](benchmarks/runs/2026-10-17/decode-overlap.json) and [safety/provenance](benchmarks/runs/2026-10-17/safety-and-provenance.json)
- [Protocol](methodology.md) and [portable runner](benchmarks/run_benchmark.py)

The measured run produced 17 throughput responses, three functional responses and one later OCR response. There were no HTTP errors in those inference responses, no fresh Xid/system OOM/allocation warnings, and the own vision sidecar was not loaded. Cached tokens remain null where the API did not return them.

The exact physical model export is a separately required input: no complete source-to-export reproduction manifest was established. The launcher is an explicit reconstruction with conditional equivalence, not a clean-host reproduction certificate.
