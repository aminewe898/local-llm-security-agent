---
name: windows-coding-loop
description: "Default loop for any coding task on this Windows machine: explore, plan, small edits, run tests, fix, report."
---

# Windows coding loop

Use for: writing, fixing or refactoring code, adding tests, small apps and scripts.

## Steps
1. **Locate** — `search_files` (target `files`, then `content`) to find the relevant code. Read only the line ranges you need.
2. **Plan** — for anything over ~3 steps, write a `todo` list first and keep it updated.
3. **Baseline** — run the existing tests/build once before editing so you know what already failed.
   - Python: `python -m pytest -q` (or `python -m unittest -q` if no pytest). Node: `npm test`. Use the project's own scripts when they exist.
4. **Edit small** — prefer `patch` (find/replace) over rewriting whole files. One logical change at a time.
5. **Verify** — rerun the tests after each change. If something fails, read the traceback, fix the cause, rerun. After 3 failed attempts on the same error, stop and explain what you tried.
6. **Report** — what changed (files), the exact test command and its result, and anything not verified.

## Rules
- Terminal is Git Bash: bash syntax, forward slashes. Use `pwsh -NoProfile -Command "..."` only for Windows-only things.
- New projects go in `~/agent-work/<name>` unless told otherwise. Create a venv with `uv venv` for Python deps; never `pip install` globally.
- Git: commit locally on a feature branch with a clear message. `git push`, PRs and anything public need the user's OK (the guard will ask).
- Never claim "works" or "fixed" without a passing run you can quote.
