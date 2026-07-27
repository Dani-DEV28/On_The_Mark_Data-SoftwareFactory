# OpenShell Setup (Sandbox Backend for OpenClaw)

How to install NVIDIA OpenShell on a Mac and wire it in as OpenClaw's sandbox
backend, so agent tool calls (exec/read/write/edit) run inside isolated
MicroVMs instead of directly on the host. Verified 2026-07-26 with OpenShell
`0.0.91` and OpenClaw `2026.7.1-2` on macOS (Apple Silicon only — Intel Macs
are not supported). Companion doc: [openclaw-setup.md](openclaw-setup.md).

## Architecture

```
OpenClaw gateway (127.0.0.1:18789)
  └─ @openclaw/openshell-sandbox plugin
       └─ openshell CLI ──mTLS──▶ OpenShell gateway (127.0.0.1:17670)
                                     └─ vm driver (Hypervisor.framework)
                                          └─ MicroVM sandboxes
```

No cloud account is required — OpenShell is open source (NVIDIA) and the
gateway runs entirely locally.

## 1. Install the OpenShell CLI + gateway

Official one-liner (installs CLI + gateway via Homebrew on macOS, deb/rpm on
Linux, and registers the local gateway):

```bash
curl -LsSf https://raw.githubusercontent.com/NVIDIA/OpenShell/main/install.sh | sh
```

If you prefer explicit steps (what the script does on macOS): it stages the
`openshell.rb` formula from the GitHub release into a local tap
(`openshell/local`), runs `brew install`, then `brew services start` the
gateway. The CLI alone can also be installed with `uv tool install -U openshell`,
but the gateway daemon only comes from the brew formula / OS packages.

## 2. Configure the MicroVM compute driver (macOS)

On macOS with no Docker/Podman, use the built-in MicroVM driver
(Hypervisor.framework). **It is never auto-detected** — without this the
gateway crash-loops with "no compute driver configured":

```bash
# The brew service wrapper sources this env file on start
printf 'OPENSHELL_DRIVERS=vm\n' > ~/.config/openshell/gateway.env
brew services restart openshell/local/openshell
```

The vm driver also needs `e2fsprogs` to build sandbox root filesystems:

```bash
brew install e2fsprogs
```

On Linux with Docker or Podman installed, drivers auto-detect and neither
step is needed.

## 3. Register and verify the gateway

The installer usually registers the gateway automatically. If not:

```bash
openshell gateway add https://127.0.0.1:17670 --local --name openshell
```

Verify:

```bash
openshell status
# Server: https://127.0.0.1:17670, Status: Connected,
# Authentication: Authenticated (mTLS transport), Version: 0.0.91
```

Smoke-test a sandbox (first run downloads the VM image — takes a while):

```bash
openshell sandbox create --from base --name smoke-test
openshell sandbox list
openshell sandbox delete smoke-test
```

Logs if anything fails: `/opt/homebrew/var/log/openshell/openshell-gateway.{out,err}.log`
and `openshell doctor`.

## 4. Wire into OpenClaw

Install the plugin:

```bash
openclaw plugins install @openclaw/openshell-sandbox
```

(The plugin's config key is `openshell`, not the npm package name.)

Add the sandbox block to `~/.openclaw/openclaw.json`:

```json
{
  "agents": {
    "defaults": {
      "sandbox": {
        "mode": "all",
        "backend": "openshell",
        "scope": "session",
        "workspaceAccess": "rw"
      }
    }
  }
}
```

Set the plugin config **via the CLI, not by hand-editing the JSON** — hand-
edited `plugins.entries.*.config` keys were silently stripped on reload in my
testing, leaving the plugin on defaults:

```bash
openclaw config set plugins.entries.openshell.config.from base
openclaw config set plugins.entries.openshell.config.mode remote
openclaw config set plugins.allow '["openshell"]' --json   # pin plugin trust
```

Notes:

- `from: base` — the default `openclaw` sandbox image fails to provision on
  the macOS vm driver (see gotchas); `base` works and is enough for exec.
- `mode: "remote"` seeds the workspace once and operates on remote files —
  best for long-running agents. `"mirror"` syncs local↔remote each turn —
  better for interactive dev, more overhead.
- `scope: "session"` gives each session its own sandbox.

## 5. Patch the sandbox name length (macOS vm driver)

The OpenShell vm driver caps sandbox names at **19 characters**, but the
plugin generates names like `openclaw-agent-main-main-1b41619c` (33 chars),
so every exec fails with `name exceeds maximum length (33 > 19)`. Until fixed
upstream, patch the plugin's name builder (find the install dir via
`openclaw plugins inspect openshell`):

```bash
# in .../node_modules/@openclaw/openshell-sandbox/dist/index.js, in
# buildOpenShellSandboxName, replace:
#   return `openclaw-${safe || "session"}-${hash.toString(16).slice(0, 8)}`;
# with:
#   return `oc-${(safe || "session").slice(0, 7).replace(/-+$/, "")}-${hash.toString(16).slice(0, 8)}`.slice(0, 19);
```

This keeps the uniqueness hash, producing names like `oc-agent-m-1b41619c`.
**The patch is overwritten whenever the plugin is reinstalled/updated** —
re-apply it, or check whether upstream has fixed the limit by then.

## 6. Restart and verify end to end

```bash
openclaw gateway restart
openclaw sandbox explain   # expect: runtime: sandboxed, backend: openshell
openclaw agent --agent main --message "Use your exec tool to run: uname -a"
# expect a Linux aarch64 uname line from inside the MicroVM
openclaw sandbox list      # shows the per-session sandbox runtime
```

If config changes don't seem to take effect (e.g. sandboxes keep using the
old image), stale runtime entries pin the previous settings — clear them:

```bash
openclaw sandbox recreate --all
openshell sandbox delete <name>   # delete any Error-phase sandboxes too
```

`openclaw sandbox explain` also prints the tool allow/deny policy the sandbox
enforces (exec/read/write/edit allowed by default; messaging/browser tools
denied inside the sandbox).

## Gotchas learned the hard way

- **Gateway crash-loop on macOS**: `OPENSHELL_DRIVERS=vm` must be set in
  `~/.config/openshell/gateway.env` (step 2) — vm is never auto-detected.
- **`mke2fs not found`** on sandbox create → `brew install e2fsprogs`.
- **`name exceeds maximum length (33 > 19)`** → plugin name patch (step 5).
- **`FATAL: prepared image disk missing /image-rootfs`** in the VM console
  log (`~/.local/state/openshell/vm-driver/sandboxes/<id>/rootfs-console.log`)
  with the sandbox stuck in `Error` phase: the `openclaw` image's rootfs
  conversion is broken on the macOS vm driver without a local container
  engine. Use `from: base` (step 4). If a bad build is cached, also delete the
  matching `sandbox-prepared-rootfs-*` dir under
  `~/.local/state/openshell/vm-driver/images/`.
- **Plugin config silently ignored** → always set it with
  `openclaw config set`, then verify with `openclaw config get plugins`.
- **First sandbox create is slow** (VM image download); later creates are fast.
- The OpenShell gateway is loopback-only with mTLS by default; the OpenClaw
  gateway must run on the same host as the `openshell` CLI.
