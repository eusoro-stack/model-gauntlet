"""Task: strict JSON output for bot/tool-call work. The hermes3 home turf."""
import json

PROMPT = """Return ONLY valid JSON, no markdown fences, no prose. An array of exactly 3 objects,
each with keys "model", "vram_gb", "best_for". Rank qwen2.5-coder:14b, hermes3:8b, and
moondream for a Telegram bot that must read screenshots and write Python."""

OPTIONS = {"temperature": 0.2, "num_predict": 1024, "seed": 42}

def grade(resp, extract_code):
    out = []
    txt = resp.strip()
    fenced = "```" in txt
    out.append(("no markdown fences", not fenced, "clean" if not fenced else "used fences"))
    if fenced:
        txt = extract_code(txt).strip()
    try:
        data = json.loads(txt)
        out.append(("parses as JSON", True, "ok"))
    except Exception as e:
        out.append(("parses as JSON", False, repr(e)))
        return out
    out.append(("exactly 3 objects", isinstance(data, list) and len(data) == 3,
                len(data) if isinstance(data, list) else type(data).__name__))
    keys_ok = isinstance(data, list) and all(
        isinstance(o, dict) and set(o) == {"model", "vram_gb", "best_for"} for o in data)
    out.append(("exact keys", keys_ok, "ok" if keys_ok else "key mismatch"))
    vision_ok = isinstance(data, list) and any(
        "moondream" in str(o.get("model", "")) and any(w in str(o.get("best_for", "")).lower()
        for w in ("vision", "image", "screenshot")) for o in data if isinstance(o, dict))
    out.append(("moondream flagged for vision", vision_ok, "ok" if vision_ok else "missed"))
    return out