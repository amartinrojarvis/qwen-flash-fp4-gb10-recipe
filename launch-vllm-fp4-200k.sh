#!/usr/bin/env bash
# Portable, local-only launcher for the observed 200K / 4-slot profile.
# It does not pull, download, or convert model weights.
set -euo pipefail

RECIPE_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
IMAGE="${IMAGE:-eugr/spark-vllm-b12x@sha256:03a956544e9f9b4b7ba91690469fbe7848bdbef29a7d2e0f5788368467bb3595}"
MODEL_DIR="${MODEL_DIR:-/srv/models/qwen3.8-flash-next-fp4-local}"
HF_CACHE_DIR="${HF_CACHE_DIR:-/var/cache/qwen-fp4/huggingface}"
B12X_CACHE_DIR="${B12X_CACHE_DIR:-/var/cache/qwen-fp4/b12x}"
CHAT_TEMPLATE_PATH="${CHAT_TEMPLATE_PATH:-$RECIPE_DIR/config/qwen-chat-template.jinja}"
HOST="${HOST:-127.0.0.1}"
PORT="${PORT:-8000}"
SERVED_MODEL_NAME="${SERVED_MODEL_NAME:-vllmcritic}"
SERVED_MODEL_ALIAS="${SERVED_MODEL_ALIAS:-Qwen3.8-Flash-Next}"
SHM_SIZE="${SHM_SIZE:-64g}"
MEMORY_LIMIT="${MEMORY_LIMIT:-110g}"
MEMORY_SWAP="${MEMORY_SWAP:-120g}"
DRY_RUN=0

usage() {
  cat <<'EOF'
Usage: launch-vllm-fp4-200k.sh [--dry-run]

Override only paths and local endpoint settings with environment variables:
  MODEL_DIR, HF_CACHE_DIR, B12X_CACHE_DIR, CHAT_TEMPLATE_PATH, HOST, PORT
  IMAGE, SHM_SIZE, MEMORY_LIMIT, MEMORY_SWAP, SERVED_MODEL_NAME, SERVED_MODEL_ALIAS
EOF
}

if [[ "${1:-}" == "--dry-run" ]]; then DRY_RUN=1; shift; fi
if [[ $# -ne 0 ]]; then usage >&2; exit 64; fi

# Template bytes are intentionally not redistributed in this repository.
# Supply the separately licensed, hash-verified template described in provenance.md.
if [[ $DRY_RUN -eq 0 ]]; then
  [[ -f "$MODEL_DIR/config.json" ]] || { echo "MODEL_DIR must be a local verified export containing config.json: $MODEL_DIR" >&2; exit 2; }
  [[ -f "$CHAT_TEMPLATE_PATH" ]] || { echo "CHAT_TEMPLATE_PATH is required and must be an exact, separately obtained template: $CHAT_TEMPLATE_PATH" >&2; exit 2; }
  expected=e57684bae4156211a55473c5a63be976a405a37ab5be5ae0e5abf1df5349c4b2
  actual=$(sha256sum "$CHAT_TEMPLATE_PATH"); actual=${actual%% *}
  [[ "$actual" == "$expected" ]] || { echo "Chat template SHA-256 differs from the measured recipe." >&2; exit 2; }
  mkdir -p "$HF_CACHE_DIR" "$B12X_CACHE_DIR"
fi

args=(
  docker run --rm
  --gpus all
  --network host
  --ipc private
  --shm-size "$SHM_SIZE"
  --memory "$MEMORY_LIMIT"
  --memory-swap "$MEMORY_SWAP"
  --pids-limit 4096
  --cap-add IPC_LOCK
  --ulimit memlock=-1
  --ulimit nofile=1048576:1048576
  --ulimit stack=67108864:67108864
  --security-opt seccomp=unconfined
  --security-opt apparmor=unconfined
  -e VLLM_HOST_IP="$HOST"
  -e NCCL_IB_DISABLE=1
  -e NCCL_IGNORE_CPU_AFFINITY=1
  -e NCCL_SOCKET_IFNAME=lo
  -e GLOO_SOCKET_IFNAME=lo
  -e TP_SOCKET_IFNAME=lo
  -e CUTE_DSL_ARCH=sm_121a
  -e SAFETENSORS_FAST_GPU=1
  -e VLLM_SSM_CONV_STATE_LAYOUT=DS
  -e VLLM_USE_AOT_COMPILE=1
  -e VLLM_USE_V2_MODEL_RUNNER=1
  -e VLLM_MXFP8_LM_HEAD=1
  -e B12X_POLICY_MODE=auto
  -e B12X_W4A16_A4_PREFILL=1
  -e VLLM_B12X_MOE_FP4_LAYER_MAX_INPUT_SCALE=w13
  -e VLLM_B12X_MOE_FP4_FORCE_A16=1
  -e VLLM_PLE_TABLE_MEMORY=disk
  -e B12X_DISK_BACKEND=io_uring
  -e VLLM_USE_MEGA_AOT_ARTIFACT=1
  -e VLLM_ENGINE_READY_TIMEOUT_S=3600
  -e VLLM_WORKER_MULTIPROC_METHOD=spawn
  -e HF_HUB_OFFLINE=1
  -e PYTORCH_ALLOC_CONF=backend:native,expandable_segments:True
  -v "$MODEL_DIR:/models/qwen:ro"
  -v "$HF_CACHE_DIR:/root/.cache/huggingface"
  -v "$B12X_CACHE_DIR:/root/.cache/b12x"
  -v "$CHAT_TEMPLATE_PATH:/config/qwen-chat-template.jinja:ro"
  "$IMAGE"
  vllm serve /models/qwen
  --host "$HOST"
  --port "$PORT"
  --tensor-parallel-size 1
  --pipeline-parallel-size 1
  --mamba-cache-mode align
  --enable-prefix-caching
  --enable-chunked-prefill
  --dtype bfloat16
  --kv-cache-dtype fp8
  --quantization modelopt_mixed
  --block-size 16
  --load-format b12x
  --max-model-len 200000
  --max-num-seqs 4
  --max-num-batched-tokens 4096
  --speculative-config '{"method":"mtp","num_speculative_tokens":3}'
  --gdn-decode-kernel b12x
  --linear-backend b12x
  --moe-backend b12x
  --no-enable-flashinfer-autotune
  --mm-encoder-tp-mode data
  --reasoning-parser qwen3
  --tool-call-parser qwen3_xml
  --enable-auto-tool-choice
  --compilation-config '{"pass_config":{"fuse_act_quant":true}}'
  --gpu-memory-utilization 0.8
  --served-model-name "$SERVED_MODEL_NAME" "$SERVED_MODEL_ALIAS"
  --additional-config '{"ple_table_memory":"disk"}'
  --chat-template /config/qwen-chat-template.jinja
  --default-chat-template-kwargs '{"enable_thinking":false}'
)

if [[ $DRY_RUN -eq 1 ]]; then
  printf '%q ' "${args[@]}"; printf '\n'
else
  exec "${args[@]}"
fi
