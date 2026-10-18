# Qwen Flash FP4 on GB10: 4 × 200K vLLM recipe

Portable reconstruction of the **observed effective 200K profile**, distributed without weights, caches, credentials or host identities. Measured results and their limits are recorded in [results.md](results.md), the [initial long-context campaign](results-long-context-2026-10-17.md), and the [full-context completion](results-full-context-completion-2026-10-17.md). It is a local-export launcher, not a Hugging Face download recipe and not a production deployment instruction.

## Contexto / Context

### Español — por qué estoy probando vLLM

Soy **Alberto Martín**, filmmaker y creador de [IA para Filmmakers](https://www.iaparafilmmakers.es/?utm_source=github&utm_medium=referral&utm_campaign=qwen_fp4_gb10&utm_content=readme_es). Suelo usar **TensorFold** para trabajar con IA local. En mi día a día mezclo código, herramientas, documentos, referencias visuales y conversaciones largas con fotos o fotogramas; me importa conservar el contexto y poder seguir trabajando sin releer todo a cada turno.

A fecha de la revisión del **18 de octubre de 2026**, la receta de Qwen Flash Next para TensorFold que estoy siguiendo documenta una limitación relevante: los prompts con imágenes o vídeo **no se conservan para reutilización de prefijo**, por lo que se vuelven a procesar en cada turno con medios. El [README del proyecto lo explica expresamente](https://github.com/MiaAI-Lab/Qwen3.8-Flash-Next-Single-DGX-Spark-TensorFold/blob/06df57f8a76c74fec908c87fdbc4dd702ff598f9/README.md#L330-L333), y su [parche de serving excluye las solicitudes con medios de la búsqueda de caché](https://github.com/MiaAI-Lab/Qwen3.8-Flash-Next-Single-DGX-Spark-TensorFold/blob/06df57f8a76c74fec908c87fdbc4dd702ff598f9/patches/0007-serving.patch#L68-L74). Hablo de esa receta y revisión concretas, no de todas las versiones de TensorFold ni de una incapacidad para entender imágenes.

Para mi trabajo audiovisual estoy probando **vLLM como una alternativa que parece más robusta para este flujo**: historiales largos, herramientas, entrada visual y varias conversaciones activas. Aquí comparto la receta y las pruebas, incluidos fallos del evaluador y resultados inconclusos. Los [casos visuales corregidos](results-multimodal-cache-v2-2026-10-18.md) comprobaron seguimiento e invalidación al cambiar imágenes, pero **todavía no demuestran reutilización del encoder o de la caché visual**. Tampoco hay una comparación equivalente que pruebe superioridad universal frente a TensorFold. MTP6 sigue pendiente, sin resultados inventados.

**¿Quieres aplicar IA a un problema real de tu negocio audiovisual?** En [mi asesoría y mentoría 1:1 para filmmakers, videógrafos, fotógrafos y pequeños equipos](https://www.iaparafilmmakers.es/?utm_source=github&utm_medium=referral&utm_campaign=qwen_fp4_gb10&utm_content=mentoria_es) trabajamos sobre tu caso y construimos un sistema que encaje con tu forma de trabajar.

### English — why I am testing vLLM

I'm **Alberto Martín**, a filmmaker and the creator of [IA para Filmmakers](https://www.iaparafilmmakers.es/?utm_source=github&utm_medium=referral&utm_campaign=qwen_fp4_gb10&utm_content=readme_en). I normally use **TensorFold** for local AI. My filmmaking workflow combines code, tools, documents, visual references and long conversations containing photos or frames. Context continuity and dependable interaction matter as much as headline throughput.

As checked on **18 October 2026**, the particular Qwen Flash Next TensorFold recipe I follow documents a relevant limitation: image/video prompts **are not retained for prefix reuse**, so media-bearing turns process them again. See the [explicit upstream README statement](https://github.com/MiaAI-Lab/Qwen3.8-Flash-Next-Single-DGX-Spark-TensorFold/blob/06df57f8a76c74fec908c87fdbc4dd702ff598f9/README.md#L330-L333) and the [serving patch's media exclusion from cache lookup](https://github.com/MiaAI-Lab/Qwen3.8-Flash-Next-Single-DGX-Spark-TensorFold/blob/06df57f8a76c74fec908c87fdbc4dd702ff598f9/patches/0007-serving.patch#L68-L74). This is a statement about that pinned recipe, not every TensorFold version or its ability to understand images.

For my audiovisual work I am evaluating **vLLM as a potentially more robust fit for this workflow**. This repository records the configuration, measurements, harness corrections and remaining unknowns. The [corrected visual tests](results-multimodal-cache-v2-2026-10-18.md) verified history follow-up and changed-image integrity, but **do not establish visual-encoder or media-cache reuse**. This is not a matched proof that vLLM is universally better than TensorFold. MTP6 has not been run.

**Interested in applying AI to your audiovisual business?** My [practical 1:1 AI advisory and mentoring for filmmakers and small creative teams](https://www.iaparafilmmakers.es/?utm_source=github&utm_medium=referral&utm_campaign=qwen_fp4_gb10&utm_content=mentoring_en) starts with a real problem and a system that fits your workflow. The linked service details are in Spanish.

## Results index / Índice de resultados

- [Initial serving measurements](results.md)
- [Long-context campaign and audited fixture limits](results-long-context-2026-10-17.md)
- [Near-ceiling C2/C3/C4 completion](results-full-context-completion-2026-10-17.md)
- [Event-driven long-history interactivity](results-interactivity-2026-10-18.md)
- [Multimodal integrity: corrected v2](results-multimodal-cache-v2-2026-10-18.md)
- [Earlier multimodal phase and correction notice](results-multimodal-cache-phase1-2026-10-18.md)
- [Optimization research](optimization-research-2026-10-18.md) and [MTP6 status: not run](results-mtp6-admission-2026-10-18.md)

Technical results and service links are separate: the tests are not a guarantee of client outcomes or endorsements from upstream authors.

## What is pinned

- Image: `eugr/spark-vllm-b12x@sha256:03a956544e9f9b4b7ba91690469fbe7848bdbef29a7d2e0f5788368467bb3595` (`linux/arm64` observed).
- Runtime: vLLM `0.1.dev21830+g8244d1c44.d20261015`; PyTorch `2.13.0+cu130`; CUDA `13.0` observed in the pinned image.
- Upstream recipe source: `https://github.com/eugr/spark-vllm-docker.git` at `0bdc9c94cd89843e1c8f7d7b33df2d5bc746c03d`.
- Model logical ID/revision: `nvidia/Qwen3.8-Flash-Next-FP4-Local` / `b9ce18a6887e18c089fdea8509a33e63429a3300`.
- Effective flags: 200,000 maximum request tokens, 4 sequences, MTP 3, FP8 KV cache, `modelopt_mixed`, PLE disk mode via `io_uring`, native expandable PyTorch allocator.

The source 200K profile repeated some options. vLLM uses the last occurrence: `--max-num-seqs 4`, FP8 KV cache, and MTP with 3 speculative tokens. This recipe writes each effective option once.

## Physical requirements

This is a narrow hardware/runtime recipe, not a capacity guarantee:

- NVIDIA GB10 / Blackwell-class UMA system with **128 GB UMA**.
- Linux `arm64`, NVIDIA driver compatible with the pinned CUDA 13 image, Docker with GPU support.
- Fast local NVMe: the model export, HF metadata cache, and B12X JIT cache must be on local persistent storage. Disk PLE uses `io_uring`; do not put its working storage on a network filesystem.
- A local, complete, verified FP4 export. The observed deployment used a roughly 102 GB physical export; do not assume a model ID alone recreates an exported or converted directory.
- 64 GB `/dev/shm` and the observed 110 GB memory / 120 GB memory+swap container limits are defaults in the launcher. Validate against the target host before use.

## Required local model export

Set `MODEL_DIR` to a directory that contains the complete model export and at least `config.json`, tokenizer files, processor files, safetensors shards, and the safetensors index. The launcher mounts it read-only at `/models/qwen` and starts `vllm serve /models/qwen`.

`HF_HUB_OFFLINE=1` is deliberate. This prevents an unpinned network fallback. A model ID plus revision is provenance, **not** a promise that a fresh Hugging Face fetch reproduces an artisanal/local export.

The chat template is not bundled because this package does not establish redistribution permission for the observed template. Obtain it from an authorized source, verify its SHA-256 against `provenance.md`, then set `CHAT_TEMPLATE_PATH`. Do not substitute a visually similar template.

## Prepare and run

```bash
cd qwen-flash-fp4-gb10-recipe
chmod +x launch-vllm-fp4-200k.sh

# CPU-only inspection; launches nothing.
./launch-vllm-fp4-200k.sh --dry-run

# Example paths are local placeholders, not a prescribed filesystem layout.
MODEL_DIR=/srv/models/qwen3.8-flash-next-fp4-local \
HF_CACHE_DIR=/var/cache/qwen-fp4/huggingface \
B12X_CACHE_DIR=/var/cache/qwen-fp4/b12x \
CHAT_TEMPLATE_PATH=/srv/model-config/qwen-chat-template.jinja \
HOST=127.0.0.1 PORT=8000 \
./launch-vllm-fp4-200k.sh
```

The launcher uses host networking, binds vLLM to loopback by default, retains `--ipc private` with `--shm-size 64g`, adds only `IPC_LOCK`, and does **not** use `--privileged`. It preserves the observed `seccomp=unconfined` and `apparmor=unconfined` settings because this B12X/`io_uring` environment was observed with them. Review those exceptions under the target's security policy; they are compatibility settings, not a blanket security recommendation.

## Re-run the measurements against an already healthy backend

```bash
python3 benchmarks/run_benchmark.py --selftest
python3 benchmarks/run_benchmark.py \
  --base-url http://127.0.0.1:8000 --model vllmcritic \
  --output-dir benchmark-output/$(date +%Y%m%dT%H%M%S)
python3 benchmarks/vision_smoke.py --base-url http://127.0.0.1:8000 --model vllmcritic
```

The producer uses synthetic, tokenizer-calibrated prompts and preserves SSE/usage. A fresh output directory is required. `--router-base-url` and `--service-ready-file` are optional observation inputs for deployments that have those interfaces; omitted evidence remains unknown. It does not stop other applications, flush caches, swap models, or install a watchdog. Use an existing memory/fatal-event monitor and stop the experiment if the endpoint or host becomes unhealthy. Cold prefix versus immediate exact replay is defined in [methodology.md](methodology.md).

The OCR image is a generated synthetic text fixture (`K7M4`), not a user's photograph. It tests one simple capability only. Repository measurements used the initial producer plus the documented matched-8K supplement; the portable runner now includes that C1 pair in its main matrix.

## Important limits

- “4 × 200K” is a configured scheduling target, not proof of four simultaneous fully populated 200K requests. It must be measured separately.
- The recorded benchmark ran against the actual monitored deployment. This portable launcher itself has only CPU/dry-run verification and requires separately acquired assets; it is not a clean-host GPU reproduction. It does not install the private production systemd/watchdog integration.
- Startup logs from the inspected environment show a historical `262144` initialization as well as the current effective 200K argv. This package follows the current profile’s final argv/options and does not relabel the historical log as 200K proof.
- Basic JSON/tool/grounding fixtures and one simple OCR image passed. General vision quality and video remain unqualified; support declared by model metadata is not a benchmark result.
- The pinned runtime includes vendor/community B12X modifications. Changing image digest, model export, driver, cache location, allocator, or flags invalidates equivalence; rerun the methodology.

See `provenance.md`, `methodology.md`, `results.md`, `X-draft.md`, and `identity.json`.

## Latest bounded trial
- [MTP3 vs MTP6 bounded A/B (2026-10-18)](results-mtp6-ab-2026-10-18.md) — MTP6 not retained; MTP3 active.
