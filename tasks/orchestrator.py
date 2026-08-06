"""Task: dependency-ordered deployment plan. Grades code correctness + interface obedience."""

PROMPT = """Write a single Python function `plan(services)` for a deployment orchestrator.

Input: dict mapping service name -> list of services it depends on.
Example: {"bot": ["db", "cache"], "db": [], "cache": ["db"]}

Requirements:
1. Return a list of service names in a valid start order (dependencies first).
2. If there is a circular dependency, raise ValueError with the message "cycle detected".
3. If a service depends on something not defined in the dict, treat that dependency as already running (ignore it).
4. The order must be deterministic: when multiple services are startable, start them in alphabetical order.
5. Standard library only. The function MUST be named exactly plan. Output ONLY a python code block containing the function."""

OPTIONS = {"temperature": 0.3, "num_predict": 8192, "seed": 42}

CHECKS = ["function named plan", "valid order", "alphabetical tiebreak",
          "cycle raises exact msg", "unknown dep ignored", "real PM2 stack"]

def grade(resp, extract_code):
    out = []
    ns = {}
    try:
        exec(extract_code(resp), ns)
    except Exception as e:
        return [("function named plan", False, f"code did not execute: {e!r}")]
    plan = ns.get("plan")
    out.append(("function named plan", bool(plan), "found" if plan else
                [k for k, v in ns.items() if callable(v) and not k.startswith("__")]))
    if not plan: return out
    def t(name, fn, check):
        try:
            r = fn(); out.append((name, check(r), r))
        except ValueError as e: out.append((name, check(e), str(e)))
        except Exception as e: out.append((name, False, repr(e)))
    t("valid order", lambda: plan({"bot": ["db", "cache"], "db": [], "cache": ["db"]}),
      lambda r: r == ["db", "cache", "bot"])
    t("alphabetical tiebreak", lambda: plan({"c": [], "a": [], "b": []}),
      lambda r: r == ["a", "b", "c"])
    t("cycle raises exact msg", lambda: plan({"a": ["b"], "b": ["a"]}),
      lambda r: isinstance(r, ValueError) and str(r) == "cycle detected")
    t("unknown dep ignored", lambda: plan({"bot": ["tailscale"], "db": []}),
      lambda r: isinstance(r, list) and sorted(r) == ["bot", "db"])
    t("real PM2 stack", lambda: plan({"openclaw": ["ollama"], "sentinel": ["ollama", "caddy"],
                                      "ollama": [], "caddy": [], "tpms": ["caddy"]}),
      lambda r: isinstance(r, list) and r.index("ollama") < r.index("openclaw")
                and r.index("caddy") < r.index("sentinel") and r.index("ollama") < r.index("sentinel")
                and r.index("caddy") < r.index("tpms"))
    return out