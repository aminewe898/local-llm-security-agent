# Credits & third‑party components

This project is original engineering and documentation built **on top of** excellent open‑source work.
It bundles none of their source — you install each tool yourself.

| Component | Role here | Project / License |
|---|---|---|
| **Hermes Agent** | the autonomous agent runtime | Nous Research — MIT |
| **LM Studio** | local model server (OpenAI‑compatible) | LM Studio — proprietary, free |
| **Gemma 4 26B‑A4B** | the base model (uncensored community build used locally) | Google — Gemma license |
| **OWASP Juice Shop** | the deliberately‑vulnerable CTF target | OWASP — MIT |
| **Model Context Protocol (MCP)** | tool/plugin interface | Anthropic — open spec |
| **MITRE ATT&CK / CWE / CAPEC** | security knowledge base content | MITRE — free for use with attribution |
| **CISA KEV** | known‑exploited‑vulnerabilities feed | CISA — public domain |
| **OWASP Cheat Sheet Series** | remediation guidance | OWASP — CC BY‑SA |
| **NVD** | live CVE lookups | NIST — public |

The code in this repository (the MCP tool servers, the SQLi enumerator, the safety guard, the blind
benchmark harness, the knowledge‑base indexer, the skills, and all reports) is by the repository author,
MIT‑licensed.

Security content from MITRE/OWASP/CISA/NVD is **not redistributed** here — `security-kb/build_index.py`
downloads it from the official sources at build time.
