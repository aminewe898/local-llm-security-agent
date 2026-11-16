# CTF lab — isolated, blind, independently‑scored

The harness that benchmarks the agent as an autonomous web pentester against **OWASP Juice Shop**, with
hard isolation and verification the agent cannot game.

## Isolation (the real security boundary)

```
docker network create --internal ctflab          # no internet
ctf-juice     : OWASP Juice Shop,  127.0.0.1:3000 published for host-side scoring only
ctf-attacker  : alpine + curl/python,  on ctflab ONLY — no internet, no host mounts
```
The agent's lab tools run commands **inside `ctf-attacker`** via `docker exec`. That container can reach the
target and nothing else — verified: outbound internet is blocked, there are no host filesystem mounts.

## Verification (unfakeable)

Juice Shop detects a successful exploit **server‑side** and flips `solved: true` in `/api/Challenges`.
The harness reads that endpoint **from the host** before and after each attempt. The agent never sees the
scoreboard and cannot mark anything solved — only a real exploit does. (This caught three false
"I solved it" claims across versions.)

## The tool servers (MCP) — how they evolved

| File | Adds |
|---|---|
| `lab_mcp.py`  (v1) | `lab_shell` — raw bash in the sandbox |
| `lab2_mcp.py` (v3) | `http_map` (discover routes from JS), `http_req` (structured, session‑persistent) |
| `lab3_mcp.py` (v3) | enforces structured HTTP; `http_decode`; removes raw shell |
| `lab4_mcp.py` (v4) | `http_grep_js` (find **parameter** names in JS), loop guard, `note` scratchpad |
| `lab5_mcp.py` (v5) | `sqli_enumerate` — sqlmap‑style breakout + column‑count automation |

`httpreq.py` / `httpreq4.py` run inside the sandbox and provide the persistent HTTP session + loop guard.
`sqli_enum.py` is the UNION‑injection enumerator (finds the breakout and column count, returns a template —
it extracts nothing and hardcodes no answer).

## The harness

`run_ctf*.py` — for each challenge: reset Juice Shop + the sandbox session, snapshot the scoreboard, run one
locked‑down Hermes session (blind; no web search), snapshot again, attribute the solve. `challenges/*.json`
are the challenge ladders (public objective text only — no solutions). `skills/web-pentest-v*.md` show the
methodology skill evolving. `tools/` holds analysis helpers (`dump_session.py`, `live_watch.py`,
`diag_probe.py`). `results/*.jsonl` are the raw scoreboard‑verified outcomes.

## Reproducing (prerequisites)

LM Studio with the Gemma model loaded, Hermes Agent installed, Docker Desktop, and the `lab*`/`seckb` MCP
servers wired into a Hermes profile (see `../agent/config.example.yaml`). Bring up the lab, then run a
harness, e.g. `python run_ctf_v5.py v5_validate.json results/out.jsonl`. This is a research/portfolio
artifact, not a one‑click installer — paths and the LM Studio model id are environment‑specific.
