# Measurement protocol actually executed

The current results were collected on 2026-10-17 against the already-running, monitored 200K/4-slot backend. The model was not swapped or restarted for this benchmark. The portable launcher in this repository was separately CPU/dry-run checked; it was not itself used for the live run.

## Requests and cache definition

- Synthetic chat prompts: fresh leading nonce, repeated ` alpha` filler, then an instruction to produce long English prose. The nonce changes at the beginning to avoid long shared prefixes among cold lanes.
- Exact total prompt sizes, including the chat template, were calibrated with the live chat-form `/tokenize` API and checked against streamed `usage.prompt_tokens`.
- `cold` means a fresh prompt prefix on an already-loaded model, not empty weight/JIT/HF caches or a cold boot. `warm` is an immediate exact replay of the preceding prompt.
- Temperature 0, seed 42, thinking disabled; `ignore_eos=true` deliberately forces the throughput output budget. `finish_reason=length` is expected for throughput, never accepted as a clean functional completion.
- The 1,024/256 C1 cold/warm pairs were repeated three times. 512/128, C2 and C4 at 8,192/256, and C1 at 32,768/128 used one wave each. A matched 8,192/256 C1 cold/warm pair was measured afterward, once. Do not portray this as a statistical scaling comparison.

## Timing and concurrency

Raw SSE and actual usage are retained in `benchmarks/runs/2026-10-17/`. TTFT is the first nonempty visible-content event, not a role/reasoning/empty event. Every stream must include usage, a finish reason and `[DONE]`. Client timings include loopback HTTP and a small pre-request metric read; these are not bare-kernel timings.

- End-to-end request output rate: actual completion tokens / complete client request duration.
- Wave output rate: sum of actual completion tokens / complete client wave wall time, including prefill and client launch overhead. This is the aggregate C2/C4 figure.
- Approximate decode rate: `(completion_tokens - 1) / (last_visible_content_time - first_visible_content_time)`. Speculative/SSE coalescing means this is an estimate, not a precise one-token-step rate.
- Effective prefill rate, if read from raw JSON, is prompt tokens / client TTFT. It includes scheduler/network/metric overhead and is not isolated kernel prefill.

C2/C4 used simultaneous barriers and independently salted prompts. Native running and waiting gauges were sampled together. Decode overlap was derived from the latest first-visible event through the earliest last-visible event, and target-running/zero-waiting samples were counted inside that interval. The production router was observed separately: no external inference traffic was seen during the main measured waves. Other host services were not stopped.

## Cache, MTP and safety

The API did not expose per-request cached-token details: those fields remain null. Native prefix-cache counter deltas corroborated full-prefix hits for each immediate short replay. MTP acceptance is accepted draft tokens / proposed draft tokens, not a measured speedup over MTP-off.

Host available RAM/swap and native request metrics were sampled. The service-ready record was unchanged, preemption delta was zero, and the reviewed kernel window had no Xid/system-OOM/allocation-warning event. The existing independent production memory and fatal-event protections remained enabled.

JSON, exact structured tool arguments, source-grounded null abstention and one simple OCR image were separate small functional probes. They are not a general model-quality benchmark.

## Scope and reproducibility limits

This is an HTTP serving benchmark, not raw llama-bench, MMLU, a long soak or proof of four populated 200K windows. Original run nonces were random time-based values; prompt hashes and generation settings were preserved, but exact original nonce replay is unavailable. The portable runner regenerates the same token-calibrated workload distribution, adds convenient CLI parameters and runs the matched 8K C1 pair in the main matrix; its ordering differs from the original main run plus supplement. Never present portable-runner CPU checks as a fresh GPU reproduction.

See `results.md`, `provenance.md` and the raw JSON/SSE for evidence and limits.
