#!/usr/bin/env python3
"""Model Gauntlet — audition local Ollama models against graded task suites.

Usage:
  python3 gauntlet.py <model> [task_name]   run all tasks (or one) against a model
  python3 gauntlet.py --board               show the leaderboard from results history
Endpoint: env GAUNTLET_HOST or local_config.json, default http://localhost:11434
"""
import json, urllib.request, re, sys, time, os, importlib.util, glob

ROOT = os.path.dirname(os.path.abspath(__file__))
_cfg = os.path.join(ROOT, "local_config.json")
CFG = json.load(open(_cfg)) if os.path.exists(_cfg) else {}
HOST = os.environ.get("GAUNTLET_HOST", CFG.get("host", "http://localhost:11434"))
RESULTS = os.path.join(ROOT, "results.jsonl")

def ask(model, prompt, options):
    t0 = time.time()
    req = urllib.request.Request(HOST + "/api/generate",
        data=json.dumps({"model": model, "prompt": prompt, "stream": False,
                         "options": options}).encode(),
        headers={"Content-Type": "application/json"})
    d = json.loads(urllib.request.urlopen(req, timeout=600).read())
    resp = d["response"]
    m = re.search(r"<think>.*?</think>", resp, re.S)
    if m: resp = resp[m.end():]              # strip reasoning-model thinking
    toks = d.get("eval_count", 0)
    tps = toks / (d.get("eval_duration", 1) / 1e9)
    return resp, {"tokens": toks, "tok_s": round(tps, 1), "secs": round(time.time() - t0, 1)}

def extract_code(text):
    blocks = re.findall(r"```(?:python)?\s*\n(.*?)```", text, re.S)
    return "\n\n".join(blocks) if blocks else text
def load_tasks(only=None):
    tasks = []
    for path in sorted(glob.glob(os.path.join(ROOT, "tasks", "*.py"))):
        name = os.path.splitext(os.path.basename(path))[0]
        if only and name != only: continue
        spec = importlib.util.spec_from_file_location(name, path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        tasks.append((name, mod))
    return tasks

def run(model, only=None, runs=1):
    tasks = load_tasks(only)
    if not tasks:
        print(f"no task named '{only}' in tasks/"); return
    total_pass = total_tests = 0
    for name, mod in tasks:
        print(f"\n=== {name} · {model} · {runs} run(s) ===")
        base_opts = getattr(mod, "OPTIONS", {"temperature": 0.3, "num_predict": 4096})
        best_p, best_results, best_perf = -1, None, None
        for i in range(runs):
            opts = dict(base_opts)
            opts["seed"] = opts.get("seed", 42) + i        # deterministic, but varied across runs
            resp, perf = ask(model, mod.PROMPT, opts)
            results = mod.grade(resp, extract_code)
            p = sum(1 for _, ok, _ in results if ok)
            if runs > 1: print(f"  run {i+1}: {p}/{len(results)} · seed {opts['seed']} · {perf['tok_s']} tok/s")
            with open(RESULTS, "a") as f:
                f.write(json.dumps({"ts": time.strftime("%Y-%m-%d %H:%M"), "model": model,
                                    "task": name, "run": i + 1, "seed": opts["seed"],
                                    "pass": p, "of": len(results), **perf}) + "\n")
            if p > best_p: best_p, best_results, best_perf = p, results, perf
        for tname, ok, detail in best_results:
            print(("PASS " if ok else "FAIL ") + tname, "->", str(detail)[:90])
        total_pass += best_p; total_tests += len(best_results)
        tag = f"best of {runs}" if runs > 1 else "score"
        print(f"{tag} {best_p}/{len(best_results)} · {best_perf['tok_s']} tok/s · {best_perf['secs']}s")
    print(f"\nTOTAL: {total_pass}/{total_tests}" + (f" (best of {runs})" if runs > 1 else ""))
    export_js()

EXPORT = os.environ.get("GAUNTLET_EXPORT", CFG.get("export", os.path.join(ROOT, "gauntlet-data.js")))
PUBLISH = os.environ.get("GAUNTLET_PUBLISH", CFG.get("publish", ""))

def export_js():
    """Publish results history for the USO COMMAND dashboard (UNIT 05)."""
    if not os.path.exists(RESULTS): return
    rows = [json.loads(l) for l in open(RESULTS)]
    with open(EXPORT, "w") as f:
        f.write("const GAUNTLET_DATA = " + json.dumps(rows) + ";")
    if PUBLISH:
        os.system("scp -o BatchMode=yes -o ConnectTimeout=5 '%s' '%s' >/dev/null 2>&1" % (EXPORT, PUBLISH))

def board():
    if not os.path.exists(RESULTS): print("no results yet"); return
    agg = {}
    for line in open(RESULTS):
        r = json.loads(line)
        a = agg.setdefault(r["model"], {"pass": 0, "of": 0, "tps": [], "runs": 0})
        a["pass"] += r["pass"]; a["of"] += r["of"]; a["tps"].append(r["tok_s"]); a["runs"] += 1
    print(f"{'MODEL':<26}{'SCORE':<10}{'AVG TOK/S':<11}RUNS")
    for m, a in sorted(agg.items(), key=lambda kv: -(kv[1]['pass'] / max(1, kv[1]['of']))):
        print(f"{m:<26}{str(a['pass'])+'/'+str(a['of']):<10}{round(sum(a['tps'])/len(a['tps']),1):<11}{a['runs']}")

if __name__ == "__main__":
    args = sys.argv[1:]
    runs = 1
    if "--runs" in args:
        i = args.index("--runs"); runs = int(args[i + 1]); del args[i:i + 2]
    if not args or args[0] in ("-h", "--help"): print(__doc__)
    elif args[0] == "--board": board()
    else: run(args[0], args[1] if len(args) > 1 else None, runs)