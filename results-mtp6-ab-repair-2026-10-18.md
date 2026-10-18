# MTP3 vs MTP6: repaired bounded A/B — 18 October 2026

## Decision / decisión

**MTP6 was not retained. MTP3 is the active persistent 4×200K profile.**

This supersedes the conclusion of the earlier one-wave MTP report, whose
measurement is preserved as history but is not a qualified comparison. The
old harness generated a different leading nonce for each cold/warm request
while hashing only the prompt suffix, retained just one repetition per family,
and did not retain the full grounding response. Its old percentages are therefore
observations from that pilot, not repeated causal results.

The repaired run used three real paired repetitions for each of three Spanish
families (prose, Python code and tool-workflow explanation), each with a cold
request followed by an immediate byte-identical warm replay. The immutable
fixture generated every leading nonce once before execution. The canonical full
HTTP request body—model, message, nonce, output budget, temperature 0, seed
17, stream/usage settings and thinking-off option—was byte-identical between
cold/warm and between MTP3/MTP6 for each pair. Every stream retained full raw
SSE privately before grading, required nonempty visible content, usage, finish
reason and `[DONE]`, and timestamped visible events monotonically for TTFT and
max gap.

## Primary result: warm end-to-end output throughput

Rate is server-reported completion tokens divided by full streamed request
wall time. Values below are medians of the three matched repetitions, expressed
as MTP6 relative to MTP3:

| Family | MTP6 vs MTP3 warm median |
|---|---:|
| Prose | −20.5% |
| Python code | −9.1% |
| Tool-workflow explanation | −18.9% |
| All warm matched pairs | **−14.9% median** |

The predefined retention rule required at least +5% median gain in two of the
three families, positive global warm median, no important family below −10%,
quality/safety passes, and no matched maximum-gap increase above 2 seconds.
Quality and safety passed and gaps met the limit, but performance did not.
Three pairs describe this bounded workload; they are not statistical certainty,
a long-prefill campaign, a soak, or a claim about all prompts.

The public [sanitized row set](results-mtp6-ab-repair-2026-10-18.sanitized.json)
contains all 36 real SSE request measurements (3 repetitions × 3 families ×
cold/warm × 2 profiles): TTFT, completion usage, end-to-end throughput, true
maximum visible-event gap, full canonical request hash, and finish flags. Raw
SSE/JSON, prompts, private runtime paths, assets, host IDs and credentials are
not published.

## Functional and safety gates

- The strict schema case returned exactly `{"pedido":"R-19","entrega":null}`
  on both profiles. The raw response was saved before parsing.
- The structured tool case made exactly one `registrar` call with
  `{"nombre":"foto","cantidad":2}` on both profiles. No tool was executed.
- The previous “grounding failed” boolean was not reused: it lacked raw output
  and could not distinguish a model error from a grader/contract problem.
- Both profile waves had zero native preemptions. Native speculative counters
  were recorded as descriptive deltas, not proof of causality.
- The host stayed above the 8 GiB available-RAM and 4 GiB swap floors. No fresh
  Xid, host OOM or `NV_ERR_NO_MEMORY` was observed in the run window.
- The final MTP3 direct chat canary completed with HTTP 200, nonempty content
  and `finish_reason=stop`; the API reported 200,000 context tokens. The
  persistent user service, router activity endpoint and selected MTP3 profile
  were read back after the switch. A basic direct vision-route smoke also
  passed after final handoff; it is not a general visual-quality or encoder-cache
  claim.

## Scope / alcance

Only speculative depth changed: MTP3 versus MTP6. The same retained container,
model/image, aliases, 200,000-token limit, four slots, FP8 KV, 0.8 memory
target, native expandable allocator, disk `io_uring` PLE, chat template and
thinking-off setting were used. There was no image/runtime/weight update or
cache-clearing experiment. `cached_tokens` was absent from the API and is
reported as null; correct OCR or a prefix metric does not prove visual-encoder
reuse.

Spanish: esta medición está orientada a flujos de postproducción y atención a
clientes audiovisuales. Mentoría técnica:
https://www.iaparafilmmakers.es/?utm_source=github&utm_medium=referral&utm_campaign=qwen_fp4_gb10&utm_content=mtp6_ab

English: this measurement is aimed at filmmaking post-production and client
workflows. Technical mentoring:
https://www.iaparafilmmakers.es/?utm_source=github&utm_medium=referral&utm_campaign=qwen_fp4_gb10&utm_content=mtp6_ab
