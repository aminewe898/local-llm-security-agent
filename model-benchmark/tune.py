"""Apply an LM Studio per-model load config, reload the model, and measure speed + memory.

Usage: python tune.py <trial-name> [--ctx 16384] [key=value ...]
Keys are LM Studio load-config keys without the "llm.load." prefix, e.g.
  llama.flashAttention=true numCpuExpertLayersRatio=1 llama.acceleration.offloadRatio=1
Values are JSON. A value prefixed with "c:" is wrapped as {"checked": true, "value": ...}.
Appends one row to tune_results.jsonl.
"""
import json, os, subprocess, sys, time
import requests

MODEL = "gemma-4-26b-a4b-it-qat-heretic"
BASE = "http://localhost:1235"
CFG = os.path.expanduser(r"~\.lmstudio\apps\bionic\.internal\user-concrete-model-default-config"
                         r"\SC117\gemma-4-26B-A4B-it-qat-heretic-GGUF\gemma-4-26B-A4B-it-qat-heretic-UD-Q4_K_XL.gguf.json")
HERE = os.path.dirname(os.path.abspath(__file__))

name = sys.argv[1]
ctx = 16384
fields = []
args = sys.argv[2:]
i = 0
while i < len(args):
    a = args[i]
    if a == "--ctx":
        ctx = int(args[i + 1]); i += 2; continue
    k, v = a.split("=", 1)
    wrap = v.startswith("c:")
    raw = v[2:] if wrap else v
    try:
        val = json.loads(raw)
    except json.JSONDecodeError:
        val = raw.strip('"')  # bare string, e.g. q8_0 after shell quote stripping
    fields.append({"key": "llm.load." + k, "value": {"checked": True, "value": val} if wrap else val})
    i += 1


def sh(cmd):
    return subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")


def vram():
    return int(sh(["nvidia-smi", "--query-gpu=memory.used", "--format=csv,noheader,nounits"]).stdout.strip())


def free_ram_gb():
    out = sh(["powershell", "-NoProfile", "-Command", "(Get-CimInstance Win32_OperatingSystem).FreePhysicalMemory"]).stdout.strip()
    return round(int(out) / 1048576, 1)


def chat(prompt, max_tokens):
    t = time.time()
    r = requests.post(BASE + "/api/v0/chat/completions", json={"model": MODEL, "messages": [{"role": "user", "content": prompt}],
                      "max_tokens": max_tokens, "temperature": 0.6, "top_p": 0.95, "seed": 42}, timeout=900)
    r.raise_for_status()
    j = r.json()
    j["_wall"] = time.time() - t
    return j


sh(["lms", "unload", "--all"])
time.sleep(2)
os.makedirs(os.path.dirname(CFG), exist_ok=True)
json.dump({"preset": "", "operation": {"fields": []}, "load": {"fields": fields}}, open(CFG, "w"), indent=2)
vram0, ram0 = vram(), free_ram_gb()
t = time.time()
ld = sh(["lms", "load", MODEL, "-c", str(ctx), "-y"])
load_s = round(time.time() - t, 1)
row = {"trial": name, "ctx": ctx, "fields": {f["key"][9:]: f["value"] for f in fields}, "load_s": load_s}
if "loaded successfully" not in (ld.stdout + ld.stderr):
    row["error"] = (ld.stdout + ld.stderr)[-300:]
    print("LOAD FAILED", row["error"])
else:
    row["vram_model_mib"] = vram() - vram0
    row["vram_total_mib"] = vram()
    try:
        gen = [chat("Explain how TCP congestion control works, in about 300 words.", 400) for _ in range(2)][1]
        row["gen_tps"] = round(gen["stats"]["tokens_per_second"], 1)
        filler = "\n".join(f"2026-11-{1 + n % 28:02d} 10:{n % 60:02d}:07 INFO worker-{n % 7} processed batch {n} in {40 + (n * 37) % 300} ms, queue depth {(n * 13) % 90}"
                           + ("  NOTE: the backup key code is 7341." if n == 211 else "") for n in range(330))
        lp = chat(f"[run {name}]\n" + filler + "\n\nIn the log above, what is the backup key code? Reply with just the number.", 1500)
        row["prompt_tokens"] = lp["usage"]["prompt_tokens"]
        row["long_ttft_s"] = round(lp["stats"]["time_to_first_token"], 1)
        row["prompt_tps"] = round(lp["usage"]["prompt_tokens"] / lp["stats"]["time_to_first_token"])
        row["long_gen_tps"] = round(lp["stats"]["tokens_per_second"], 1)
        row["long_ok"] = "7341" in (lp["choices"][0]["message"].get("content") or "")
    except Exception as e:
        row["error"] = f"{type(e).__name__}: {e}"[:300]
    row["ram_used_by_load_gb"] = round(ram0 - free_ram_gb(), 1)
    row["free_ram_gb"] = free_ram_gb()
    row["vram_after_mib"] = vram()
open(os.path.join(HERE, "tune_results.jsonl"), "a", encoding="utf-8").write(json.dumps(row) + "\n")
print(json.dumps(row))
