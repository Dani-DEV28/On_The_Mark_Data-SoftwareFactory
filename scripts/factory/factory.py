#!/usr/bin/env python3
"""Software Factory engine — TPM-driven pull model over the kata board.

Agents are the 7 SOUL.md personas, executed as chat completions against the
local llama-swap endpoint (one model loaded at a time). Agents exchange
structured YAML task artifacts stored under evidence/artifacts/<kata>/ and
mirrored as kata comments for the human audit trail.

Gates (kata labels):
  gate:intaken      -> Tech Lead analyzes, produces task artifact
  gate:scoped       -> PM writes acceptance criteria / edge cases / subtasks
  gate:designed     -> Architect (only if needs-architect label) or skip
  gate:implementing -> Implementer writes files+tests; applied on a git branch
  gate:qa           -> DevOps/QA runs tests (never fixes code)
  gate:tl-review    -> Tech Lead reviews QA failure, produces revised task
  gate:documenting  -> Docs Engineer updates docs
  gate:review       -> PR-ready; human reviews and closes
  gate:halted       -> stopped by TPM (see Factory Incident Report)

Subcommands:
  gate --gate <name> [--limit N] [--katas a,b]   process one gate
  intake --katas a,b | --limit N                 pull unlabeled katas into gate:intaken
  stop-check [--kata <id>]                       TPM stop conditions -> PASS|FAIL|HALT
  heartbeat                                      TPM no-progress tracking
  status                                         board summary by gate
  evidence                                       write evidence/evidence-table.md
  baseline --kata <id>                           single-agent baseline run
"""

import argparse
import datetime as dt
import hashlib
import json
import os
import re
import subprocess
import sys
import threading
import time
import urllib.request

import yaml

FACTORY_DIR = os.environ.get("FACTORY_DIR") or os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
KATA_BIN = os.environ.get("KATA_BIN", os.path.expanduser("~/.local/bin/kata"))
UV_BIN = os.environ.get("UV_BIN", os.path.expanduser("~/.local/bin/uv"))
LLM_URL = os.environ.get("SFAI_INFERENCE_URL", "http://localhost:9292") + "/v1/chat/completions"
MODEL = os.environ.get("SFAI_MODEL", "qwen3.6-35b-a3b-fp8")
CTX_LIMIT = int(os.environ.get("SFAI_CTX_TOKENS", "32768"))  # served max-model-len
CORPUS = os.path.join(FACTORY_DIR, "corpus")
EVIDENCE = os.path.join(FACTORY_DIR, "evidence")
ARTIFACTS = os.path.join(EVIDENCE, "artifacts")
INCIDENTS = os.path.join(EVIDENCE, "incidents")
USAGE_LOG = os.path.join(EVIDENCE, "usage.jsonl")
HEARTBEAT_STATE = os.path.join(EVIDENCE, "heartbeat-state.json")
SOULS_DIR = os.path.join(FACTORY_DIR, "config", "openclaw", "agents")
STOP_CFG = os.path.join(FACTORY_DIR, "config", "stop-gap.yaml")

GATE_ROLE = {
    "intake": ("gate:intaken", "tech-lead"),
    "scoped": ("gate:scoped", "product-manager"),
    "designed": ("gate:designed", "architect"),
    "implement": ("gate:implementing", "implementer"),
    "qa": ("gate:qa", "devops-qa"),
    "tl-review": ("gate:tl-review", "tech-lead"),
    "docs": ("gate:documenting", "docs-engineer"),
    "ci": ("gate:ci", "devops-qa"),
}
ALL_GATE_LABELS = [
    "gate:intaken", "gate:scoped", "gate:designed", "gate:implementing",
    "gate:qa", "gate:tl-review", "gate:documenting", "gate:ci",
    "gate:review", "gate:halted",
]


def now():
    return dt.datetime.now(dt.timezone.utc)


LOG_FILE = os.environ.get("SFAI_LOG_FILE") or os.path.join(EVIDENCE, "factory.log")


def file_log(line):
    try:
        os.makedirs(EVIDENCE, exist_ok=True)
        with open(LOG_FILE, "a") as f:
            f.write(line + "\n")
    except OSError:
        pass


def log(msg):
    line = f"[{now().strftime('%H:%M:%S')}] {msg}"
    _panel_interrupt(line)
    file_log(line)


IS_TTY = sys.stdout.isatty()

ROLE_ICON = {
    "tech-lead": "🧭", "product-manager": "📋", "architect": "📐",
    "implementer": "🔧", "devops-qa": "🧪", "docs-engineer": "📚",
    "tpm": "🕰️", "baseline": "👤",
}


TEAM = ["tech-lead", "product-manager", "architect", "implementer",
        "devops-qa", "docs-engineer", "tpm"]
TEAM_STATE = os.path.join(EVIDENCE, "team-state.json")


def _team_state():
    try:
        with open(TEAM_STATE) as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return {}


def _save_team_state(state):
    try:
        os.makedirs(EVIDENCE, exist_ok=True)
        with open(TEAM_STATE, "w") as f:
            json.dump(state, f)
    except OSError:
        pass


# ---- shared panel state: several agents can be active concurrently ----
_PANEL = threading.RLock()
_ACTIVE = {}        # role -> AgentView
_DRAWN = [0]        # lines currently drawn on screen
_FRAME_I = [0]


def _panel_lines():
    _FRAME_I[0] += 1
    frame = AgentView.FRAMES[_FRAME_I[0] % len(AgentView.FRAMES)]
    lanes = f"{len(_ACTIVE)} agent(s) active — heavy + light lanes, batched on one local model"
    hdr = f"\x1b[1m── factory team ──\x1b[0m {now().strftime('%H:%M:%S')} ({lanes})"
    any_view = next(iter(_ACTIVE.values()), None)
    lines = [hdr]
    for role in TEAM:
        v = _ACTIVE.get(role)
        if v is not None:
            lines.append(v.active_row(frame))
        elif any_view is not None:
            lines.append(any_view.idle_row(role))
    return lines


def _panel_draw():
    with _PANEL:
        if not IS_TTY:
            return
        lines = _panel_lines()
        out = (f"\x1b[{_DRAWN[0]}F" if _DRAWN[0] else "")
        out += "".join("\x1b[K" + l[:180] + "\n" for l in lines)
        sys.stdout.write(out)
        sys.stdout.flush()
        _DRAWN[0] = len(lines)


def _panel_interrupt(line):
    """Print a plain line without corrupting the panel region."""
    with _PANEL:
        if IS_TTY and _DRAWN[0]:
            sys.stdout.write(f"\x1b[{_DRAWN[0]}F\x1b[0J")
            _DRAWN[0] = 0
        print(line, flush=True)


def _panel_loop():
    while True:
        with _PANEL:
            if not _ACTIVE:
                break
        _panel_draw()
        time.sleep(0.15)


class AgentView:
    """Full-team terminal panel: all 7 roles are always visible; active ones
    (possibly several — heavy + light lanes) animate with live token streams,
    the rest show queue depth and last completed work (persisted via
    evidence/team-state.json). Plain log lines when stdout is not a TTY."""

    FRAMES = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"

    def __init__(self, role, kata_id, verb="working"):
        self.role, self.kata, self.verb = role, kata_id, verb
        self.tok = 0
        self.tail = ""
        self.t0 = time.time()
        self._stop = threading.Event()
        self._i = 0
        self._thread = None
        self._lock = threading.Lock()
        self._drawn = False
        self.last = _team_state()
        # Snapshot each role's queue once per agent turn (cheap; not per-frame).
        role_gate = {"tech-lead": "gate:intaken", "product-manager": "gate:scoped",
                     "architect": "gate:designed", "implementer": "gate:implementing",
                     "devops-qa": "gate:qa", "docs-engineer": "gate:documenting"}
        self.queue = {}
        if IS_TTY:
            for r, lbl in role_gate.items():
                try:
                    self.queue[r] = len(kata_list(label=lbl))
                except Exception:  # noqa: BLE001
                    self.queue[r] = None
            try:
                self.queue["tech-lead"] = (self.queue.get("tech-lead") or 0) + \
                    len(kata_list(label="gate:tl-review"))
            except Exception:  # noqa: BLE001
                pass

    def start(self):
        with _PANEL:
            _ACTIVE[self.role] = self
            need_loop = IS_TTY and len(_ACTIVE) == 1
        if need_loop:
            threading.Thread(target=_panel_loop, daemon=True).start()
        if not IS_TTY:
            log(f"{ROLE_ICON.get(self.role, '•')} {self.role} {self.verb} on {self.kata}...")
        return self

    def feed(self, delta):
        with self._lock:
            self.tok += 1
            self.tail = (self.tail + delta).replace("\n", "⏎ ")[-46:]

    def active_row(self, frame):
        icon = ROLE_ICON.get(self.role, "•")
        el = time.time() - self.t0
        rate = self.tok / el if el > 0.5 else 0
        with self._lock:
            tail = self.tail
        return (f"{frame} {icon} \x1b[1m{self.role:<16}\x1b[0m {self.verb} on "
                f"\x1b[1m{self.kata}\x1b[0m  {self.tok:>5} tok {rate:5.1f} tok/s "
                f"{el:4.0f}s \x1b[2m{tail}\x1b[0m")

    def idle_row(self, role):
        icon = ROLE_ICON.get(role, "•")
        q = self.queue.get(role)
        if role == "tpm":
            queue_s = "watching (stop-check every cycle)"
        elif q is None:
            queue_s = ""
        elif q == 0:
            queue_s = "queue empty"
        else:
            queue_s = f"\x1b[0m\x1b[33m{q} queued\x1b[0m\x1b[2m"
        info = self.last.get(role)
        if info:
            age = int(time.time() - info.get("ts", 0))
            age_s = f"{age // 60}m ago" if age >= 60 else f"{age}s ago"
            return (f"  {icon} \x1b[2m{role:<16} {queue_s} · "
                    f"last ✓ {info.get('msg', '')[:44]} ({age_s})\x1b[0m")
        return f"  {icon} \x1b[2m{role:<16} idle · {queue_s}\x1b[0m"

    def note(self, text):
        with self._lock:
            self.tail = text[-46:]

    def done(self, msg=""):
        el = time.time() - self.t0
        summary = f"{self.kata}: {msg}  {self.tok} tok {el:.0f}s"
        with _PANEL:
            self.last[self.role] = {"msg": summary, "ts": time.time()}
            _save_team_state(self.last)
            _ACTIVE.pop(self.role, None)
        icon = ROLE_ICON.get(self.role, "•")
        line = f"✓ {icon} {self.role:<16} {self.kata}  {self.tok} tok  {el:.0f}s  {msg}"
        if IS_TTY:
            _panel_interrupt(line)
        else:
            print(line, flush=True)
        file_log(f"[{now().strftime('%H:%M:%S')}] {line}")


# ---------- kata CLI ----------

def kata(*args, actor=None, check=True):
    cmd = [KATA_BIN]
    if actor:
        cmd += ["--as", actor]
    cmd += list(args)
    r = subprocess.run(cmd, cwd=FACTORY_DIR, capture_output=True, text=True)
    if check and r.returncode != 0:
        raise RuntimeError(f"kata {' '.join(args[:3])}... failed: {r.stderr.strip()[:300]}")
    return r


def kata_list(label=None, status="open", limit=200):
    args = ["list", "--json", "--status", status, "--limit", str(limit)]
    if label:
        args += ["--label", label]
    out = kata(*args).stdout
    data = json.loads(out) if out.strip() else {}
    return data.get("issues", []) if isinstance(data, dict) else data


def find_kata(short_id):
    for status in ("open", "all"):
        for it in kata_list(status=status, limit=500):
            if it.get("short_id") == short_id:
                return it
    return None


def set_gate(short_id, new_label, actor="tpm"):
    # Add-first so the kata can never reach a zero-label dead end; a crash
    # mid-transition leaves old+new labels, swept by the next transition.
    if new_label:
        r = kata("label", "add", short_id, new_label, actor=actor, check=False)
        if r.returncode != 0 and "already" not in (r.stderr or "").lower():
            r = kata("label", "add", short_id, new_label, actor=actor, check=False)
            if r.returncode != 0 and "already" not in (r.stderr or "").lower():
                raise RuntimeError(
                    f"set_gate({short_id} -> {new_label}) add failed: {(r.stderr or '').strip()[:200]}")
    for lbl in ALL_GATE_LABELS:
        if lbl != new_label:
            r = kata("label", "rm", short_id, lbl, actor=actor, check=False)
            if r.returncode != 0:
                kata("label", "rm", short_id, lbl, actor=actor, check=False)


def comment(short_id, body, actor):
    kata("comment", short_id, "--body", body, actor=actor, check=False)


# ---------- artifacts ----------

def art_dir(short_id):
    d = os.path.join(ARTIFACTS, short_id)
    os.makedirs(d, exist_ok=True)
    return d


def save_artifact(short_id, name, data, actor):
    path = os.path.join(art_dir(short_id), f"{name}.yaml")
    text = yaml.safe_dump(data, sort_keys=False, allow_unicode=True, width=100)
    with open(path, "w") as f:
        f.write(text)
    comment(short_id, f"[{actor}] {name} artifact:\n```yaml\n{text[:3500]}\n```", actor)
    log(f"   {short_id}: {name} artifact saved ({len(text)} bytes) → {os.path.relpath(path, FACTORY_DIR)}")
    return path


def load_artifact(short_id, name):
    path = os.path.join(art_dir(short_id), f"{name}.yaml")
    if os.path.exists(path):
        with open(path) as f:
            return yaml.safe_load(f)
    return None


def record_event(short_id, event, detail=""):
    path = os.path.join(art_dir(short_id), "timeline.jsonl")
    with open(path, "a") as f:
        f.write(json.dumps({"ts": now().isoformat(), "event": event, "detail": detail[:400]}) + "\n")


def read_timeline(short_id):
    path = os.path.join(art_dir(short_id), "timeline.jsonl")
    if not os.path.exists(path):
        return []
    with open(path) as f:
        return [json.loads(l) for l in f if l.strip()]


# ---------- LLM ----------

def llm_chat(system, user, kata_id, role, max_tokens=8192, temperature=0.2, view=None):
    payload = json.dumps({
        "model": MODEL,
        "messages": [{"role": "system", "content": system},
                     {"role": "user", "content": user}],
        "max_tokens": max_tokens,
        "temperature": temperature,
        "stream": True,
        "stream_options": {"include_usage": True},
    }).encode()
    req = urllib.request.Request(LLM_URL, data=payload,
                                 headers={"Content-Type": "application/json"})
    t0 = time.time()
    parts, usage = [], {}
    with urllib.request.urlopen(req, timeout=1200) as r:
        for raw in r:
            line = raw.decode("utf-8", "replace").strip()
            if not line.startswith("data:"):
                continue
            data = line[5:].strip()
            if data == "[DONE]":
                break
            try:
                chunk = json.loads(data)
            except json.JSONDecodeError:
                continue
            if chunk.get("usage"):
                usage = chunk["usage"]
            for ch in chunk.get("choices", []):
                delta = (ch.get("delta") or {}).get("content")
                if delta:
                    parts.append(delta)
                    if view:
                        view.feed(delta)
    os.makedirs(EVIDENCE, exist_ok=True)
    with open(USAGE_LOG, "a") as f:
        f.write(json.dumps({
            "ts": now().isoformat(), "kata": kata_id, "role": role,
            "prompt_tokens": usage.get("prompt_tokens"),
            "completion_tokens": usage.get("completion_tokens"),
            "seconds": round(time.time() - t0, 1),
        }) + "\n")
    return "".join(parts)


def extract_yaml(text):
    # Fences anchored at column 0: embedded ``` inside YAML block scalars are
    # indented, so they can't terminate the capture early.
    m = re.findall(r"^```ya?ml[ \t]*\n(.*?)\n```[ \t]*$", text, re.DOTALL | re.MULTILINE)
    blob = m[-1] if m else text
    return yaml.safe_load(blob)


def agent_yaml(role, system, user, kata_id, schema_keys, max_tokens=8192):
    """Call an agent, demanding a fenced YAML artifact; one retry with feedback."""
    last_err = None
    for attempt in range(2):
        prompt = user if attempt == 0 else (
            user + f"\n\nYOUR PREVIOUS REPLY WAS INVALID ({last_err}). "
                   "Reply again with ONLY one fenced ```yaml block containing the artifact.")
        view = AgentView(role, kata_id,
                         "retrying" if attempt else "working").start()
        try:
            # Fit completion into the served context (conservative ~3 chars/token).
            est = (len(system) + len(prompt)) // 3 + 512
            text = llm_chat(system, prompt, kata_id, role,
                            max_tokens=max(2048, min(max_tokens, CTX_LIMIT - est)),
                            view=view)
            data = extract_yaml(text)
            if not isinstance(data, dict):
                raise ValueError("artifact is not a YAML mapping")
            missing = [k for k in schema_keys if k not in data]
            if missing:
                raise ValueError(f"missing keys: {missing}")
            view.done("artifact ✓")
            return data
        except Exception as e:  # noqa: BLE001
            last_err = str(e)[:200]
            view.done(f"✗ {last_err[:60]}")
    raise RuntimeError(f"{role} produced invalid artifact: {last_err}")


def soul(role):
    path = os.path.join(SOULS_DIR, role, "SOUL.md")
    with open(path) as f:
        text = f.read()
    # Append any SKILL_*.md playbooks the role ships with (capped per skill).
    d = os.path.join(SOULS_DIR, role)
    for fn in sorted(os.listdir(d)):
        if fn.startswith("SKILL_") and fn.endswith(".md"):
            with open(os.path.join(d, fn)) as f:
                text += f"\n\n--- {fn} ---\n" + f.read()[:3000]
    return text


# ---------- corpus git ----------

# One shared working tree: any checkout/read/write sequence must hold this.
CORPUS_LOCK = threading.RLock()


def corpus_git(*args, check=True):
    r = subprocess.run(
        ["git", "-c", "user.name=Software Factory", "-c", "user.email=factory@onthemark.local",
         *args], cwd=CORPUS, capture_output=True, text=True)
    if check and r.returncode != 0:
        raise RuntimeError(f"git {' '.join(args[:3])} failed: {r.stderr.strip()[:300]}")
    return r


def corpus_branch(short_id, prefix="factory"):
    name = f"{prefix}/{short_id}"
    # Legit work is always committed by apply_files before switching branches,
    # so discarding stray tracked edits and untracked leftovers is safe.
    corpus_git("reset", "--hard", check=False)
    corpus_git("clean", "-fd", check=False)  # no -x: keeps .venv/__pycache__
    corpus_git("checkout", "main")           # strict: never branch from the wrong base
    if corpus_git("rev-parse", "--verify", name, check=False).returncode != 0:
        corpus_git("branch", name)
    corpus_git("checkout", name)
    return name


def safe_rel(path):
    p = os.path.normpath(path)
    if p.startswith("/") or p.startswith(".."):
        raise ValueError(f"unsafe path in artifact: {path}")
    return p


def apply_files(short_id, files, msg):
    """files: [{path, content}] — validate fully, then write and commit."""
    if not isinstance(files, list) or not files:
        raise ValueError("artifact 'files' must be a non-empty list of {path, content}")
    entries = []
    for f in files:
        if not isinstance(f, dict) or not isinstance(f.get("path"), str) \
                or not isinstance(f.get("content"), str):
            raise ValueError(f"malformed files entry: {str(f)[:120]}")
        entries.append((safe_rel(f["path"]), f["content"]))
    written = []
    for rel, content in entries:
        dst = os.path.join(CORPUS, rel)
        os.makedirs(os.path.dirname(dst) or CORPUS, exist_ok=True)
        with open(dst, "w") as fh:
            fh.write(content)
        written.append(rel)
    corpus_git("add", *written)
    before = corpus_git("rev-parse", "HEAD").stdout.strip()
    corpus_git("commit", "-m", msg, check=False)
    after = corpus_git("rev-parse", "HEAD").stdout.strip()
    if after == before:
        raise RuntimeError(f"no new commit ({short_id}): artifact was a no-op, files={written}")
    sha = corpus_git("rev-parse", "--short", "HEAD").stdout.strip()
    return written, sha


def file_snippet(rel, limit=6000):
    try:
        rel = safe_rel(rel)
    except (ValueError, TypeError):
        return f"(path {rel!r} rejected: not a repo-relative path)"
    path = os.path.join(CORPUS, rel)
    if os.path.isdir(path):
        r = subprocess.run(["git", "ls-files", rel], cwd=CORPUS, capture_output=True, text=True)
        return f"(directory {rel}):\n" + "\n".join(r.stdout.splitlines()[:40])
    if not os.path.exists(path):
        return f"(file {rel} does not exist yet)"
    with open(path, errors="replace") as f:
        text = f.read(limit + 1)
    return text[:limit] + ("\n...[truncated]" if len(text) > limit else "")


def repo_tree(limit=150):
    r = subprocess.run(["git", "ls-files"], cwd=CORPUS, capture_output=True, text=True)
    lines = r.stdout.splitlines()
    return "\n".join(lines[:limit]) + (f"\n...({len(lines)} files total)" if len(lines) > limit else "")


def _locked_repo_tree(limit=150):
    with CORPUS_LOCK:
        return repo_tree(limit)


# ---------- context assembly ----------

def kata_context(item, include_artifacts=("tech-lead", "product-manager", "architect", "tl-review")):
    sid = item["short_id"]
    parts = [f"KATA {sid}: {item['title']}", "", "ISSUE BODY:", str(item.get("body") or "")[:6000]]
    for name in include_artifacts:
        art = load_artifact(sid, name)
        if art:
            parts += ["", f"--- {name.upper()} ARTIFACT ---",
                      yaml.safe_dump(art, sort_keys=False)[:4000]]
    return "\n".join(parts)


PROTOCOL = (
    "You are one specialized agent in a software factory. You communicate ONLY via "
    "structured YAML task artifacts. Reply with exactly one fenced ```yaml block. "
    "No prose outside the fence. Be concrete and minimal — this is a hackathon MVP. "
    "Inside any file content, never place ``` at the start of a line (indent embedded "
    "markdown fences); use YAML block scalars (path: ... content: |) for file contents.")


# ---------- gate handlers ----------

def gate_intake(item):
    sid = item["short_id"]
    art = agent_yaml(
        "tech-lead",
        soul("tech-lead") + "\n\n" + PROTOCOL +
        "\nProduce a task artifact with keys: analysis (str), type (bug|feature|spike|docs), "
        "needs_architect (bool — true ONLY for API changes, DB migrations, or cross-module refactors), "
        "affected_files (list of repo-relative paths or dirs), "
        "task (mapping: title, objective, constraints (list)).",
        kata_context(item, include_artifacts=()) +
        "\n\nREPO FILE TREE (corpus):\n" + _locked_repo_tree(),
        sid, ["analysis", "type", "needs_architect", "affected_files", "task"])
    save_artifact(sid, "tech-lead", art, "tech-lead")
    record_event(sid, "Analysis Complete")
    if art.get("needs_architect"):
        kata("label", "add", sid, "needs-architect", actor="tech-lead", check=False)
    set_gate(sid, "gate:scoped")
    log(f"  {sid}: Tech Lead analyzed -> scoped (architect={art.get('needs_architect')})")


def gate_scoped(item):
    sid = item["short_id"]
    art = agent_yaml(
        "product-manager",
        soul("product-manager") + "\n\n" + PROTOCOL +
        "\nProduce an artifact with keys: acceptance_criteria (list), edge_cases (list), "
        "subtasks (list), definition_of_done (str).",
        kata_context(item), sid,
        ["acceptance_criteria", "edge_cases", "subtasks", "definition_of_done"])
    save_artifact(sid, "product-manager", art, "product-manager")
    record_event(sid, "Planning Complete")
    set_gate(sid, "gate:designed")
    log(f"  {sid}: PM scoped -> designed")


def gate_designed(item):
    sid = item["short_id"]
    labels_probe = kata_list(label="needs-architect")
    needs = any(i["short_id"] == sid for i in labels_probe)
    if not needs:
        record_event(sid, "Architecture Skipped")
        set_gate(sid, "gate:implementing")
        log(f"  {sid}: Architect skipped -> implementing")
        return
    art = agent_yaml(
        "architect",
        soul("architect") + "\n\n" + PROTOCOL +
        "\nProduce an artifact with keys: design_notes (str), risks (list), approved (bool).",
        kata_context(item), sid, ["design_notes", "risks", "approved"])
    save_artifact(sid, "architect", art, "architect")
    record_event(sid, "Architecture Complete")
    set_gate(sid, "gate:implementing")
    log(f"  {sid}: Architect reviewed -> implementing")


def gate_implement(item):
    sid = item["short_id"]
    kata("claim", sid, "--force", actor="implementer", check=False)
    attempts = len([e for e in read_timeline(sid) if e["event"].startswith("Implementation Attempt")])
    tl = load_artifact(sid, "tech-lead") or {}
    review = load_artifact(sid, "tl-review")
    system = (soul("implementer") + "\n\n" + PROTOCOL +
              "\nProduce an artifact with keys: files (list of {path, content} — COMPLETE file "
              "contents, repo-relative paths, include unit tests), notes (str), "
              "test_command (str — must start with 'uv run pytest').")
    base = kata_context(item)
    # Show whole files within a char budget; never pair full-file OUTPUT with
    # truncated INPUT — a truncated file is forbidden to rewrite.
    affected = [p for p in tl.get("affected_files", []) if isinstance(p, str)][:4]
    avail = max(8000, (30000 - 16384) * 3 - len(system) - len(base))
    per_file = max(2000, min(12000, avail // max(1, len(affected))))
    parts, truncated = [], set()
    with CORPUS_LOCK:
        corpus_branch(sid)  # read context from THIS kata's branch (matters on retries)
        for p in affected:
            snip = file_snippet(p, per_file)
            if snip.endswith("[truncated]"):
                truncated.add(os.path.normpath(p))
            parts.append(f"=== {p} ===\n{snip}")
    snippets = "\n\n".join(parts)
    if truncated:
        snippets += ("\n\nWARNING: files marked ...[truncated] are INCOMPLETE. You MUST NOT "
                     "include them in your files output — rewriting them would delete the unseen "
                     "remainder. Put changes in other or new files, or explain in notes.")
    extra = ""
    if review:
        extra = "\nA PREVIOUS ATTEMPT FAILED QA. Follow the Tech Lead's revised guidance artifact above exactly."
    art = agent_yaml(
        "implementer", system,
        base + "\n\nRELEVANT FILES:\n" + snippets + extra,
        sid, ["files", "notes", "test_command"], max_tokens=16384)
    if truncated and isinstance(art.get("files"), list):
        bad = [f.get("path") for f in art["files"] if isinstance(f, dict)
               and os.path.normpath(str(f.get("path", ""))) in truncated]
        if bad:
            raise RuntimeError(f"implementer tried to overwrite truncated files {bad}")
    with CORPUS_LOCK:
        branch = corpus_branch(sid)
        written, sha = apply_files(sid, art["files"],
                                   f"factory({sid}) attempt {attempts + 1}: {item['title'][:60]}")
    art["_commit"] = sha
    art["_branch"] = branch
    save_artifact(sid, "implementer", art, "implementer")
    record_event(sid, f"Implementation Attempt {attempts + 1}", f"{sha} files={written}")
    set_gate(sid, "gate:qa")
    log(f"  {sid}: Implementer attempt {attempts + 1} ({sha}) -> qa")


def gate_qa(item):
    sid = item["short_id"]
    impl = load_artifact(sid, "implementer") or {}
    cmd = impl.get("test_command", "")
    if not isinstance(cmd, str) or not cmd.startswith("uv run pytest"):
        cmd = "uv run pytest tests/ -x -q"
    # Targeted tests, the full suite, AND the same static checks CI runs —
    # otherwise lint/type failures are only discovered after the push.
    # pytest lives in the "test" extra; mypy in "dev"; ruff via uvx.
    uvx = os.path.join(os.path.dirname(UV_BIN), "uvx")
    runs = [(cmd, [UV_BIN, "run", "--extra", "test"] + cmd.split()[2:])]
    if "tests/ " not in cmd + " " and not cmd.rstrip().endswith("tests/"):
        runs.append(("uv run pytest tests/ -q",
                     [UV_BIN, "run", "--extra", "test", "pytest", "tests/", "-q"]))
    runs.append(("ruff check .", [uvx, "ruff@0.15.21", "check", "."]))
    runs.append(("mypy petri", [UV_BIN, "run", "--extra", "dev", "mypy", "petri"]))
    t0 = time.time()
    out, passed = "", True
    qa_view = AgentView("devops-qa", sid, "testing").start()
    with CORPUS_LOCK:
        corpus_branch(sid)
        for label, cmd_args in runs:
            qa_view.note(f"$ {label}")
            try:
                r = subprocess.run(cmd_args, cwd=CORPUS, capture_output=True, text=True, timeout=900)
                out += f"\n$ {label}\n" + (r.stdout + "\n" + r.stderr)[-5000:]
                if r.returncode != 0:
                    passed = False
                    break
            except subprocess.TimeoutExpired:
                out, passed = out + f"\n$ {label}\nTIMEOUT after 900s", False
                break
            except FileNotFoundError as e:
                out += f"\n$ {label}\nSKIPPED (tool missing: {e})"
    out = out[-7000:]
    qa_view.done("tests+lint green ✓" if passed else "checks FAILED ✗")
    cmd = " && ".join(l for l, _ in runs)
    cmd = " && ".join(runs)
    failures = re.findall(r"^(FAILED|ERROR) (\S+)", out, re.MULTILINE)
    failures += [("LINT", m) for m in re.findall(r"^(\S+\.py:\d+:\d+: \S+ .{0,80})", out, re.MULTILINE)][:10]
    failures += [("TYPE", m) for m in re.findall(r"^(\S+\.py:\d+: error: .{0,80})", out, re.MULTILINE)][:10]
    sig = hashlib.sha256("|".join(sorted(f"{a} {b}" for a, b in failures)).encode()).hexdigest()[:12]
    art = {"commands": [cmd], "passed": passed, "seconds": round(time.time() - t0, 1),
           "failures": [f"{a} {b}" for a, b in failures][:25], "signature": sig,
           "output_tail": out[-2500:]}
    save_artifact(sid, f"qa-{int(time.time())}", art, "devops-qa")
    if passed:
        record_event(sid, "QA Passed")
        set_gate(sid, "gate:documenting")
        log(f"  {sid}: QA PASSED -> documenting")
    else:
        record_event(sid, "QA Failed", sig)
        set_gate(sid, "gate:tl-review")
        log(f"  {sid}: QA FAILED ({len(failures)} failures) -> tl-review")


def gate_tl_review(item):
    sid = item["short_id"]
    qa_arts = sorted(f for f in os.listdir(art_dir(sid)) if f.startswith("qa-"))
    last_qa = load_artifact(sid, qa_arts[-1][:-5]) if qa_arts else {}
    ci_arts = sorted(f for f in os.listdir(art_dir(sid)) if f.startswith("ci-"))
    last_ci = load_artifact(sid, ci_arts[-1][:-5]) if ci_arts else {}
    failure_ctx = ""
    if last_qa:
        failure_ctx += "\n\nQA FAILURE ARTIFACT:\n" + yaml.safe_dump(last_qa, sort_keys=False)[:3000]
    if last_ci:
        failure_ctx += "\n\nCI FAILURE ARTIFACT (from the GitHub PR checks):\n" + \
            yaml.safe_dump(last_ci, sort_keys=False)[:3000]
    art = agent_yaml(
        "tech-lead",
        soul("tech-lead") + "\n\n" + PROTOCOL +
        "\nQA or CI failed. Diagnose and produce a REVISED task artifact with keys: "
        "diagnosis (str), revised_task (mapping: objective, constraints), guidance (str — "
        "specific instructions for the implementer to fix the failure).",
        kata_context(item) + failure_ctx,
        sid, ["diagnosis", "revised_task", "guidance"])
    save_artifact(sid, "tl-review", art, "tech-lead")
    record_event(sid, "Retry")
    set_gate(sid, "gate:implementing")
    log(f"  {sid}: Tech Lead reviewed failure -> implementing (retry)")


def gate_docs(item):
    sid = item["short_id"]
    impl = load_artifact(sid, "implementer") or {}
    with CORPUS_LOCK:
        corpus_branch(sid)
        changelog = file_snippet("CHANGELOG.md", 2000)
    changelog_truncated = changelog.endswith("[truncated]")
    art = agent_yaml(
        "docs-engineer",
        soul("docs-engineer") + "\n\n" + PROTOCOL +
        "\nProduce an artifact with keys: files (list of {path, content} — ONLY documentation "
        "files like CHANGELOG.md or docs/*.md; COMPLETE contents), summary (str). "
        "Keep it to at most 2 small files.",
        kata_context(item) + "\n\nIMPLEMENTER NOTES:\n" + str(impl.get("notes", ""))[:2000] +
        "\n\nEXISTING CHANGELOG (if any):\n" + changelog +
        ("\n\nNOTE: CHANGELOG.md is truncated above — do NOT rewrite it; create a new docs file instead."
         if changelog_truncated else ""),
        sid, ["files", "summary"], max_tokens=8192)
    if changelog_truncated and isinstance(art.get("files"), list):
        art["files"] = [f for f in art["files"] if isinstance(f, dict)
                        and os.path.normpath(str(f.get("path", ""))) != "CHANGELOG.md"]
    with CORPUS_LOCK:
        corpus_branch(sid)
        try:
            written, sha = apply_files(sid, art.get("files", []), f"factory({sid}) docs")
        except Exception as e:  # noqa: BLE001
            written, sha = [], "none"
            art["_error"] = str(e)[:200]
    art["_commit"] = sha
    save_artifact(sid, "docs-engineer", art, "docs-engineer")
    record_event(sid, "Documentation Complete", sha)
    set_gate(sid, "gate:ci")
    log(f"  {sid}: Docs done -> ci (push PR + watch checks)")


def _gh_api(path):
    """Unauthenticated GitHub API GET (public repos); uses GITHUB_TOKEN if set."""
    req = urllib.request.Request(
        f"https://api.github.com{path}",
        headers={"User-Agent": "software-factory", "Accept": "application/vnd.github+json",
                 **({"Authorization": f"Bearer {os.environ['GITHUB_TOKEN']}"}
                    if os.environ.get("GITHUB_TOKEN") else {})})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def corpus_slug():
    url = corpus_git("remote", "get-url", "origin").stdout.strip()
    m = re.search(r"github\.com[:/]([^/]+/[^/.]+)", url)
    return m.group(1) if m else None


def gate_ci(item):
    """Push the branch, ensure a PR exists, watch CI checks.
    Green -> gate:review. Failures -> ci artifact + gate:tl-review (self-heal)."""
    sid = item["short_id"]
    branch = f"factory/{sid}"
    slug = corpus_slug()
    if not slug:
        raise RuntimeError("corpus origin is not a GitHub remote")
    owner = slug.split("/")[0]
    with CORPUS_LOCK:
        head_sha = corpus_git("rev-parse", branch).stdout.strip()
        # 1. Push (works when the GB10 has credentials; otherwise needs a relay).
        push = corpus_git("push", "origin", f"{branch}:{branch}", check=False)
    pushed = push.returncode == 0

    # 2. Find the PR for this branch.
    prs = _gh_api(f"/repos/{slug}/pulls?head={owner}:{branch}&state=open")
    if not prs:
        msg = (f"branch {branch} @ {head_sha[:7]} is ready but no PR exists"
               + ("" if pushed else " and push failed (no GitHub credentials on this host)")
               + f". Relay: git push origin {branch} && gh pr create --head {branch}")
        comment(sid, f"[devops-qa] CI gate waiting: {msg}", "devops-qa")
        log(f"  {sid}: CI waiting — {msg[:120]}")
        return  # stay at gate:ci; retried next cycle
    pr = prs[0]
    pr_sha = pr["head"]["sha"]
    if pr_sha != head_sha and not pushed:
        log(f"  {sid}: CI waiting — PR #{pr['number']} is at {pr_sha[:7]} but local is "
            f"{head_sha[:7]}; push needed (relay: git push origin {branch})")
        return

    # 3. Aggregate check runs for the PR head.
    runs = _gh_api(f"/repos/{slug}/commits/{pr_sha}/check-runs").get("check_runs", [])
    pending = [r for r in runs if r.get("status") != "completed"]
    if not runs or pending:
        log(f"  {sid}: CI pending on PR #{pr['number']} "
            f"({len(pending)}/{len(runs)} checks still running)")
        return  # stay at gate:ci
    failed = [r for r in runs if r.get("conclusion") not in ("success", "neutral", "skipped")]
    if not failed:
        record_event(sid, "CI Passed", pr_sha[:7])
        set_gate(sid, "gate:review")
        comment(sid, f"[devops-qa] CI GREEN on PR #{pr['number']} ({len(runs)} checks). "
                     f"PR READY for human review: {pr['html_url']}", "devops-qa")
        log(f"  {sid}: CI GREEN ({len(runs)} checks) -> review  {pr['html_url']}")
        return
    def _annotations(run):
        try:
            ann = _gh_api(f"/repos/{slug}/check-runs/{run['id']}/annotations")
            return [f"{a.get('path')}:{a.get('start_line')} {a.get('annotation_level')}: "
                    f"{(a.get('message') or '')[:200]}" for a in ann[:10]]
        except Exception:  # noqa: BLE001
            return []
    art = {"pr": pr["number"], "pr_url": pr["html_url"], "sha": pr_sha,
           "failed_checks": [{"name": r["name"],
                              "summary": ((r.get("output") or {}).get("summary") or
                                          (r.get("output") or {}).get("title") or "")[:500],
                              "annotations": _annotations(r),
                              "url": r.get("html_url")} for r in failed]}
    save_artifact(sid, f"ci-{int(time.time())}", art, "devops-qa")
    record_event(sid, "CI Failed", ",".join(r["name"] for r in failed)[:100])
    set_gate(sid, "gate:tl-review")
    log(f"  {sid}: CI FAILED ({', '.join(r['name'] for r in failed)}) -> tl-review")


HANDLERS = {
    "intake": gate_intake, "scoped": gate_scoped, "designed": gate_designed,
    "implement": gate_implement, "qa": gate_qa, "tl-review": gate_tl_review,
    "docs": gate_docs, "ci": gate_ci,
}


# ---------- stop conditions (TPM) ----------

def load_stop_cfg():
    with open(STOP_CFG) as f:
        cfg = yaml.safe_load(f)["stop_conditions"]
    m = re.match(r"(\d+)m", str(cfg.get("max_runtime", "45m")))
    cfg["max_runtime_min"] = int(m.group(1)) if m else 45
    return cfg


def check_kata_stop(item, cfg):
    """Returns (verdict, reason). verdict in PASS|HALT."""
    sid = item["short_id"]
    timeline = read_timeline(sid)
    # Count evaluated failures (QA and CI), not attempts started — otherwise
    # the Nth attempt would be committed and halted before ever being tested.
    failed = [e for e in timeline if e["event"] in ("QA Failed", "CI Failed")]
    if len(failed) >= cfg["max_attempts"]:
        return "HALT", f"Retry budget exceeded ({len(failed)}/{cfg['max_attempts']} failed attempts)"
    if timeline:
        # Runtime = the CURRENT work stream, not kata lifetime: the clock
        # restarts at each revival (intake, QA/CI failure feedback, retry) so
        # time parked at gate:review / waiting on CI doesn't count.
        restarts = [e for e in timeline
                    if e["event"] in ("Intaken", "Retry", "QA Failed", "CI Failed")]
        t0 = dt.datetime.fromisoformat((restarts[-1] if restarts else timeline[0])["ts"])
        mins = (now() - t0).total_seconds() / 60
        if mins > cfg["max_runtime_min"]:
            return "HALT", f"Runtime limit exceeded ({mins:.0f}m > {cfg['max_runtime_min']}m in current attempt)"
    fails = [e for e in timeline if e["event"] == "QA Failed"]
    sigs = [e.get("detail", "") for e in fails]
    if sigs and len(sigs) >= cfg["identical_failures"]:
        tail = sigs[-cfg["identical_failures"]:]
        if len(set(tail)) == 1 and tail[0]:
            return "HALT", f"Identical QA failure repeated {cfg['identical_failures']}x"
    state = json.load(open(HEARTBEAT_STATE)) if os.path.exists(HEARTBEAT_STATE) else {}
    if state.get("counters", {}).get(sid, 0) >= cfg["no_progress_cycles"]:
        return "HALT", f"No progress for {cfg['no_progress_cycles']} heartbeat cycles"
    # Role-error events only ("<role> Failed" from cmd_gate); routine QA test
    # failures are governed by max_attempts / identical_failures instead.
    agent_fails = {e["event"] for e in timeline
                   if e["event"].endswith(" Failed") and e["event"] != "QA Failed"}
    if len(agent_fails) > cfg["max_failed_agents"]:
        return "HALT", f"More than {cfg['max_failed_agents']} distinct agents failed"
    return "PASS", ""


def incident_report(item, reason):
    sid = item["short_id"]
    timeline = read_timeline(sid)
    attempts = len([e for e in timeline if e["event"].startswith("Implementation Attempt")])
    elapsed = "unknown"
    if timeline:
        t0 = dt.datetime.fromisoformat(timeline[0]["ts"])
        elapsed = f"{(now() - t0).total_seconds() / 60:.0f} minutes"
    qa_arts = sorted(f for f in os.listdir(art_dir(sid)) if f.startswith("qa-"))
    last_qa = load_artifact(sid, qa_arts[-1][:-5]) if qa_arts else {}
    event_role = [
        ("Analysis Complete", "Tech Lead"), ("Retry", "Tech Lead"), ("tech-lead Failed", "Tech Lead"),
        ("Planning Complete", "Product Manager"), ("product-manager Failed", "Product Manager"),
        ("Architecture Complete", "Architect"), ("architect Failed", "Architect"),
        ("Implementation Attempt", "Implementer"), ("implementer Failed", "Implementer"),
        ("QA Passed", "QA"), ("QA Failed", "QA"), ("devops-qa Failed", "QA"),
        ("Documentation Complete", "Docs"), ("docs-engineer Failed", "Docs"),
    ]
    seen = {role for e in timeline for prefix, role in event_role if e["event"].startswith(prefix)}
    report = {
        "Factory Incident Report": None,
        "Issue": f"#{sid} {item['title']}",
        "Status": "Stopped",
        "Reason": reason,
        "Attempts": attempts,
        "Elapsed": elapsed,
        "Agents": [r for r in ["Tech Lead", "Product Manager", "Architect",
                               "Implementer", "QA", "Docs"] if r in seen],
        "Timeline": [e["event"] for e in timeline],
        "Observed Errors": (last_qa or {}).get("failures", [])[:10],
        "Repeated Failure": (last_qa or {}).get("failures", ["none"])[0] if last_qa.get("failures") else "none",
        "Artifacts": sorted(os.listdir(art_dir(sid))),
        "Recommendation": "Human intervention required.",
    }
    os.makedirs(INCIDENTS, exist_ok=True)
    path = os.path.join(INCIDENTS, f"{sid}.yaml")
    text = yaml.safe_dump(report, sort_keys=False, allow_unicode=True)
    with open(path, "w") as f:
        f.write(text)
    comment(sid, f"[tpm] FACTORY INCIDENT REPORT\n```yaml\n{text[:3500]}\n```", "tpm")
    return path


def cmd_stop_check(args):
    cfg = load_stop_cfg()
    stops = [i for i in kata_list() if i["title"].startswith("[stop]")]
    if stops:
        print(f"HALT: manual [stop] kata on board: "
              f"{', '.join(i['short_id'] for i in stops)}")
        return 3  # factory-wide stop; per-kata halts return 2
    items = []
    if args.kata:
        it = find_kata(args.kata)
        if not it:
            print(f"FAIL: kata {args.kata} not found")
            return 1
        items = [it]
    else:
        for lbl in ("gate:intaken", "gate:scoped", "gate:designed", "gate:implementing",
                    "gate:qa", "gate:tl-review", "gate:documenting", "gate:ci"):
            items += kata_list(label=lbl)
    halted = False
    for it in items:
        verdict, reason = check_kata_stop(it, cfg)
        if verdict == "HALT":
            halted = True
            path = incident_report(it, reason)
            set_gate(it["short_id"], "gate:halted")
            print(f"HALT {it['short_id']}: {reason} -> {path}")
    if halted:
        return 2
    print(f"PASS ({len(items)} active katas within limits)")
    return 0


def cmd_heartbeat(_args):
    """TPM heartbeat: track no-progress cycles + deadlock detection."""
    os.makedirs(EVIDENCE, exist_ok=True)
    state = json.load(open(HEARTBEAT_STATE)) if os.path.exists(HEARTBEAT_STATE) else {}
    prev = state.get("snapshot", {})
    counters = state.get("counters", {})
    snapshot = {}
    for lbl in ALL_GATE_LABELS[:-2]:
        if lbl == "gate:ci":
            continue  # waiting on external CI / push relay is not a stall
        for it in kata_list(label=lbl):
            snapshot[it["short_id"]] = f"{lbl}@{it.get('updated_at', '')}"
    for sid, sig in snapshot.items():
        counters[sid] = counters.get(sid, 0) + 1 if prev.get(sid) == sig else 0
    counters = {sid: c for sid, c in counters.items() if sid in snapshot}
    with open(HEARTBEAT_STATE, "w") as f:
        json.dump({"ts": now().isoformat(), "snapshot": snapshot, "counters": counters}, f, indent=1)
    stalled = [f"{s}({c})" for s, c in counters.items() if c >= 2]
    log(f"heartbeat: {len(snapshot)} active, stalled: {', '.join(stalled) or 'none'}")
    return 0


# ---------- intake selection ----------

def cmd_intake(args):
    labeled = set()
    for lbl in ALL_GATE_LABELS:
        labeled |= {i["short_id"] for i in kata_list(label=lbl)}
    cands = []
    for it in kata_list(limit=500):
        sid = it["short_id"]
        t = it["title"]
        if (sid in labeled or t.startswith("[stop]") or t.startswith("[artifact]")
                or "[EPIC]" in t or "smoke test" in t):
            continue
        cands.append(it)
    if args.katas:
        want = set(args.katas.split(","))
        chosen = [i for i in cands if i["short_id"] in want]
        for sid in want - {i["short_id"] for i in chosen}:
            if sid in labeled:
                log(f"  {sid}: already at a gate — skipping re-intake (remove its gate label to force)")
                continue
            it = find_kata(sid)
            if not it:
                log(f"  {sid}: not found — skipping")
                continue
            t = it["title"]
            if it.get("status") != "open" or t.startswith("[stop]") or "[EPIC]" in t or "smoke test" in t:
                log(f"  {sid}: excluded from intake (status={it.get('status')}) — skipping")
                continue
            chosen.append(it)
    else:
        chosen = cands[:args.limit]
    for it in chosen:
        set_gate(it["short_id"], "gate:intaken")
        record_event(it["short_id"], "Intaken")
        log(f"  {it['short_id']} -> gate:intaken ({it['title'][:60]})")
    print(f"intaken: {len(chosen)}")
    return 0


# ---------- gate runner ----------

def cmd_gate(args):
    label, role = GATE_ROLE[args.gate]
    items = kata_list(label=label)
    if args.katas:
        want = set(args.katas.split(","))
        items = [i for i in items if i["short_id"] in want]
    items = items[:args.limit]
    if not items:
        return 0
    log(f"┌─ gate {args.gate} ({ROLE_ICON.get(role, '')} {role}): {len(items)} kata(s): "
        + ", ".join(f"{i['short_id']} «{i['title'][:45]}»" for i in items))
    for it in items:
        t0 = time.time()
        try:
            HANDLERS[args.gate](it)
            log(f"└─ {it['short_id']}: gate {args.gate} finished in {time.time() - t0:.0f}s")
        except Exception as e:  # noqa: BLE001
            record_event(it["short_id"], f"{role} Failed", str(e)[:300])
            comment(it["short_id"], f"[{role}] gate {args.gate} ERROR: {str(e)[:400]}", role)
            log(f"└─ {it['short_id']}: ERROR in {args.gate} after {time.time() - t0:.0f}s: {str(e)[:200]}")
    return 0


# ---------- two-lane cycle: heavy work + light planning in parallel ----------

HEAVY_GATES = ["implement", "qa", "docs", "ci"]     # corpus-locked, big generations
LIGHT_GATES = ["intake", "scoped", "designed", "tl-review"]  # planning artifacts


def cmd_cycle(args):
    """One orchestration cycle with two concurrent lanes. vLLM batches the
    concurrent requests; the corpus working tree is serialized by CORPUS_LOCK."""
    errors = []

    def run_lane(gates):
        for g in gates:
            try:
                ns = argparse.Namespace(gate=g, limit=args.limit, katas=args.katas)
                cmd_gate(ns)
            except Exception as e:  # noqa: BLE001
                errors.append(f"{g}: {str(e)[:200]}")
    lanes = [threading.Thread(target=run_lane, args=(HEAVY_GATES,), name="heavy"),
             threading.Thread(target=run_lane, args=(LIGHT_GATES,), name="light")]
    for t in lanes:
        t.start()
    for t in lanes:
        t.join()
    for e in errors:
        log(f"lane error: {e}")
    return 1 if errors else 0


# ---------- status / evidence ----------

def cmd_status(_args):
    print("=== Factory board by gate ===")
    total = 0
    for lbl in ALL_GATE_LABELS:
        items = kata_list(label=lbl)
        total += len(items)
        if items:
            print(f"{lbl:20s} {len(items):3d}  " +
                  ", ".join(i["short_id"] for i in items[:12]))
    print(f"{'(gated total)':20s} {total:3d}")
    return 0


def cmd_evidence(_args):
    usage = {}
    if os.path.exists(USAGE_LOG):
        with open(USAGE_LOG) as f:
            for line in f:
                row = json.loads(line)
                u = usage.setdefault(row.get("kata") or "?", {"pt": 0, "ct": 0, "calls": 0, "sec": 0})
                u["pt"] += row.get("prompt_tokens") or 0
                u["ct"] += row.get("completion_tokens") or 0
                u["calls"] += 1
                u["sec"] += row.get("seconds") or 0
    rows = []
    if os.path.isdir(ARTIFACTS):
        for sid in sorted(os.listdir(ARTIFACTS)):
            if not os.path.isdir(os.path.join(ARTIFACTS, sid)):
                continue  # generated .html artifacts live alongside kata dirs
            timeline = read_timeline(sid)
            if not timeline:
                continue
            it = find_kata(sid) or {"title": "?", "status": "?"}
            gate = "?"
            for lbl in ALL_GATE_LABELS:
                if any(i["short_id"] == sid for i in kata_list(label=lbl, status="all")):
                    gate = lbl
                    break
            t0 = dt.datetime.fromisoformat(timeline[0]["ts"])
            t1 = dt.datetime.fromisoformat(timeline[-1]["ts"])
            attempts = len([e for e in timeline if e["event"].startswith("Implementation Attempt")])
            u = usage.get(sid, {"pt": 0, "ct": 0, "calls": 0, "sec": 0})
            rows.append((sid, it["title"][:48], gate, attempts,
                         f"{(t1 - t0).total_seconds() / 60:.1f}m",
                         u["calls"], u["pt"], u["ct"], f"{u['sec']:.0f}s"))
    os.makedirs(EVIDENCE, exist_ok=True)
    path = os.path.join(EVIDENCE, "evidence-table.md")
    with open(path, "w") as f:
        f.write("# Factory Evidence — real data from the kata board\n\n")
        f.write(f"Generated: {now().isoformat()}\n\n")
        f.write("| kata | title | gate | attempts | cycle time | LLM calls | prompt tok | completion tok | LLM time |\n")
        f.write("|------|-------|------|----------|-----------|-----------|------------|----------------|----------|\n")
        for r in rows:
            f.write("| " + " | ".join(str(x) for x in r) + " |\n")
        if not rows:
            f.write("| (no factory activity yet) |\n")
    print(f"wrote {path} ({len(rows)} katas)")
    return 0


# ---------- Tech Lead artifact creation (plan #20) ----------

def cmd_artifact(args):
    """Tech Lead builds a self-contained HTML visualization from factory state."""
    tag = re.sub(r"[^a-zA-Z0-9_-]", "-", args.tag or "artifact")
    gates = []
    for lbl in ALL_GATE_LABELS:
        items = kata_list(label=lbl)
        if items:
            gates.append(f"{lbl}: " + ", ".join(
                f"{i['short_id']} ({i['title'][:60]})" for i in items[:10]))
    board = kata("list").stdout[-3000:]
    gitlog = corpus_git("log", "--oneline", "--all", "-15", check=False).stdout
    diffstat = corpus_git("diff", "--stat", "main...HEAD", check=False).stdout[-1500:]
    context = ("KATA BOARD SUMMARY:\n" + board +
               "\n\nGATE STATE:\n" + ("\n".join(gates) or "(no katas at gates)") +
               "\n\nCORPUS GIT LOG (all branches):\n" + gitlog +
               "\n\nCURRENT BRANCH DIFF STAT:\n" + diffstat)
    system = (soul("tech-lead") +
              "\n\nYou are producing an HTML artifact. Reply with ONLY a complete HTML "
              "document starting with <!doctype html>. Requirements: fully self-contained "
              "(embedded CSS/JS, no external CDNs or network requests), dark theme, "
              "renders correctly when opened directly in a browser. No markdown fences.")
    user = f"REQUEST: {args.prompt}\n\nFACTORY STATE:\n{context[:20000]}"
    est = (len(system) + len(user)) // 3 + 512
    view = AgentView("tech-lead", tag, "building artifact").start()
    text = llm_chat(system, user, f"artifact-{tag}", "tech-lead",
                    max_tokens=max(4096, min(16384, CTX_LIMIT - est)), view=view)
    view.done("html ✓")
    # Strip a fence if the model added one anyway, then isolate the document.
    m = re.search(r"```(?:html)?\s*\n(.*?)\n```", text, re.DOTALL)
    if m and "<html" in m.group(1).lower():
        text = m.group(1)
    idx = text.lower().find("<!doctype")
    if idx < 0:
        idx = text.lower().find("<html")
    if idx > 0:
        text = text[idx:]
    os.makedirs(ARTIFACTS, exist_ok=True)
    ts = now().strftime("%Y%m%d-%H%M%S")
    path = os.path.join(ARTIFACTS, f"{tag}-{ts}.html")
    with open(path, "w") as f:
        f.write(text)
    print(f"artifact written: {path}")
    return 0


# ---------- baseline ----------

def cmd_baseline(args):
    it = find_kata(args.kata)
    if not it:
        print(f"kata {args.kata} not found")
        return 1
    sid = it["short_id"]
    t0 = time.time()
    art = agent_yaml(
        "baseline",
        "You are a single generalist software engineer with no team. Solve the GitHub issue "
        "end-to-end yourself. " + PROTOCOL +
        "\nProduce an artifact with keys: files (list of {path, content} — COMPLETE contents "
        "including tests), notes (str), test_command (str starting with 'uv run pytest').",
        f"ISSUE: {it['title']}\n\n{it.get('body', '')[:6000]}\n\nREPO FILE TREE:\n" + repo_tree(),
        sid, ["files", "notes", "test_command"], max_tokens=16384)
    with CORPUS_LOCK:
        corpus_branch(sid, prefix="baseline")
        written, sha = apply_files(sid, art["files"], f"baseline({sid}): {it['title'][:60]}")
        cmd = art.get("test_command", "uv run pytest tests/ -x -q")
        if not isinstance(cmd, str) or not cmd.startswith("uv run pytest"):
            cmd = "uv run pytest tests/ -x -q"
        try:
            r = subprocess.run([UV_BIN, "run", "--extra", "test"] + cmd.split()[2:], cwd=CORPUS,
                               capture_output=True, text=True, timeout=900)
            passed = r.returncode == 0
            tail = (r.stdout + r.stderr)[-2000:]
        except subprocess.TimeoutExpired:
            passed, tail = False, "TIMEOUT"
    result = {"kata": sid, "branch": f"baseline/{sid}", "commit": sha,
              "passed": passed, "wall_seconds": round(time.time() - t0, 1),
              "files": written, "output_tail": tail}
    os.makedirs(os.path.join(EVIDENCE, "baseline"), exist_ok=True)
    path = os.path.join(EVIDENCE, "baseline", f"{sid}.yaml")
    with open(path, "w") as f:
        yaml.safe_dump(result, f, sort_keys=False)
    print(f"baseline {sid}: passed={passed} in {result['wall_seconds']}s -> {path}")
    return 0 if passed else 1


# ---------- main ----------

def main():
    ap = argparse.ArgumentParser(prog="factory")
    sub = ap.add_subparsers(dest="cmd", required=True)
    g = sub.add_parser("gate")
    g.add_argument("--gate", required=True, choices=list(GATE_ROLE))
    g.add_argument("--limit", type=int, default=3)
    g.add_argument("--katas")
    c = sub.add_parser("cycle")
    c.add_argument("--limit", type=int, default=3)
    c.add_argument("--katas")
    i = sub.add_parser("intake")
    i.add_argument("--katas")
    i.add_argument("--limit", type=int, default=2)
    s = sub.add_parser("stop-check")
    s.add_argument("--kata")
    sub.add_parser("heartbeat")
    sub.add_parser("status")
    sub.add_parser("evidence")
    b = sub.add_parser("baseline")
    b.add_argument("--kata", required=True)
    a = sub.add_parser("artifact")
    a.add_argument("--prompt", required=True)
    a.add_argument("--tag", default="artifact")
    args = ap.parse_args()
    fns = {"gate": cmd_gate, "cycle": cmd_cycle, "intake": cmd_intake,
           "stop-check": cmd_stop_check, "heartbeat": cmd_heartbeat, "status": cmd_status,
           "evidence": cmd_evidence, "baseline": cmd_baseline, "artifact": cmd_artifact}
    sys.exit(fns[args.cmd](args))


if __name__ == "__main__":
    main()
