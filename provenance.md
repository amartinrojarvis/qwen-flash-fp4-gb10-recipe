# Provenance and licensing

## Runtime identity observed read-only

| Item | Value |
|---|---|
| Model logical ID | `nvidia/Qwen3.8-Flash-Next-FP4-Local` |
| Immutable model revision | `b9ce18a6887e18c089fdea8509a33e63429a3300` |
| Base model stated by the local model card | `Qwen/Qwen3.8-Flash-Next` |
| Image | `eugr/spark-vllm-b12x@sha256:03a956544e9f9b4b7ba91690469fbe7848bdbef29a7d2e0f5788368467bb3595` |
| Image platform observed | `linux/arm64` |
| Local image ID observed | `sha256:a7f76ae9f18c7701c9cde5f72c606393d9a21ca94dd8e53b27589935f64fcbe2` |
| vLLM | `0.1.dev21830+g8244d1c44.d20261015` |
| PyTorch / CUDA | `2.13.0+cu130` / `13.0` |
| Recipe upstream | `https://github.com/eugr/spark-vllm-docker.git` |
| Recipe source commit | `0bdc9c94cd89843e1c8f7d7b33df2d5bc746c03d` |

The upstream source license at that commit is MIT (copyright Eugene Rakhmatulin). This package contains no upstream source code, image content, model weights, or copied model-card text. The upstream license does not grant rights to the model, image, dependencies, or third-party patches; retain their own terms.

## Model terms

The inspected local model card identifies the model download terms as the NVIDIA Open Model Agreement and states that the base model is governed by Qwen Community License 1.0. These are reported provenance facts, not relicensing or legal advice. Obtain and accept current terms from the official model sources before downloading, using, redistributing, or publishing derivatives.

## Local export / conversion status

The deployment mounted a separate read-only local model export rather than serving directly from a network model ID. Metadata in that export matches the logical ID/revision above and identifies Model Optimizer mixed precision (`modelopt`, `MIXED_PRECISION`) with NVFP4 and MXFP8 components.

No self-contained conversion command, conversion repository, or reproducible source-to-export manifest was found in the inspected runtime/profile metadata. Therefore this repository does **not** claim that `MODEL_ID@REVISION` can regenerate `MODEL_DIR`, and it does not supply weights or conversion tooling. Treat the local export as a required physical input and record its authorized acquisition and integrity evidence in the consuming environment.

## Chat-template handling

Observed runtime template digest:

```text
SHA-256: e57684bae4156211a55473c5a63be976a405a37ab5be5ae0e5abf1df5349c4b2
bytes:   28234
```

The template bytes are intentionally omitted. Their originating repository, explicit license, and redistribution permission were not established by the readonly inspection. Obtain the exact authorized artifact separately, hash it, and only then set `CHAT_TEMPLATE_PATH`. No URL is provided because a mutable or guessed URL would not be a reproducible source.

## Vendor/runtime modifications

The pinned upstream source commit contains B12X/FlashInfer/vLLM patches and Qwen3.8 loader work. The observed image is digest-pinned but its build recipe is not reproduced here. This package makes no claim that `custom_runtime_patches: []` in the deployment profile means the image is unmodified; source inspection found vendor B12X-related changes in the upstream build tree. The image digest is the operational pin.
