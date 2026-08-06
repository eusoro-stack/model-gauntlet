# Model Gauntlet

Audition rig for local Ollama models. Every model that joins the roster earns
its role here first — no vibes, only scores.

Born from a real finding: the same 14B model scored 5/5 on a coding task, then
3/6 on the identical task an hour later. Single runs are noise. This harness
makes local-LLM evaluation seeded, repeatable, and machine-graded.

## Current standings

7 models · 3 task suites · 3 seeded runs each · 63 scored generations.
Served by Ollama on an RTX 4080.

| Model | Score | Avg tok/s |
|---|---|---|
| llama3.1:latest | 37/48 (77.1%) | 118.1 |
| hermes3:8b | 35/48 (72.9%) | 119.4 |
| qwen2.5-coder:14b | 33/48 (68.8%) | 65.6 |
| qwen2.5:14b | 32/48 (66.7%) | 63.4 |
| phi4:latest | 28/48 (58.3%) | 62.0 |
| deepseek-r1:14b | 28/48 (58.3%) | 57.7 |
| mistral-small:latest | 28/48 (58.3%) | 35.1 |

Both 8B models beat every 14B model on these tasks, at roughly twice the
throughput. Parameter count is not the story; instruction adherence is.

`deepseek-r1:14b` is the cautionary tale — it burned ~8 minutes per
`orchestrator` run generating reasoning tokens, versus seconds for everything
else, and still landed mid-table.

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
Ollama options), `CHECKS` (list of every check name the grader can score), and
`grade(resp, extract_code) -> [(test_name, bool, detail)]`. It is picked up
automatically.

`CHECKS` is not optional bookkeeping. Graders naturally bail out early when a
response is too malformed to keep testing — unparseable JSON, code that won't
execute. Left alone, that shrinks the denominator and *rewards* the worst
failures: 0/2 dents a score less than 0/5. The harness pads every result up to
`CHECKS`, marking unreached checks failed, so a broken response is always
measured against the full bar.

This was a real bug here, not a hypothetical. It sat in the graders for weeks
and quietly inflated three models before an audit caught it.

## History

Results append to `results.jsonl` — timestamp, model, task, run, seed, score,
tok/s. The leaderboard aggregates everything ever run. The repo ships with the
founding results from an RTX 4080: a fine-tuned 8B beating a 14B reasoner on
instruction adherence at twice the speed.
