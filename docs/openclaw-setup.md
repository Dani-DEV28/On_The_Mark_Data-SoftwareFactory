# OpenClaw + llama-swap Setup Guide

How to install OpenClaw on a machine and point it at the `otmd-ai` llama-swap
gateway (or any OpenAI-compatible endpoint like vLLM) instead of a cloud
provider. Verified 2026-07-26 with OpenClaw `2026.7.1-2` on macOS.

## Architecture

```
This machine                        otmd-ai server (Ubuntu 24.04)
┌─────────────────────┐   Tailscale   ┌──────────────────────────┐
│ OpenClaw gateway    │ ────────────▶ │ llama-swap :8000         │
│ 127.0.0.1:18789     │   HTTP /v1    │  ├─ qwen3.6-27b          │
│ (LaunchAgent/daemon)│               │  ├─ gemma-4-* / qwen3.6-*│
└─────────────────────┘               │  └─ nemotron-3-*         │
                                      └──────────────────────────┘
```

llama-swap loads/unloads models on demand, so the first request to a cold
model can take a while — set a generous `timeoutSeconds`.

## Prerequisites

1. **Node.js 22.22.3+, 24.15+, or 25.9+** (`node --version`). On macOS:
   `brew install node`.
2. **Tailscale** installed and logged into the tailnet, so the machine can
   reach the model server. Verify:
   ```bash
   curl -s http://otmd-ai.tail52ca70.ts.net:8000/v1/models
   ```
   You should get a JSON list of models. This same list is what you'll
   register in the OpenClaw config below.

## 1. Install OpenClaw

```bash
curl -fsSL https://openclaw.ai/install.sh | bash
```

(Windows: `iwr -useb https://openclaw.ai/install.ps1 | iex`)

This installs the `openclaw` CLI via npm. The interactive wizard
(`openclaw onboard --install-daemon`) assumes a cloud provider API key; since
we use a local endpoint, skip it and write the config by hand instead.

## 2. Write the config

Create `~/.openclaw/openclaw.json`:

```json
{
  "agents": {
    "defaults": {
      "model": { "primary": "llamaswap/qwen3.6-27b" }
    }
  },
  "models": {
    "mode": "merge",
    "providers": {
      "llamaswap": {
        "baseUrl": "http://otmd-ai.tail52ca70.ts.net:8000/v1",
        "apiKey": "sk-local",
        "api": "openai-completions",
        "timeoutSeconds": 600,
        "request": { "allowPrivateNetwork": true },
        "models": [
          {
            "id": "qwen3.6-27b",
            "name": "Qwen 3.6 27B",
            "reasoning": false,
            "input": ["text"],
            "cost": { "input": 0, "output": 0, "cacheRead": 0, "cacheWrite": 0 },
            "contextWindow": 120000,
            "maxTokens": 8192
          }
        ]
      }
    }
  }
}
```

Add one entry per model you want available — the `id` must exactly match the
id from `/v1/models`. Current models on otmd-ai: `qwen3.6-27b`,
`qwen3.6-35b-a3b`, `gemma-4-12b`, `gemma-4-26b-a4b`, `gemma-4-31b`,
`nemotron-3-nano-30b-a3b`, `nemotron-3-super-120b-a12b` (set
`"reasoning": true` on the nemotron-super).

Gotchas learned the hard way:

- The default model reference is `<provider-key>/<model-id>` — the prefix
  must match the key under `providers` (`llamaswap/...` here), or OpenClaw
  will never route to your endpoint.
- `baseUrl` must include `/v1`.
- `request.allowPrivateNetwork: true` is required for non-loopback private
  endpoints (tailnet/LAN hosts).
- `apiKey` is required by the schema even though llama-swap ignores it — any
  string works.
- There is no `auth` key in provider blocks; use `apiKey`.

## 3. Install the daemon and start the gateway

```bash
openclaw daemon install
```

This auto-generates a gateway token, appends a `gateway` block to the config,
and installs a LaunchAgent (macOS) / systemd unit (Linux) so the gateway runs
on login. Give it ~10 seconds to warm up, then:

```bash
openclaw gateway status
```

Expected: `Runtime: running`, `Connectivity probe: ok`, listening on
`127.0.0.1:18789`.

## 4. Verify end to end

```bash
openclaw models list | grep llamaswap   # all your models, default marked
openclaw agent --agent main --message "Reply with exactly: OK from llama-swap"
```

The first message to a cold model is slow while llama-swap loads it. Then:

```bash
openclaw dashboard   # opens the Control UI in the browser
```

## Troubleshooting

- **Gateway port 18789 not listening right after install** — normal warm-up;
  re-run `openclaw gateway status` after a few seconds.
- **Logs**: `~/Library/Logs/openclaw/gateway.log` (macOS) and
  `~/.openclaw/logs/`.
- **Timeouts on big models** — raise `timeoutSeconds`; llama-swap's own
  `healthCheckTimeout` on the server is 1800s, so model loads can legitimately
  take minutes.
- **`No target session selected`** when messaging — pass `--agent main`.

## Server side (already done on otmd-ai, for reference)

llama-swap runs as a systemd service (`llama-swap.service`) listening on
`:8000`, config at `/root/llama-swap/config.yaml`. Nothing server-side needs
to change to add a new OpenClaw client — just make sure the client machine is
on the tailnet.
