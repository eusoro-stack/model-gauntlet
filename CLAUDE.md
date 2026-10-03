# Model Gauntlet — Project Guide

## What this is
A small Python harness that auditions local Ollama models against graded task
suites. Each task sends a fixed prompt, grades the response by machine
(exact checks, or executing the returned code), and appends a score line to
`results.jsonl`. Runs are seeded so scores are reproducible. Zero dependencies
beyond Python 3 stdlib. Models are served by Ollama on the owner's GPU PC
(RTX 4080); this repo only talks to that endpoint over HTTP.

## Key commands
```bash
python3 gauntlet.py --help                       # usage (safe, no network)
python3 gauntlet.py --board                      # leaderboard from results.jsonl (local, read-only)
python3 gauntlet.py hermes3:8b                   # run all tasks against one model
python3 gauntlet.py hermes3:8b --runs 3          # best-of-3 per task (recommended, honest number)
python3 gauntlet.py qwen2.5-coder:14b orchestrator   # run a single task
```
- Running a model needs a reachable Ollama. Default is `http://localhost:11434`;
  override with env `GAUNTLET_HOST` or a gitignored `local_config.json`.
- Every model run appends one JSON line per task per run to `results.jsonl`
  (ts, model, task, run, seed, pass, of, tokens, tok_s, secs), then writes
  `gauntlet-data.js` (gitignored) for the owner's private dashboard.
- `docs/index.html` is the public leaderboard (GitHub Pages). It is static:
  it fetches `results.jsonl` from the `main` branch at page load, so the live
  board only changes when a new `results.jsonl` is committed and pushed to main.

## Project structure
```
gauntlet.py              # whole harness: ask Ollama, grade, pad, append, board, export
tasks/                   # one file per task; auto-discovered by filename
  orchestrator.py        #   model writes plan(); graded by executing it against hidden tests
  json_discipline.py     #   strict JSON output, no fences, no prose
  constraints.py         #   exact bullet/word counts, forbidden words
results.jsonl            # append-only score history (the data behind README + docs page)
results-legacy.jsonl     # pre-seed-era results, kept for reference; not read by anything
docs/index.html          # public leaderboard page
README.md                # public write-up with the current standings table
```

## Gotchas
- Seeds: each task pins `seed: 42` in `OPTIONS`; `--runs N` uses 42, 43, 44...
  Changing a task's PROMPT, OPTIONS, or CHECKS invalidates comparison with old
  results. Treat existing tasks as frozen; add a new file instead.
- `CHECKS` must list every check name the grader can emit. The harness pads
  missing checks as failures so a crashed response is scored against the full bar.
- `results.jsonl` is append-only history. Do not rewrite, dedupe, or reorder it;
  the README table and the docs page are derived from it. If you change it, the
  README standings table should be regenerated to match (`--board`).
- Do not hand-edit `results-legacy.jsonl`, `gauntlet-data.js`, or `local_config.json`.
- `orchestrator` grading calls `exec()` on model output. Only run it against models
  you trust on a machine you control.
- Keep this repo public-safe: no hostnames, IPs, Tailscale names, or scp targets
  in committed files. Those belong in `local_config.json` (gitignored).

## Related projects
Sibling repos by the same owner: uso-command (dashboard that consumes
`gauntlet-data.js`), roon-myclaw, kinetix-ide, breathefirst-app, revoice, tadbot.
