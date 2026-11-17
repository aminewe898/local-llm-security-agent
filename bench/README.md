# V6 — reproducible, honest benchmarking

The point of V6 is **a measurement pipeline you can trust**, not more exploits. Everything the earlier
versions measured had reproducibility holes; this harness closes them and fails loudly when it can't.

## What makes a number here trustworthy

1. **Fail-loud preflight** (`preflight.py`). Before any measurement, every precondition is checked and the
   run **aborts** if one is off:
   - Docker up · the pinned model loaded · Juice Shop healthy *and is actually Juice Shop* · sandbox up ·
     **sandbox has no internet** · the arm's server **defines** the expected tools · the gateway **discovers**
     them. During development this preflight caught a broken docker network, a *wrong target* (another app
     squatting on the port), and an env-passthrough bug — each of which would have silently produced garbage.
2. **Clean state every attempt** (`bench_lib.reset_juice` + `reset_sandbox`). Juice Shop is restarted so the
   before-snapshot is empty, which makes solve **attribution unambiguous** (no "solved in a previous run"
   confound). The sandbox session/loop-log/notes are wiped so no identity or history leaks between attempts.
3. **Independent verification.** A solve is only counted if Juice Shop's own server-side scoreboard
   (`/api/Challenges`, read from the host) flips the challenge's key. The agent never sees it and cannot fake
   it. We also record **claimed-vs-verified** to compute a **false-claim rate** — the model over-claims, and
   this quantifies it honestly.
4. **N repeats → distributions, not anecdotes** (`--repeats`). The model is non-deterministic (temp 0.6), so a
   single solve or failure is noise. Reporting is **k/N solve rate with a 95% Wilson interval**.
5. **Full environment manifest** (`*.manifest.json`): timestamp, model + sampling, config + skill hashes,
   expected tools, Juice Shop version + image, attacker image digest, Hermes version, repo commit, GPU power
   state, and the preflight result. Enough to audit or re-derive a run.

## Arms (for the research question)

`arms.json` defines a 2×2 ablation on the **same fixed model and hardware**, isolating the levers:

| arm | tools | planning (skill) |
|---|---|---|
| `baseline` | raw shell only | terse |
| `tools_only` | full structured + `sqli_enumerate` | terse |
| `planning_only` | raw shell only | full methodology + proof-gating |
| `full` | full structured + enumerator | full methodology + proof-gating |

Comparing arms answers: *how much autonomous capability does each lever (tools / planning / verification)
recover from a fixed small local model, without upgrading the model or hardware?*

## Running

```bash
# one arm over a challenge suite, 3 clean repeats each
python run_bench.py --arm full --suite ../challenges.json --repeats 3 --out ../results/bench/full.jsonl
# honest report (one or many arms -> ablation table)
python report.py ../results/bench/baseline.jsonl ../results/bench/tools_only.jsonl \
                 ../results/bench/planning_only.jsonl ../results/bench/full.jsonl > ../results/bench/report.md
```

## Honest limitations

- **Non-determinism is embraced, not removed.** Temp 0.6 means repeats vary; that's why we report rates +
  intervals. A strict-determinism mode (temp 0) would trade realism for repeatability.
- **Small N** (a few repeats per challenge, for wall-clock reasons) gives **wide confidence intervals** — the
  intervals are reported, not hidden. More repeats tighten them.
- **Incidental solves** (a challenge tripped as a side effect of another objective) are recorded separately,
  never counted toward the target challenge.
- **Challenge difficulty is uneven** across Juice Shop; the suite is chosen to span easy→hard, and the per-
  challenge breakdown is always shown so aggregates can't hide a skew.
- Verification covers *that* a vuln was exploited, not the *quality* of the agent's explanation.
