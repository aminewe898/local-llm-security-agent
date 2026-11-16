---
name: lmstudio-models
description: "Inspect or manage local LM Studio models with the lms CLI without unloading the model you run on."
---

# LM Studio models (lms CLI)

You run on `gemma-4-26b-a4b-it-qat-heretic`, served by LM Studio at http://127.0.0.1:1235.
**Unloading or reloading that model ends your own session — never do it.**

## Read-only (safe)
- `lms ps` — loaded models, context size, parallel slots
- `lms ls` — downloaded models
- `curl -s http://127.0.0.1:1235/api/v0/models` — JSON incl. capabilities
- `nvidia-smi --query-gpu=memory.used,memory.total,pstate,power.draw --format=csv`

## Changes (ask the user first)
- Loading a second model will not fit in 8 GB VRAM next to Gemma and will slow everything.
- Downloads (`lms get`) are multi-GB: state size and source, then ask.
- Tuned load settings live in LM Studio's per-model config; do not edit files under ~/.lmstudio.
