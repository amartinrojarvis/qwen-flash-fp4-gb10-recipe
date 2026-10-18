# Full-context completion — 2026-10-17

Sanitized machine-readable evidence: [`benchmarks/runs/2026-10-17-full-context-completion/summary.json`](benchmarks/runs/2026-10-17-full-context-completion/summary.json). The private run retained bounded raw SSE and telemetry; this repository contains no prompts, response bodies, addresses, host paths, credentials, template contents, model files, or caches.

## Result

The existing 200,000-token FP4 vLLM profile completed every explicitly requested near-ceiling admission wave. Each retrieval request was calibrated through the active chat template to **198,976 prompt tokens** and reserved 1,024 generated tokens; this is exactly the 200,000-token per-request ceiling.

| workload | requests completed | semantic canary | TTFT visible, seconds/request | aggregate E2E output tok/s | scheduler/residency observation |
|---|---:|---|---|---:|---|
| C2 × 198,976 + 1,024 | 2/2 | 2/2 | 86.334, 168.952 | 0.940 | Scheduler-managed/serialized; no common visible decode interval proving C2 residency. |
| C3 × 198,976 + 1,024 | 3/3 | 3/3 | 86.083, 171.525, 253.643 | 0.922 | Scheduler-managed/serialized; residency not proven. |
| C4 × 198,976 + 1,024 | 4/4 | 4/4 | 258.024, 339.391, 172.363, 86.692 | 0.910 | Scheduler-managed/serialized; residency not proven. |

The canary request has distinct salted markers near the beginning (~5%), middle (~50%), and tail of every prompt. Raw or fenced JSON was accepted, then locally graded for the exact marker order. All completions returned streamed usage and normal `stop` termination.

## Separate output-throughput workload

A separate C4 workload used 32,768 prompt tokens/request, `ignore_eos=true`, and 512 requested output tokens. It completed 4/4 at `length`, with 32.126 aggregate E2E output tok/s over 63.749 s. Per-request TTFT was 30.857, 44.088, 52.900, and 14.519 s; approximate visible-decode rates were 16.045, 26.630, 47.143, and 10.788 tok/s. The historical collector recorded an 8.985-second common visible-decode interval and 43 four-running/zero-waiting samples, but their alignment is unqualified because of its relative-clock defect; see the audit correction below.

Aggregate E2E throughput is completed output divided by full wave wall time, including prefill. Approximate visible-decode TPS uses SSE timing and is affected by chunk coalescing and MTP; it must not be compared directly with the short retrieval canaries or kernel-only benchmarks.

## Safety and boundaries

The service stayed healthy through the run. The completed C3/C4 evidence recorded no GPU Xid, host OOM, or `NV_ERR_NO_MEMORY`; minimum available memory and free swap during that completion were 16,752,340,992 and 11,139,485,696 bytes. The active configuration remained the effective 200K profile: four sequences, MTP 3, FP8 KV cache, `modelopt_mixed`, disk/`io_uring` PLE, and native expandable allocator.

`RESIDENCY_NOT_PROVEN` is not a model or capacity failure. It means the telemetry did not contain two samples of every requested decoder running with no waiting requests during a common visible-decode interval. The C2/C3/C4 admissions and semantic requests nevertheless completed. This campaign is synthetic retrieval plus a bounded output workload; it does not establish general quality, MMLU, a long soak, or four fully resident 200K contexts.

Direct checks against the same endpoint also passed: chat JSON, one required tool call with exact arguments, and the repository's synthetic OCR fixture. The OCR check is one simple fixture, not a general vision result.

## Fixture audit correction

The historical marker named `CANARY_95` was actually placed after the final filler block, close to the prompt tail, not at 95% depth. Its identifier and recorded responses are preserved; its name must not be interpreted as a verified position. This is beginning/middle/tail retrieval evidence, and the last marker is easier to recover from the adjacent question.

The earlier 43-sample common-decode claim used per-request relative timestamps aligned to a pre-calibration wave timestamp. Treat its alignment as unqualified; the newer event-driven interactivity report uses absolute monotonic timestamps and supersedes that clock construction. The earlier throughput/usage figures are retained, not recomputed as a new run.
