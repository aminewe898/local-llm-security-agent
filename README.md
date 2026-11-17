# Local LLM Security Agent

**Turning a fully-local, uncensored 26B LLM on an 8 GB laptop into a reliable autonomous web‑penetration‑testing agent — and proving, with blind benchmarks, exactly how capable it really is.**

No cloud. No API keys. No paid services. Everything runs on one Windows laptop (RTX 5060 Laptop, 8 GB VRAM; 32 GB RAM).

---

## TL;DR

I took a local uncensored model (**Gemma 4 26B‑A4B "Heretic", Q4**, served by LM Studio), tuned it, wrapped it in an autonomous agent (**Hermes Agent**), gave it an offline security knowledge base, and then engineered it — across five iterations — into an agent that can **independently find and exploit real web vulnerabilities** in an isolated CTF lab, verified by an **independent scoreboard it cannot fake**.

Key outcomes:

| | Result |
|---|---|
| **Inference tuning** | 28 → **~40 tok/s** generation, 930 → **~1,500 tok/s** prompt, **16k → 65k** context — all on 8 GB VRAM via MoE CPU‑offload |
| **Autonomous CTF (OWASP Juice Shop, blind)** | **V1: 3/7 → V5: 9 distinct vulns solved**, scoreboard‑verified |
| **The headline fix** | A never‑solved challenge (UNION SQL‑injection schema dump) went **0 → 3/3 reliable** after one general tool — proving the limit was *engineering*, not the model |
| **Reliability** | False "I solved it" claims driven to **0** via proof‑gated verification; every claim independently checked |

**Honest verdict:** as an autonomous pentester this setup performs at the level of a **capable junior / strong security intern** — excellent recon, reliable on standard web vulns *with the right tooling*, needs supervision on complex multi‑step chains, and must always be independently verified.

👉 Full write‑up: [`docs/full-project-report.md`](docs/full-project-report.md)

---

## Why this is interesting

Most "AI hacking agent" demos use frontier cloud models and trust the model's own claim of success. This project does the opposite and treats it as a **reliability‑engineering problem on constrained local hardware**:

- **Fully local & private** — a 26B model on an 8 GB GPU, nothing leaves the machine.
- **Blind** — the agent gets no solutions, no walkthroughs, and no web search during challenges.
- **Independently verified** — success is read from OWASP Juice Shop's own server‑side scoreboard on the host; the agent physically cannot fake a solve.
- **Iterative, evidence‑driven engineering** — five versions, each change justified by a specific observed failure in the transcripts.
- **Separating model limits from engineering gaps** — a controlled investigation (V5) shows most of the apparent "intelligence ceiling" was actually missing tooling.

---

## Architecture

```
            ┌──────────────────────────── your laptop (offline) ────────────────────────────┐
            │                                                                                │
   you ───► │  Hermes Agent ──► LM Studio ──► Gemma 4 26B‑A4B Heretic (Q4, 65k ctx, tuned)   │
            │       │                                                                        │
            │       ├─ safety guard hook (blocks secrets/dangerous cmds; timed grant window) │
            │       ├─ seckb MCP  (offline ATT&CK · CWE · CAPEC · CISA KEV · OWASP + live CVE)│
            │       └─ lab MCP ──► docker exec ──►  ┌─ attacker container (no internet)       │
            │                                        │     curl / python / sqli tools         │
            │   independent scoreboard check ◄───────┼─► OWASP Juice Shop (target)            │
            │     (host reads /api/Challenges)        └─ isolated Docker network ─────────────┘
            └────────────────────────────────────────────────────────────────────────────────┘
```

The agent's **only** way to run anything is a sandboxed container with no internet and no host filesystem — the real security boundary, not just a prompt rule.

---

## The five iterations (what the benchmarks taught me)

| Ver | Change | Verified result | Lesson |
|----|--------|-----------------|--------|
| **V1** | baseline agent, raw shell | 3/7 (recon only) | can *find* exposed things, can't *exploit* |
| **V2** | rewritten pentest skill + reasoning tuning | 5/7 (+2 SQLi) | methodology > raw tools; *also found a bug where new tools silently never loaded* |
| **V3** | structured HTTP tool (sessions, clean payloads) | IDOR solved; 2/3 unseen; 2–4× faster | tooling beats hand‑rolled `curl` for multi‑step |
| **V4** | JS‑grep param discovery, loop guard, notes, proof‑gated claims | param discovery fixed; **false claims → 0** | reliability is a feature you engineer |
| **V5** | `sqli_enumerate` (sqlmap‑style UNION automation) | **schema dump 0 → 3/3** | the "ceiling" was mechanical enumeration, not reasoning |
| **V6** | a **reproducible, honest benchmark harness** (not more exploits) | single‑run "wins" were optimistic | measure distributions, not anecdotes |

Along the way I found and fixed bugs that were **silently invalidating the benchmarks** — a pooled agent gateway serving stale tools, and a session token contaminating runs — and caught the agent making **false success claims** repeatedly, every one exposed by the independent scoreboard.

### V6 — honest benchmarking ([`bench/`](bench/))

V1–V5 each measured with **single runs**, which is how a lucky pass becomes a reported "solve." V6 rebuilds the
measurement itself: a **fail‑loud preflight** (aborts if Docker, the model, the *correct* target, sandbox
isolation, or the arm's tools aren't verified), **fresh target + sandbox every attempt** (clean solve
attribution), **N repeats → k/N solve rate with confidence intervals**, a recorded **false‑claim rate**, and a
full **reproducibility manifest** per run. Building it immediately caught three silent environment faults
(broken Docker network, another app squatting on the target port, an env‑passthrough bug) — the exact class of
error that quietly corrupts benchmarks.

It also re‑contextualized an earlier "win": re‑measured with repeats, **View Basket is only ~50% reliable**, and
on the failing run the agent **falsely claimed success** — invisible to a single‑run benchmark. The harness also
ships a 2×2 **ablation** (tools × planning) on the *fixed* model + hardware to answer the project's research
question: *how much autonomous capability can tools, planning, and verification recover from a small local model
without upgrading it?* See [`bench/README.md`](bench/README.md) for the methodology and honest limitations.

---

## What's in here

```
docs/                model/agent benchmark reports + the V5 reasoning‑vs‑engineering investigation
model-benchmark/     model comparison harness (Gemma vs Ornith) + LM Studio tuning sweeps
agent/               the safety guard hook, permission‑window script, launcher, config example, skills
security-kb/         offline security knowledge base MCP server (ATT&CK/CWE/CAPEC/KEV/OWASP + live CVE)
ctf-lab/             the isolated lab: MCP tool servers (v1→v5), the SQLi enumerator, blind harness,
                     challenge sets, skill evolution, and the raw scoreboard‑verified results
```

Start with [`docs/full-project-report.md`](docs/full-project-report.md), then the code in `ctf-lab/` (the `lab*_mcp.py` progression and `sqli_enum.py` tell the engineering story).

---

## Tech stack

Gemma 4 26B‑A4B Heretic · LM Studio · Hermes Agent · MCP (Model Context Protocol) · Docker · OWASP Juice Shop · Python · PowerShell · MITRE ATT&CK/CWE/CAPEC · CISA KEV · OWASP Cheat Sheets · NVD.

---

## Safety & ethics

All offensive testing is confined to **OWASP Juice Shop**, a deliberately vulnerable application built and licensed specifically for security training, running in an **isolated Docker network with no internet access**. The agent cannot reach any external host, and a safety hook blocks it from touching secrets or the host system. The included tools are general‑purpose web‑assessment helpers (the kind of thing Burp/ZAP/sqlmap provide) — there are **no exploits for real‑world systems and no challenge solutions hardcoded anywhere**.

This repository is for defensive security research, learning, and portfolio demonstration. Don't point it at anything you don't own or aren't authorized to test.

## Credits

See [`CREDITS.md`](CREDITS.md). Built on the open‑source work of Nous Research (Hermes Agent), LM Studio, the OWASP Juice Shop team, MITRE, OWASP, and CISA.
