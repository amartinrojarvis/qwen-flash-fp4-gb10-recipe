# Event-driven interactivity benchmark — 2026-10-18

This run exercised the unchanged 200K vLLM FP4 profile: four sequence slots,
FP8 KV cache, MTP 3, `modelopt_mixed`, disk PLE, and the native expandable
allocator. It did not restart the service, flush cache, change flags, or test
MTP 6.

## Method

Three independent conversations were built with real streamed assistant turns.
Each was continued with a small user turn and a fixed 1,024-token response.
For each wave, the harness waited for visible content from **all three** peers,
then started a calibrated cold 32K request before any peer finished. Every
start, first-visible, last-visible, and SSE-content event uses one
`monotonic_ns` clock. This replaces the earlier producer's invalid comparison
of per-request relative timestamps to a pre-calibration wave timestamp.

Private raw SSE remains local. The committed JSON contains hashes, usage,
settings, scheduler/metric observations, and timing only. `cached_tokens` is
`null` because the API did not expose it; native prefix-counter deltas are
corroboration, not substituted cache-hit claims.

## Results

| Wave | Peer continuation prompt tokens | Peer visible TTFT (s) | Peer max visible gap (s) | Cold 32K TTFT (s) | Aggregate E2E TPS | Native samples during cold prefill |
|---|---:|---:|---:|---:|---:|---|
| medium128k | 129,047 / 129,047 / 129,047 | 1.296 / 1.398 / 0.507 | 1.695 / 1.695 / 1.695 | 13.778 | 111.381 | running 3–4, waiting 0 (9 samples) |
| near198k | 197,979 / 197,979 / 198,847 | 1.654 / 1.746 / 0.676 | 1.713 / 1.714 / 1.714 | 13.996 | 106.340 | running 3–4, waiting 0 (9 samples) |

All six peers produced visible content before injection and were still active
at injection. During both cold-prefill intervals, each peer emitted its next
visible content in 0.017s (128K) or 0.082s (near-198K); no individual peer
SSE gap spanned the full cold-prefill interval. Each peer completed the fixed
1,024-token output. The cold request also completed 1,024 tokens in each
wave. Peer per-request E2E TPS was 28.453/28.396/28.782 at 128K and
26.816/26.972/27.729 near 198K.

The predeclared warm thresholds were visible TTFT <=2s and max visible pause
<=2s. All six peer measurements met them. This is a fluency result for this
fixture, not proof of general quality, a cache-residency guarantee, or a
four-full-window capacity claim.

## Recovery and safety

A harness-owned 32K request was cancelled after it emitted visible content.
The engine returned to running=0/waiting=0 without restart, and a 32-token
follow-up completed with visible output. Memory and swap floors remained above
8 GiB and 4 GiB respectively. No service restart occurred; the final backend
still reported both aliases at a 200,000-token limit and was idle.

## Limits

- Native `running=3–4, waiting=0` samples show scheduler activity during the
  cold prefill, but do not establish that four near-200K KV histories were
  physically resident simultaneously.
- No generic quality, long soak, image/vision, or MTP-off/MTP-6 comparison was
  run.
- Earlier “43 common decode samples” are not reused: their clock construction
  was not valid for this comparison.

Portable producer: `benchmarks/run_interactivity.py`.
Sanitized measured evidence: `benchmarks/runs/2026-10-18-interactivity-e2e/report.json`.
