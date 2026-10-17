# Long-context campaign — 2026-10-17

Machine-readable evidence: [`benchmarks/runs/2026-10-17-long-context/summary.json`](benchmarks/runs/2026-10-17-long-context/summary.json). The three sanitized reports and their incremental telemetry JSONL are in that directory. No prompts, local paths, addresses, credentials, template contents, model weights, or caches are included.

## Effective profile measured

- `vllmcritic`, vLLM FP4 profile; total request limit **200,000 tokens**.
- Final effective options: 4 sequences, MTP 3, FP8 KV, `modelopt_mixed`, PLE disk / `io_uring`, and native expandable allocator.
- Template was checked in the running container: SHA-256 `e57684bae4156211a55473c5a63be976a405a37ab5be5ae0e5abf1df5349c4b2`, 28,234 bytes. The template is not distributed.

## Results

| Workload | Result | Exact prompt tokens/request | Reserved output | TTFT / request | Approx. decode tok/s / request | Aggregate E2E tok/s | Notes |
|---|---:|---:|---:|---|---|---:|---|
| C4, 32,768 | `RESIDENCY_NOT_PROVEN` | 32,768 | 256 | 31.259, 53.673, 14.723, 44.704 s | 3.34, 49.78, 2.17, 7.19 | 5.49 | All four streams completed, but their first/last visible intervals did not overlap; therefore this is not evidence of four simultaneous decoders. |
| C1, 65,536 | `PASS` | 65,536 | 256 | 26.402 s | 64.51 | 2.79 | Salted canaries at 5/50/95% were recovered in order. |
| C2, 65,536 | `RESIDENCY_NOT_PROVEN` | 65,536 | 256 | 53.766, 28.077 s | 58.42, 2.93 | 2.80 | Both completed with valid canaries; common visible decode interval was absent. |
| C1, 198,000 | `PASS` | 198,000 | 1,024 | 83.637 s | 62.68 | 0.85 | Actual total was 198,072 (198,000 prompt + 72 generated), safely below 200,000. |

TTFT is the first visible content event. “Approx. decode” is `(completion_tokens−1)/(last_visible−first_visible)` and can be distorted by SSE chunking and MTP. Aggregate E2E throughput is actual completed output tokens divided by full client wave wall time, including prefill.

## Safety and stopping rule

The campaign took two idle samples before loading, used a bounded harness deadman while the existing persistent service monitor remained active, and recorded memory, swap, scheduler, preemption, prefix-cache, speculative-decoding, and kernel-event state incrementally. All executed waves reported zero preemptions; no Xid, host OOM, or `NV_ERR_NO_MEMORY` event was seen. The endpoint remained healthy afterward with the same physical 200K service and final argv; chat JSON, tool call, and the local direct OCR fixture also passed. The separate vision sidecar remained off.

Escalation stopped after the C2 65,536 concurrency wave could not prove a common decode interval. Consequently, C3/C4 near-200K and C2 near-200K are **not run**, not capacity failures. The single near-full C1 result proves one 198K prompt within the configured total-token limit; it does not prove four full resident 200K contexts, a soak, or general quality.

## Workload construction and limits

Each lane was independently calibrated through `/tokenize`, salted at the beginning, and contained unique canaries at about 5%, 50%, and 95% of its prompt. The final query requested the markers without restating them. The response was graded locally after accepting either raw JSON or a fenced JSON object. This is a synthetic retrieval/ordering check, not MMLU, a general quality claim, or a long-duration stability test. Cache fields from the API were unavailable (`null`); native counter deltas are retained in the reports.
