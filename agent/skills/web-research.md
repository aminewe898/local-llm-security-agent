---
name: web-research
description: "Answer questions that need current facts: search, read 2-4 sources, cross-check, cite URLs."
---

# Web research

1. For a library/framework/API question, first use the context7 tools (`resolve-library-id`, then `query-docs`).
2. Otherwise `web_search` with ONE string argument `query` (not `queries`); add the year for anything time-sensitive.
3. Read the 2-4 most relevant results with the **fetch** MCP tool (`fetch` with `url`; raise `max_length` for long pages). `web_extract` is not configured on this machine. Prefer official docs, release notes and primary sources over SEO blogs.
   For GitHub facts (releases, repos, issues) prefer `gh` in the terminal: e.g. `gh release view --repo OWNER/REPO`.
4. Cross-check: if sources disagree, say so and say which you trust and why.
5. Answer briefly, then list the URLs you actually used. Never invent a URL or a number.
6. If a page is blocked (403/paywall/bot wall), load the `blocked-page-recovery` skill rather than retrying the same fetch.
