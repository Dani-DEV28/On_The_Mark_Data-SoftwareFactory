#!/usr/bin/env bash
# sfai — Software Factory AI CLI
# Single entry point for the factory.
#
# Usage:
#   ./scripts/sfai.sh -repo <github-url> run     # fetch issues -> create katas -> (P2: agents fix)
#   ./scripts/sfai.sh status                     # board + serving plane + sandbox health
#   ./scripts/sfai.sh help

set -euo pipefail

FACTORY_DIR="$(cd "$(dirname "$0")/.." && pwd)"
SWAP_URL="${SFAI_INFERENCE_URL:-http://localhost:9292}"
REPO_URL=""

usage() {
    sed -n '2,9p' "$0" | sed 's/^# \{0,1\}//'
    exit "${1:-0}"
}

# --- arg parsing ---
CMD=""
while [ $# -gt 0 ]; do
    case "$1" in
        -repo|--repo) REPO_URL="$2"; shift 2 ;;
        run|status|help) CMD="$1"; shift ;;
        -h|--help) usage ;;
        *) echo "Unknown argument: $1" >&2; usage 1 ;;
    esac
done
[ -n "$CMD" ] || usage 1

# --- helpers ---
repo_slug() {  # https://github.com/owner/name(.git) -> owner/name
    echo "$1" | sed -E 's#^https?://github.com/##; s#\.git$##; s#/$##'
}

cmd_status() {
    echo "=== Software Factory Status ==="
    echo ""
    echo "--- Serving plane (llama-swap) ---"
    if curl -sf "$SWAP_URL/v1/models" >/dev/null 2>&1; then
        curl -s "$SWAP_URL/v1/models" \
            | python3 -c 'import json,sys; [print("  ", m["id"]) for m in json.load(sys.stdin)["data"]]'
    else
        echo "  DOWN — start with ./scripts/serve.sh"
    fi
    echo ""
    echo "--- Kata board ---"
    (cd "$FACTORY_DIR" && kata list 2>/dev/null | tail -8) || echo "  no board — run: kata init"
    echo ""
    echo "--- Sandbox (NemoClaw) ---"
    if command -v nemoclaw >/dev/null 2>&1; then
        nemoclaw local-pm-os-agent status 2>/dev/null | grep -E "Model:|Agent:|Connected:" || echo "  sandbox not reachable"
    else
        echo "  nemoclaw CLI not found"
    fi
}

cmd_run() {
    [ -n "$REPO_URL" ] || { echo "ERROR: run requires -repo <github-url>" >&2; exit 1; }
    local slug; slug="$(repo_slug "$REPO_URL")"

    echo "=== sfai run — $slug ==="

    # 1. Clone/refresh corpus
    if [ ! -d "$FACTORY_DIR/corpus/.git" ]; then
        echo "--- Cloning corpus ---"
        git clone "$REPO_URL" "$FACTORY_DIR/corpus"
    else
        echo "--- Refreshing corpus ---"
        git -C "$FACTORY_DIR/corpus" pull --ff-only || echo "WARNING: corpus pull failed; using existing checkout"
    fi

    # 2. Fetch open issues from GitHub
    echo "--- Fetching open issues from github.com/$slug ---"
    local issues_json
    issues_json="$(curl -sf "https://api.github.com/repos/$slug/issues?state=open&per_page=100")" \
        || { echo "ERROR: GitHub API fetch failed" >&2; exit 1; }

    # 3. Create katas with full issue bodies (idempotent via gh-<n> key)
    echo "--- Creating katas ---"
    echo "$issues_json" | FACTORY_DIR="$FACTORY_DIR" python3 -c '
import json, os, subprocess, sys
factory = os.environ["FACTORY_DIR"]
def kata(*a, **kw):
    return subprocess.run(["kata", *a], cwd=factory, capture_output=True, text=True, **kw)
existing = kata("list", "--json").stdout
created = skipped = 0
for i in json.load(sys.stdin):
    if "pull_request" in i:
        continue
    n = i["number"]
    key = f"gh-{n}:"
    if key in existing:
        skipped += 1
        continue
    labels = ", ".join(l["name"] for l in i.get("labels", [])) or "none"
    body = (i.get("body") or "(no description on GitHub)") + (
        "\n\n---\nSource: " + i["html_url"]
        + "\nGitHub labels: " + labels
        + "\nOpened by: " + i["user"]["login"])
    title = "[bug] " + key + " " + i["title"]
    r = kata("create", title, "--body", body, "--idempotency-key", f"gh-{n}")
    if r.returncode == 0:
        created += 1
        print("  +", title)
    else:
        print("  FAILED", title, r.stderr.strip()[:80])
print(f"Created {created} katas ({skipped} already on board)")'

    # 4. Orchestration (P2 — not yet implemented)
    echo ""
    echo "--- Orchestration ---"
    if [ -x "$FACTORY_DIR/scripts/orchestrate.sh" ]; then
        exec "$FACTORY_DIR/scripts/orchestrate.sh"
    else
        echo "orchestrate.sh not implemented yet (P2). Board is loaded; agents can poll with:"
        echo "  kata list --agent"
    fi
}

case "$CMD" in
    run) cmd_run ;;
    status) cmd_status ;;
    help) usage ;;
esac
