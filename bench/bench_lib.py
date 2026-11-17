"""V6 honest-benchmark shared library.
Design goals: reproducible (pinned + manifested), honest (independent verification, correct attribution,
N repeats for variance), fail-loud (preconditions checked before any measurement).
"""
import json, os, re, subprocess, sqlite3, time, urllib.request, hashlib

LAB = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))   # ~/tools/ctf-lab
HERMES = os.path.expanduser(r"~\tools\hermes-agent\.venv\Scripts\hermes.exe")
LMS = os.path.expanduser(r"~\.lmstudio\bin\lms.exe")
SCORE = "http://127.0.0.1:3001/api/Challenges/"
APPVER = "http://127.0.0.1:3001/rest/admin/application-version"
MODEL = "gemma-4-26b-a4b-it-qat-heretic"


def sh(cmd, timeout=60, env=None):
    return subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace",
                          timeout=timeout, env=env)


def scoreboard():
    """Set of challenge keys Juice Shop reports solved, read from the HOST (the agent can't see or fake it)."""
    with urllib.request.urlopen(SCORE, timeout=20) as r:
        return {c["key"] for c in json.load(r)["data"] if c["solved"]}


def juice_healthy():
    try:
        return urllib.request.urlopen(APPVER, timeout=5).status == 200
    except Exception:
        return False


def reset_juice(wait=90):
    """Fresh target: restart Juice Shop so ALL challenge state is cleared -> before-snapshot is empty,
    which makes solve attribution unambiguous."""
    sh(["docker", "restart", "ctf-juice"], timeout=60)
    t = time.time()
    while time.time() - t < wait:
        if juice_healthy():
            time.sleep(2)
            return True
        time.sleep(3)
    return False


def reset_sandbox():
    """Clear the agent's per-assessment sandbox state (auth session, request loop-log, notes)."""
    sh(["docker", "exec", "ctf-attacker", "rm", "-f",
        "/work/session.json", "/work/reqlog.json", "/work/notes.txt"], timeout=30)


def last_session_metrics(home):
    """Per-attempt metrics from the most recent Hermes session DB: tool calls, distinct tools, turns, tokens."""
    db = sqlite3.connect(f"file:{os.path.join(home, 'state.db')}?mode=ro", uri=True)
    db.row_factory = sqlite3.Row
    s = db.execute("select id, input_tokens, output_tokens from sessions order by started_at desc limit 1").fetchone()
    if not s:
        return {"tool_calls": 0, "tools": {}, "turns": 0, "input_tokens": 0, "output_tokens": 0}
    calls, tools, turns = 0, {}, 0
    for m in db.execute("select role, tool_calls from messages where session_id=?", (s["id"],)):
        if m["role"] == "assistant":
            turns += 1
        for c in json.loads(m["tool_calls"] or "[]"):
            calls += 1
            n = (c.get("function") or c).get("name", "?").split("__")[-1]
            tools[n] = tools.get(n, 0) + 1
    return {"tool_calls": calls, "tools": tools, "turns": turns,
            "input_tokens": s["input_tokens"] or 0, "output_tokens": s["output_tokens"] or 0}


def static_tools_defined(lab_server, expected):
    """Deterministic: confirm the arm's MCP server source actually DEFINES each expected tool
    (grep for `def <tool>`). Catches a wrong lab_server path / config mistake with no model involved."""
    src = ""
    try:
        src = open(os.path.join(LAB, lab_server), encoding="utf-8").read()
    except OSError:
        return False, list(expected)
    missing = [t for t in expected if f"def {t}(" not in src]
    return (not missing), missing


def mcp_discovered_tools(home, server="lab", timeout=120):
    """Deterministic tool discovery against THIS home's config (`hermes mcp test <server>`). Since the
    harness kills any pooled gateway per arm, the real -z gateway re-discovers from the same config, so
    this reflects what a run will actually get. Returns the set of lab tool names exposed."""
    env = dict(os.environ, HERMES_HOME=home)
    p = sh([HERMES, "mcp", "test", server], timeout=timeout, env=env)
    return set(re.findall(r"\b(lab_target|lab_shell|http_[a-z_]+|sqli_[a-z_]+|note)\b", p.stdout or ""))


def git_commit(path):
    try:
        return sh(["git", "-C", path, "rev-parse", "--short", "HEAD"], timeout=10).stdout.strip() or "none"
    except Exception:
        return "none"


def gpu_state():
    try:
        o = sh(["nvidia-smi", "--query-gpu=pstate,power.draw,power.limit", "--format=csv,noheader"], timeout=10).stdout.strip()
        return o.splitlines()[0] if o else "n/a"
    except Exception:
        return "n/a"


def file_hash(path):
    try:
        return hashlib.sha256(open(path, "rb").read()).hexdigest()[:12]
    except Exception:
        return "missing"


def environment_manifest(arm):
    """Everything needed to reproduce / audit a run. Written once per benchmark run."""
    juice_ver = ""
    try:
        juice_ver = json.load(urllib.request.urlopen(APPVER, timeout=5)).get("version", "")
    except Exception:
        pass
    skill = os.path.join(arm["home"], "skills", "local", "web-pentest", "SKILL.md")
    return {
        "timestamp_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "arm": arm["label"],
        "model": MODEL,
        "sampling": arm.get("sampling", {"temperature": 0.6, "top_p": 0.95, "note": "LM Studio per-model defaults"}),
        "home": os.path.basename(arm["home"]),
        "lab_server": arm.get("lab_server", "?"),
        "lab_server_sha256_12": file_hash(os.path.join(LAB, arm.get("lab_server", ""))),
        "skill_sha256_12": file_hash(skill),
        "expected_tools": sorted(arm.get("expected_tools", [])),
        "juice_version": juice_ver,
        "juice_image": sh(["docker", "inspect", "ctf-juice", "--format", "{{.Config.Image}}"], timeout=15).stdout.strip(),
        "attacker_image_digest": sh(["docker", "inspect", "ctf-attacker", "--format", "{{.Image}}"], timeout=15).stdout.strip()[:19],
        "hermes_version": (sh([HERMES, "--version"], timeout=30).stdout.splitlines() or ["?"])[0].strip(),
        "repo_commit": git_commit(LAB),
        "gpu_state_at_start": gpu_state(),
    }
