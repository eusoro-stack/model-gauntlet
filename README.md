# Model Gauntlet

Audition rig for local Ollama models. Every model that joins the roster earns
its role here first — no vibes, only scores.

Born from a real finding: the same 14B model scored 5/5 on a coding task, then
3/6 on the identical task an hour later. Single runs are noise. This harness
makes local-LLM evaluation seeded, repeatable, and machine-graded.

## Use

    python3 gauntlet.py hermes3:8b              # run all tasks
    python3 gauntlet.py hermes3:8b --runs 3     # best-of-3 per task (recommended)
    python3 gauntlet.py qwen2.5-coder:14b orchestrator   # one task
    python3 gauntlet.py --board                 # leaderboard from all history

Every task pins a base seed (42); `--runs N` uses seeds 42, 43, 44… so any
score is reproducible. Best-of-N is the honest number.

## Configuration

Defaults to Ollama at `http://localhost:11434`. Override via environment or an
optional gitignored `local_config.json`:

    GAUNTLET_HOST     Ollama endpoint (e.g. a GPU box on your tailnet)
    GAUNTLET_EXPORT   where to write gauntlet-data.js (dashboard data feed)
    GAUNTLET_PUBLISH  optional scp destination to push the data feed after runs

    // local_config.json
    { "host": "http://gpu-box:11434", "export": "...", "publish": "user@host:path" }

## Tasks

- `orchestrator` — model writes a `plan()` function; graded by **executing it**
  against hidden tests. Catches interface violations: a reasoning model once
  produced 4,600 words of deliberation, then named the function wrong. 0/5.
- `json_discipline` — strict JSON schema output, no fences, no prose.
  Fitness test for bot and tool-call duty.
- `constraints` — exact bullet counts, word counts, forbidden words.
  Trivial to state, brutal to obey; 8B models fail one constraint half the time.

## Add a task

Drop a `tasks/<name>.py` defining `PROMPT` (str), optional `OPTIONS` (dict of
Ollama options), and `grade(resp, extract_code) -> [(test_name, bool, detail)]`.
It is picked up automatically.

## History

Results append to `results.jsonl` — timestamp, model, task, run, seed, score,
tok/s. The leaderboard aggregates everything ever run. The repo ships with the
founding results from an RTX 4080: a fine-tuned 8B beating a 14B reasoner on
instruction adherence at twice the speed.
