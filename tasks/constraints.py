"""Task: multi-constraint instruction adherence. Trivial to state, brutal to obey."""
import re

PROMPT = """Write exactly 5 bullet points about Seiko watch movement types.
Each bullet starts with "- ". The third bullet must be exactly 4 words.
Do not mention quartz. Output only the 5 bullets, nothing else."""

OPTIONS = {"temperature": 0.7, "num_predict": 512, "seed": 42}

CHECKS = ["exactly 5 bullets", "nothing but bullets", "third bullet is 4 words",
          "never says quartz", "on topic"]

def grade(resp, extract_code):
    out = []
    lines = [l.strip() for l in resp.strip().splitlines() if l.strip()]
    bullets = [l for l in lines if l.startswith("- ")]
    out.append(("exactly 5 bullets", len(bullets) == 5, f"{len(bullets)} bullets"))
    out.append(("nothing but bullets", len(lines) == len(bullets), f"{len(lines)-len(bullets)} stray lines"))
    if len(bullets) >= 3:
        words = bullets[2][2:].rstrip(".").split()
        out.append(("third bullet is 4 words", len(words) == 4, f"{len(words)} words: {bullets[2][2:]}"))
    else:
        out.append(("third bullet is 4 words", False, "missing"))
    q = re.search(r"quartz", resp, re.I)
    out.append(("never says quartz", not q, "clean" if not q else "mentioned it"))
    on_topic = re.search(r"seiko|spring drive|automatic|caliber|calibre|mechanical|hi-beat", resp, re.I)
    out.append(("on topic", bool(on_topic), "ok" if on_topic else "off topic"))
    return out