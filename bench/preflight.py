"""V6 preflight: verify every precondition BEFORE measuring, and FAIL LOUDLY if any is off.
The V2-V5 benchmarks were silently invalidated by unmet preconditions (a stale gateway served old
tools; a contaminated session). This module turns each of those into a hard, checked gate.

Applying an arm = write the arm's config into bench-home, swap in its skill, clear the MCP/gateway
state, then PROVE the agent actually receives the arm's tools.
"""
import json, os, re, shutil, subprocess, sys, time
import bench_lib as B

HOME = os.path.join(B.LAB, "bench-home")

CONFIG_TMPL = """# V6 benchmark arm: {label} (generated; do not edit by hand)
model:
  provider: "lmstudio"
  base_url: "http://127.0.0.1:1235/v1"
  default: "{model}"
agent:
  max_turns: 45
  reasoning_effort: "low"
  disabled_toolsets: [web, browser, terminal, file, code_execution, vision, image_gen, tts, stt,
    video, video_gen, x_search, computer_use, kanban, connections, delegation, session_search,
    context_engine, cronjob]
auxiliary:
  compression: {{provider: "main", model: "", timeout: 600, max_concurrency: 1}}
  title_generation: {{enabled: false}}
  background_review: {{enabled: false}}
fallback_providers: []
tools: {{tool_search: {{enabled: "off"}}}}
memory: {{memory_enabled: false, user_profile_enabled: false}}
skills: {{creation_nudge_interval: 0}}
compression:
  enabled: true
  threshold: 0.5
  target_ratio: 0.3
  protect_last_n: 12
  proactive_prune_tokens: 1500
  proactive_prune_min_result_chars: 2000
approvals: {{mode: deny, cron_mode: deny, single_query_mode: deny, unattended_mode: deny}}
mcp_servers:
  lab:
    command: "uv"
    args: ["run", "--no-project", "--python", "3.13", "--with", "mcp==1.26.0", "python", "-I",
      "{lab_path}"]
    connect_timeout: 120
  seckb:
    command: "uv"
    args: ["run", "--no-project", "--python", "3.13", "--with", "mcp==1.26.0", "python", "-I",
      "{seckb_path}"]
    connect_timeout: 120
telemetry: {{shared_metrics: {{enabled: false, send: false}}}}
_config_version: 53
"""


def kill_gateways_and_cache():
    """Stop any pooled gateway / lab server and clear the schema cache so the next session re-discovers
    the arm's tools fresh (the fix for the stale-tools bug)."""
    subprocess.run(["powershell", "-NoProfile", "-Command",
        "Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -match 'lab[0-9]?_mcp.py|gateway run --quiet' } "
        "| ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }"],
        capture_output=True, timeout=30)
    for f in ("cache/mcp_schema_cache.json", "cache/tool_discovery_cache.json", ".mcp-discovery.lock"):
        try:
            os.remove(os.path.join(HOME, f))
        except OSError:
            pass
    time.sleep(2)


def apply_arm(arm):
    """Write config + skill for the arm into bench-home and reset gateway/cache. Returns the arm dict
    enriched with resolved paths (for the manifest)."""
    lab_path = os.path.join(B.LAB, arm["lab_server"]).replace("\\", "/")
    seckb_path = os.path.expanduser(r"~\tools\seckb\seckb_mcp.py").replace("\\", "/")
    open(os.path.join(HOME, "config.yaml"), "w", encoding="utf-8").write(
        CONFIG_TMPL.format(label=arm["label"], model=B.MODEL, lab_path=lab_path, seckb_path=seckb_path))
    skill_dst = os.path.join(HOME, "skills", "local", "web-pentest")
    os.makedirs(skill_dst, exist_ok=True)
    shutil.copyfile(os.path.join(B.LAB, arm["skill"]), os.path.join(skill_dst, "SKILL.md"))
    kill_gateways_and_cache()
    arm = dict(arm, home=HOME, lab_server=arm["lab_server"])
    return arm


def check(arm, verbose=True):
    """Run all preconditions. Returns (ok, report-dict). FAILS LOUD: prints and returns ok=False."""
    r = {}
    r["docker_up"] = B.sh(["docker", "info", "--format", "{{.ServerVersion}}"], timeout=20).returncode == 0
    r["model_loaded"] = B.MODEL in B.sh([B.LMS, "ps"], timeout=20).stdout
    r["juice_healthy"] = B.juice_healthy()
    r["sandbox_up"] = B.sh(["docker", "exec", "ctf-attacker", "true"], timeout=20).returncode == 0
    r["sandbox_no_internet"] = "000" in B.sh(["docker", "exec", "ctf-attacker", "sh", "-c",
        "timeout 6 curl -s -o /dev/null -w '%{http_code}' https://example.com || echo 000"], timeout=20).stdout
    # deterministic tool verification: (1) the arm's server DEFINES the tools, (2) a live -z can CALL one
    static_ok, missing = B.static_tools_defined(arm["lab_server"], arm["expected_tools"])
    r["tools_defined_in_server"] = static_ok
    r["_tools_missing_in_server"] = missing
    discovered = B.mcp_discovered_tools(HOME)
    need = set(arm["expected_tools"])
    r["gateway_serves_arm_tools"] = need.issubset(discovered)
    r["_tools_discovered"] = sorted(discovered)
    r["_tools_missing"] = sorted(need - discovered)
    ok = all(v for k, v in r.items() if not k.startswith("_"))
    if verbose:
        print(f"[preflight: arm={arm['label']}]")
        for k, v in r.items():
            if not k.startswith("_"):
                print(f"  {'OK ' if v else 'FAIL'}  {k}")
        if missing:
            print(f"  tools NOT defined in {arm['lab_server']}: {missing}")
        if r["_tools_missing"]:
            print(f"  tools not discovered by gateway: {r['_tools_missing']} (saw: {r['_tools_discovered']})")
    return ok, r


if __name__ == "__main__":
    arms = {a["label"]: a for a in json.load(open(os.path.join(B.LAB, "bench", "arms.json")))}
    arm = apply_arm(arms[sys.argv[1] if len(sys.argv) > 1 else "full"])
    ok, _ = check(arm)
    print("PREFLIGHT", "PASS" if ok else "FAIL")
    sys.exit(0 if ok else 1)
