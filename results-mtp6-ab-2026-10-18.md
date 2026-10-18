# MTP3 vs MTP6 bounded A/B — 2026-10-18

## Decision / decisión

**MTP6 was not retained. MTP3 remains the active, persistent 4×200K profile.**

A real same-container production-controller switch ran MTP6 first, then MTP3
with the same model, image, aliases, 200,000 total-token context, four slots,
FP8 KV, 0.8 GPU-memory target, PLE disk/io_uring, template and thinking-off
setting. The only serving delta was the final effective MTP setting: 3 vs 6.

The predeclared retention rule required at least a 5% warm end-to-end gain in
2/3 content families, a positive median, no family worse than 10%, and quality
and safety gates. MTP6 improved prose (+33.5%) and code (+30.4%) but regressed
the tool-workflow explanation (-18.5%). The grounded-null probe also failed
for both arms. It therefore did **not** qualify for retention; this is not a
claim that MTP6 is generally slower.

## Measured warm throughput (completed output tokens / full request wall time)

| Spanish content family | MTP3 tok/s | MTP6 tok/s | MTP6 relative |
|---|---:|---:|---:|
| Prose | 18.50 | 24.70 | +33.5% |
| Python code | 31.38 | 40.93 | +30.4% |
| Tool-workflow explanation | 41.95 | 34.20 | −18.5% |

Each arm used real OpenAI-compatible SSE, required visible output, terminal
finish reason, usage and `[DONE]`. The test is one bounded wave, not a soak,
statistical certification, long-prefill result, or a claim about four full
200K resident contexts. `cached_tokens` was absent and remains null.

## Gates observed

- Physical MTP6 argv was observed before its requests; physical MTP3 argv was
  observed after rollback.
- JSON and exact tool-call probes passed in both arms. The grounded-null probe
  failed in both arms, so the quality gate failed.
- No preemptions were recorded in either bounded wave.
- Host memory and swap floors remained above 8 GiB and 4 GiB respectively;
  no fresh Xid, host OOM, or `NV_ERR_NO_MEMORY` was found in the trial window.
- The normal controller rollback left MTP3 active; `/v1/models` reported a
  200,000 token limit and the dashboard read the same MTP3 profile.

## Reproducibility scope

The private raw evidence, model/template, container binding and service
metadata are intentionally not published. Public benchmark scripts remain
portable protocol/CPU-checked tooling; a clean-host GPU reproduction is not
claimed. Source code retains upstream rights; weights and templates are omitted.

Spanish: este experimento está orientado a flujos de postproducción y atención
a clientes audiovisuales. Mentoría técnica: https://www.iaparafilmmakers.es/UTM

English: this experiment is aimed at filmmaking post-production and client
workflows. Technical mentoring: https://www.iaparafilmmakers.es/UTM
