# Qwen Flash FP4 on GB10: 4 × 200K vLLM recipe

Portable reconstruction of the **observed effective 200K profile**, distributed without weights, caches, credentials or host identities. Measured results and their limits are recorded in [results.md](results.md) and the [long-context campaign](results-long-context-2026-10-17.md). It is a local-export launcher, not a Hugging Face download recipe and not a production deployment instruction.

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
