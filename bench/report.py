"""V6 honest report generator. Reads one or more benchmark result files and emits an auditable summary:
 - per-challenge solve RATE k/N with a 95% Wilson interval (small N => wide interval, stated honestly)
 - false-claim rate (claimed SOLVED but scoreboard says no) and under-claim rate
 - cost (median duration, tool calls, tokens)
 - if several arms are given, the ablation comparison answering 'how much does each lever recover?'
Usage: python report.py <results1.jsonl> [results2.jsonl ...]  > report.md
"""
import json, math, os, sys
from collections import defaultdict


def wilson(k, n, z=1.96):
    if n == 0:
        return (0.0, 0.0)
    p = k / n
    d = 1 + z * z / n
    c = p + z * z / (2 * n)
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return ((c - half) / d, (c + half) / d)


def med(xs):
    xs = sorted(x for x in xs if x is not None)
    return xs[len(xs) // 2] if xs else 0


def load(path):
    return [json.loads(l) for l in open(path, encoding="utf-8")]


def arm_stats(rows):
    byk = defaultdict(list)
    for r in rows:
        byk[r["key"]].append(r)
    per = {}
    for k, rs in byk.items():
        n = len(rs)
        k_solved = sum(r["solved"] for r in rs)
        lo, hi = wilson(k_solved, n)
        per[k] = {
            "name": rs[0]["name"], "difficulty": rs[0]["difficulty"],
            "n": n, "solved": k_solved, "rate": k_solved / n, "ci": (lo, hi),
            "false_claims": sum(1 for r in rs if r["claimed_solved"] and not r["solved"]),
            "under_claims": sum(1 for r in rs if r["solved"] and not r["claimed_solved"]),
            "med_s": med([r["duration_s"] for r in rs]),
            "med_calls": med([r["tool_calls"] for r in rs]),
            "med_out_tok": med([r.get("output_tokens") for r in rs]),
        }
    N = sum(p["n"] for p in per.values())
    S = sum(p["solved"] for p in per.values())
    return {
        "per": per,
        "attempts": N, "solves": S,
        "micro_rate": S / N if N else 0,                       # pooled solves / attempts
        "macro_rate": sum(p["rate"] for p in per.values()) / len(per) if per else 0,  # mean per-challenge
        "false_claim_rate": sum(p["false_claims"] for p in per.values()) / N if N else 0,
    }


def main(paths):
    arms = {}
    for p in paths:
        rows = load(p)
        label = rows[0]["arm"] if rows else os.path.basename(p)
        arms[label] = arm_stats(rows)
    print("# V6 Benchmark Report\n")
    print("Honest + reproducible: fresh target & sandbox per attempt, N repeats, host-side scoreboard "
          "verification, preflight-gated tools. Rates are k/N with 95% Wilson intervals (small N => wide).\n")
    for label, st in arms.items():
        print(f"## Arm: `{label}`\n")
        print(f"- attempts **{st['attempts']}**, solves **{st['solves']}**")
        print(f"- pooled solve rate **{st['micro_rate']*100:.0f}%**, per-challenge mean **{st['macro_rate']*100:.0f}%**")
        print(f"- false-claim rate **{st['false_claim_rate']*100:.0f}%** (claimed solved but scoreboard said no)\n")
        print("| challenge | diff | solve rate (k/N) | 95% CI | false/under claims | med s | med calls |")
        print("|---|---|---|---|---|---|---|")
        for k, c in sorted(st["per"].items(), key=lambda kv: kv[1]["difficulty"]):
            lo, hi = c["ci"]
            print(f"| {c['name']} | {c['difficulty']} | {c['solved']}/{c['n']} ({c['rate']*100:.0f}%) | "
                  f"{lo*100:.0f}-{hi*100:.0f}% | {c['false_claims']}/{c['under_claims']} | {c['med_s']} | {c['med_calls']} |")
        print()
    if len(arms) > 1:
        print("## Ablation — recovered capability per lever\n")
        print("| arm | pooled solve rate | mean per-challenge | false-claim rate |")
        print("|---|---|---|---|")
        for label, st in arms.items():
            print(f"| {label} | {st['micro_rate']*100:.0f}% | {st['macro_rate']*100:.0f}% | {st['false_claim_rate']*100:.0f}% |")
        print()


if __name__ == "__main__":
    main(sys.argv[1:])
