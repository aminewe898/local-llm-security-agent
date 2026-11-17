# Local LLM Security Agent

**Turning a fully‑local, uncensored 26B LLM on an 8 GB laptop into an autonomous web‑penetration‑testing agent — and measuring, honestly, exactly how capable it really is.**

![local‑first](https://img.shields.io/badge/cloud-none-success) ![cost](https://img.shields.io/badge/API%20keys-0-success) ![model](https://img.shields.io/badge/model-Gemma%204%2026B%20Heretic%20(Q4)-blue) ![hardware](https://img.shields.io/badge/GPU-RTX%205060%20Laptop%208GB-blue) ![license](https://img.shields.io/badge/license-MIT-informational)

Everything runs on one Windows laptop (RTX 5060 Laptop, 8 GB VRAM; 32 GB RAM). No cloud, no API keys, no paid services.

---

## TL;DR

I took a local uncensored model (**Gemma 4 26B‑A4B "Heretic", Q4**, via LM Studio), tuned it, wrapped it in an autonomous agent (**Hermes Agent**), gave it an offline security knowledge base, and engineered it — across **six iterations** — into an agent that can independently find and exploit real web vulnerabilities in an isolated CTF lab. Crucially, the last iteration rebuilds the **benchmark itself** so the numbers are trustworthy, not flattering.

| | Result |
|---|---|
| **Inference tuning** | 28 → **~40 tok/s** generation, 930 → **~1,500 tok/s** prompt, **16k → 65k** context — on 8 GB VRAM via MoE CPU‑offload |
| **Autonomous exploitation** | from **recon‑only** (V1) to reliably solving SQL‑injection auth bypass, IDOR, UNION schema dumps and access‑control tampering (V3–V5) |
| **The key result** | a never‑solved challenge went **0 → 3/3 reliable** after adding one *general* tool — evidence the limit was **engineering, not the model** |
| **Honesty** | an **independent scoreboard the agent can't fake** caught it over‑claiming success repeatedly; V6 quantifies the real reliability (e.g. a V3 "win" is actually only **~50%**) |

👉 Full write‑up: [`docs/full-project-report.md`](docs/full-project-report.md) · Benchmark methodology: [`bench/README.md`](bench/README.md)

---

## Why this is interesting

Most "AI hacking agent" demos use frontier cloud models and take the model's word that it succeeded. This project does the opposite and treats it as a **reliability‑ and measurement‑engineering problem on fixed, constrained local hardware**:

- **Fully local & private** — a 26B model on an 8 GB GPU; nothing leaves the machine.
- **Blind** — no solutions, no walkthroughs, no web search during challenges; no challenge answers hardcoded anywhere.
- **Independently verified** — success is read from OWASP Juice Shop's own server‑side scoreboard on the host. The agent never sees it and **cannot fake a solve**.
- **Evidence‑driven** — six iterations, each change justified by a specific failure observed in the transcripts.
- **Honest about limits** — a controlled investigation separates true model limits from fixable tooling gaps, and the final harness reports *distributions with confidence intervals*, not cherry‑picked single runs.

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

## The six iterations

| Ver | Change | Result | Lesson |
|----|--------|--------|--------|
| **V1** | baseline agent, raw shell | recon only | can *find* exposed things, can't *exploit* |
| **V2** | rewritten pentest skill + reasoning tuning | +2 SQL‑injections | methodology > raw tools; *also exposed a bug where new tools silently never loaded* |
| **V3** | structured HTTP tool (sessions, clean payloads) | IDOR solved; 2–4× faster | tooling beats hand‑rolled `curl` for multi‑step |
| **V4** | JS‑grep param discovery, loop guard, notes, proof‑gated claims | param discovery fixed; false claims **reduced** | reliability is a feature you engineer |
| **V5** | `sqli_enumerate` (sqlmap‑style UNION automation) | **schema dump 0 → 3/3** | the "ceiling" was mechanical enumeration, not reasoning |
| **V6** | a **reproducible, honest benchmark harness** (not more exploits) | single‑run "wins" were optimistic | measure distributions, not anecdotes |

Along the way I found and fixed bugs that were **silently invalidating the benchmarks** — a pooled agent gateway serving stale tools, a session token contaminating runs, a wrong‑target port collision — and caught the agent making **false success claims**, every one exposed by the independent scoreboard.

### V6 — honest benchmarking ([`bench/`](bench/))

V1–V5 each measured with **single runs**, which is how a lucky pass becomes a reported "solve." V6 rebuilds the measurement: a **fail‑loud preflight** (aborts unless Docker, the model, the *correct* target, sandbox isolation, and the arm's tools are all verified), **fresh target + sandbox every attempt** (clean solve attribution), **N repeats → k/N solve rate with 95% confidence intervals**, a recorded **false‑claim rate**, and a full **reproducibility manifest** per run (model, sampling, code hashes, image digests, GPU state).

Building it immediately caught three silent environment faults, and re‑measuring re‑contextualized an earlier "win": with repeats, **View Basket is only ~50% reliable**, and on the failing run the agent **falsely claimed success** — completely invisible to a single‑run benchmark. The harness ships a 2×2 **ablation** (tools × planning) on the *fixed* model + hardware to answer the research question: *how much autonomous capability can tools, planning, and verification recover from a small local model without upgrading it or the hardware?*

---

## What I learned (the transferable part)

- **Independent verification is load‑bearing, not optional.** A small model will confidently claim success it didn't achieve; only an oracle it can't see keeps the numbers honest.
- **Most apparent "model ceilings" were engineering gaps.** Parameter discovery, mechanical enumeration, and loop control looked like reasoning limits but were recovered with general tools — one turned a 0 into a reliable 3/3.
- **Benchmarks lie by default.** Single runs, stale caches, contaminated state, and wrong‑target mix‑ups quietly corrupt results; a fail‑loud harness that reports distributions is the fix.
- **The real residual limits** of a local 26B are long multi‑step chains and discovering non‑obvious single‑insight bypasses — not the basics.

---

## Repository layout

```
docs/              full project report + the V5 reasoning‑vs‑engineering investigation + benchmark write‑ups
model-benchmark/   model comparison harness (Gemma vs Ornith) + LM Studio tuning sweeps
agent/             safety guard hook, permission‑window script, launcher, config example, skills
security-kb/       offline security knowledge‑base MCP server (ATT&CK/CWE/CAPEC/KEV/OWASP + live CVE)
ctf-lab/           the isolated lab: MCP tool servers (v1→v5), the SQLi enumerator, blind runners,
                   challenge sets, skill evolution, scoreboard‑verified results
bench/             V6 honest‑benchmark harness: fail‑loud preflight, N‑repeat runner, report generator, ablation
```

**Where to start:** [`docs/full-project-report.md`](docs/full-project-report.md) for the narrative, then
[`ctf-lab/`](ctf-lab/) for the engineering (the `lab*_mcp.py` progression and `sqli_enum.py`), then
[`bench/`](bench/) for how the numbers are kept honest.

> This is a research / portfolio artifact, not a one‑click installer: it assumes a specific local setup
> (LM Studio + the model, Hermes Agent, Docker). The code and reports are the deliverable.

---

## Honest verdict

As an autonomous web pentester, this setup performs like a **capable junior / strong security intern**: excellent
reconnaissance, and — *with its tooling* — reliable on standard web vulnerabilities (SQLi auth bypass, IDOR, UNION
schema extraction, access‑control tampering). It needs supervision on complex multi‑step chains, it **over‑claims
success** (so it must always be independently verified), and its reliability on a given task is a *rate*, not a
guarantee. For a 26B model on an 8 GB laptop, that is a genuinely strong, and honestly measured, result.

---

## Tech stack

Gemma 4 26B‑A4B Heretic · LM Studio · Hermes Agent · MCP (Model Context Protocol) · Docker · OWASP Juice Shop · Python · PowerShell · MITRE ATT&CK/CWE/CAPEC · CISA KEV · OWASP Cheat Sheets · NVD.

## Safety & ethics

All offensive testing is confined to **OWASP Juice Shop**, a deliberately vulnerable application built and
licensed for security training, running in an **isolated Docker network with no internet access**. The agent
cannot reach any external host, and a safety hook blocks it from touching secrets or the host system. The included
tools are general‑purpose web‑assessment helpers (the kind Burp/ZAP/sqlmap provide) — **no real‑world exploits and
no challenge solutions are included**. For defensive research and learning only; don't point it at anything you
don't own or aren't authorized to test.

## Credits

See [`CREDITS.md`](CREDITS.md). Built on the open‑source work of Nous Research (Hermes Agent), LM Studio, the OWASP
Juice Shop team, MITRE, OWASP, and CISA. Licensed [MIT](LICENSE).
