---
name: security-research
description: "Any cybersecurity question: CVEs, attack techniques, weaknesses, code review, secure coding, hardening. Look it up in seckb, classify precisely, label evidence, cite IDs."
---

# Security research (seckb)

Use the **seckb** MCP tools before answering from memory — small models misremember IDs, scores and versions.

## Tools
- `sec_search(query, source)` — `attack`, `cwe`, `capec`, `kev`, `owasp`, or empty for all. Exact IDs work (T1059.001, CWE-79, CAPEC-66, CVE-2024-3400).
- `sec_get(id)` — full entry. CWE entries start with **Abstraction** and **Mapping usage**; CWE and CAPEC entries list **ChildOf/ParentOf** relations.
- `cve_lookup(cve_id)` — live NVD details + CISA exploited flag.

## Classification rules (follow strictly)
1. **Confirmed vs hypothetical.** Only call something a vulnerability if the code/evidence shows it (e.g. user input
   concatenated into SQL). "Accepts user input that reaches a query" is NOT a vulnerability if the value is bound as a
   parameter. If you haven't seen the code path, say "possible, unconfirmed".
2. **CWE: most specific allowed entry.** Pick the lowest-level CWE whose Mapping usage is `Allowed` (e.g. CWE-89 for SQL
   injection). Never name a `Discouraged` class-level CWE (e.g. CWE-20, CWE-707) as the classification or "root cause"
   when a specific one fits. Only mention it as a parent, labelled as such.
3. **CAPEC: general before specific.** Start from the standard pattern (e.g. CAPEC-66 SQL Injection). Add a detailed
   child (e.g. CAPEC-7 Blind SQL Injection) only if the evidence shows that variant (no error output, inference by
   timing/boolean responses). Check the ChildOf line with `sec_get`.
4. **Fixes from the primary source.** Take remediation from the OWASP cheat sheet you retrieved. For SQL injection:
   parameterized queries / prepared statements first; allowlist only for parts that cannot be bound (table/column
   names, sort order). Never recommend blocklisting or "filtering SQL keywords" as a defense — say it is not one.
5. **No unretrieved claims.** Don't cite a classification (e.g. an OWASP Top 10 category) unless a tool result
   contained it; otherwise mark it unverified.

## Answer format
- **Verified** — facts quoted from tool results, each with its ID and URL.
- **Inferred** — your reasoning from those facts, labelled as inference.
- **Unverified** — anything you could not confirm with a tool. Say so plainly.
- Then the fix, then what to patch/check next.

## Scope
Defensive focus. Hands-on testing only against systems the user owns (their localhost, code, machine). Never scan,
probe or attack third-party hosts.

## Refresh the data
Ask the user first. Then: `hermes gateway stop --yes`, re-download into `~/tools/seckb/data/`, run `python -I build_index.py` in `~/tools/seckb`.
