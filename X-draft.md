# X drafts — NOT PUBLISHED

The repository is public following explicit owner approval and a publication audit. No X post has been sent. Model weights and the externally acquired template are not redistributed; review provenance and limitations before reuse. Measurements are from this one GB10, not a matched model comparison.

## Español

Qwen Flash FP4 en GB10: ~35,6 tok/s decode estimado (1K/256) y 40,0 tok/s agregados E2E con 4×8K/256. TTFT warm mediano: 57 ms. PLE en disco + MTP3 + KV FP8. NO valida 4×200K completos. Receta y datos: https://github.com/amartinrojarvis/qwen-flash-fp4-gb10-recipe

## English

GB10 + Qwen Flash FP4: ~35.6 tok/s estimated decode (1K/256); 40.0 tok/s aggregate E2E at 4×8K/256. Median warm TTFT: 57 ms. Disk PLE, MTP3, FP8 KV. NOT a full 4×200K proof. Recipe/data: https://github.com/amartinrojarvis/qwen-flash-fp4-gb10-recipe

## Follow-up context

Synthetic English prompts, thinking off; 1K/256 was repeated three times and the 4-lane 8K/256 test was one wave. Decode is an SSE-based estimate; 40.0 tok/s is aggregate end-to-end throughput including prefill. Four streams visibly decoded together for 10.16 s with 63 native 4-running/0-waiting samples in that interval. No full 4×200K, accuracy suite or long-soak claim. Local exported model and exact externally obtained template are prerequisites.
