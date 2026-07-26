#!/usr/bin/env bash
# Software Factory — GB10 Serving Plane Setup (vLLM + llama-swap)
# Run this ON the GB10 (DGX Spark, aarch64 Grace + Blackwell sm_121).
# Usage: ./scripts/setup-gb10.sh
#
# Installs:
#   1. vLLM  — native pip install into a dedicated venv (falls back to
#              the NVIDIA NGC vLLM container if the wheel path fails)
#   2. llama-swap — latest linux_arm64 release from GitHub

set -euo pipefail

# Canonical GB10 layout (override via env if needed)
FACTORY_ROOT="${FACTORY_ROOT:-$HOME/factory/software-factory}"
UPSTREAM_ROOT="${UPSTREAM_ROOT:-$HOME/factory/upstream}"

OPENCLAW_SRC="$UPSTREAM_ROOT/OpenClaw"
OPENSHELL_SRC="$UPSTREAM_ROOT/OpenShell"
NEMOCLAW_SRC="$UPSTREAM_ROOT/NemoClaw"

# If run from a repo checkout that isn't at FACTORY_ROOT, prefer the checkout
SCRIPT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
if [ ! -d "$FACTORY_ROOT" ]; then
    FACTORY_ROOT="$SCRIPT_ROOT"
fi

VENV_DIR="$FACTORY_ROOT/.venv-vllm"
BIN_DIR="$HOME/.local/bin"
LLAMA_SWAP_REPO="mostlygeek/llama-swap"

mkdir -p "$UPSTREAM_ROOT"

echo "=== GB10 Serving Plane Setup ==="
echo "Factory root:  $FACTORY_ROOT"
echo "Upstream root: $UPSTREAM_ROOT"

# 1. Sanity checks — this script targets the GB10, not the MBP
echo ""
echo "--- Checking Platform ---"
if [ "$(uname -s)" != "Linux" ] || [ "$(uname -m)" != "aarch64" ]; then
    echo "WARNING: expected Linux/aarch64 (GB10), got $(uname -s)/$(uname -m)"
    echo "         Continuing anyway, but installs may pull wrong-arch binaries."
fi
command -v curl >/dev/null 2>&1 || { echo "ERROR: curl not found"; exit 1; }
command -v python3 >/dev/null 2>&1 || { echo "ERROR: python3 not found"; exit 1; }
if command -v nvidia-smi >/dev/null 2>&1; then
    nvidia-smi --query-gpu=name,memory.total,compute_cap --format=csv,noheader || true
else
    echo "WARNING: nvidia-smi not found — GPU driver may not be installed"
fi

mkdir -p "$BIN_DIR"
case ":$PATH:" in
    *":$BIN_DIR:"*) ;;
    *) export PATH="$BIN_DIR:$PATH"
       echo "NOTE: add 'export PATH=\"$BIN_DIR:\$PATH\"' to your shell rc" ;;
esac

# 2. Install uv (fast, handles the aarch64 CUDA wheel index cleanly)
echo ""
echo "--- Installing uv ---"
if command -v uv >/dev/null 2>&1; then
    echo "uv already installed"
else
    curl -LsSf https://astral.sh/uv/install.sh | sh
    export PATH="$HOME/.local/bin:$PATH"
fi

# 3. Install vLLM
#    GB10 is Blackwell sm_121; needs a recent vLLM with CUDA 12.9+ aarch64
#    wheels. If the native install fails, fall back to NVIDIA's container.
echo ""
echo "--- Installing vLLM ---"
VLLM_OK=0
if [ -x "$VENV_DIR/bin/vllm" ] && "$VENV_DIR/bin/vllm" --version >/dev/null 2>&1; then
    echo "vLLM already installed: $("$VENV_DIR/bin/vllm" --version 2>/dev/null | tail -1)"
    VLLM_OK=1
else
    uv venv "$VENV_DIR" --python 3.12 || uv venv "$VENV_DIR"
    if uv pip install --python "$VENV_DIR/bin/python" -U vllm \
        --torch-backend=auto; then
        if "$VENV_DIR/bin/python" -c "import vllm; print('vLLM', vllm.__version__)"; then
            VLLM_OK=1
        fi
    fi
    if [ "$VLLM_OK" -eq 1 ]; then
        ln -sf "$VENV_DIR/bin/vllm" "$BIN_DIR/vllm"
        echo "vLLM installed natively → $BIN_DIR/vllm"
    else
        echo "Native vLLM install failed — falling back to NGC container..."
        if command -v docker >/dev/null 2>&1; then
            docker pull nvcr.io/nvidia/vllm:latest && VLLM_OK=1 || true
            if [ "$VLLM_OK" -eq 1 ]; then
                # Wrapper so serve.sh's `vllm serve ...` works transparently
                cat > "$BIN_DIR/vllm" <<'EOF'
#!/usr/bin/env bash
# vLLM via NGC container (native install unavailable on this GB10)
exec docker run --rm --gpus all --ipc=host --network host \
    -v "$HOME/.cache/huggingface:/root/.cache/huggingface" \
    -v "$HOME/models:/models" \
    nvcr.io/nvidia/vllm:latest vllm "$@"
EOF
                chmod +x "$BIN_DIR/vllm"
                echo "vLLM available via container wrapper → $BIN_DIR/vllm"
            fi
        else
            echo "WARNING: docker not found — vLLM unavailable, serve.sh will fall back to Ollama"
        fi
    fi
fi

# 4. Install llama-swap (single Go binary, linux_arm64 release)
echo ""
echo "--- Installing llama-swap ---"
if command -v llama-swap >/dev/null 2>&1; then
    echo "llama-swap already installed: $(llama-swap --version 2>/dev/null || echo ok)"
else
    ASSET_URL="$(curl -fsSL "https://api.github.com/repos/$LLAMA_SWAP_REPO/releases/latest" \
        | grep -o '"browser_download_url": *"[^"]*linux_arm64[^"]*"' \
        | head -1 | cut -d'"' -f4 || true)"
    if [ -n "$ASSET_URL" ]; then
        echo "Downloading $ASSET_URL"
        TMP_DIR="$(mktemp -d)"
        curl -fsSL "$ASSET_URL" -o "$TMP_DIR/llama-swap.tar.gz"
        tar -xzf "$TMP_DIR/llama-swap.tar.gz" -C "$TMP_DIR"
        install -m 0755 "$TMP_DIR/llama-swap" "$BIN_DIR/llama-swap"
        rm -rf "$TMP_DIR"
        echo "llama-swap installed → $BIN_DIR/llama-swap"
    else
        echo "WARNING: could not resolve llama-swap linux_arm64 release — install manually:"
        echo "         https://github.com/$LLAMA_SWAP_REPO/releases"
    fi
fi

# 5. Verify
echo ""
echo "--- Verifying ---"
command -v vllm >/dev/null 2>&1 && echo "vllm:       $(command -v vllm)" || echo "vllm:       MISSING"
command -v llama-swap >/dev/null 2>&1 && echo "llama-swap: $(command -v llama-swap)" || echo "llama-swap: MISSING"
CONFIG="$FACTORY_ROOT/config/llama-swap/config.yaml"
[ -f "$CONFIG" ] && echo "config:     $CONFIG" || echo "config:     MISSING ($CONFIG)"

echo ""
echo "=== GB10 Setup Complete ==="
echo "Next: run ./scripts/serve.sh to start the serving plane"
