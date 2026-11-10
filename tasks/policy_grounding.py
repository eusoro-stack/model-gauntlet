"""Task: answer customer questions strictly from a store policy, with verbatim quotes.

Fitness test for store support bots: every answer must be backed by a word-for-word
quote from the policy, distractor numbers must not leak into answers, and a question
the policy does not cover must get "NOT IN POLICY" instead of an invented answer.
Formatting costs one point; the content is still graded if the JSON came wrapped in
fences or prose, so a formatting slip does not hide whether the answers were grounded.
"""
import json, re

POLICY = """Fernhill Candle Co. - Shipping and Returns

Shipping
We ship to the United States and Canada only. Orders ship within 2 business days.
Orders to the United States ship free when the order total is $50 or more.
Orders to Canada ship free when the order total is $100 or more.
Standard delivery takes 3 to 7 business days after shipment.

Returns
Full-price items may be returned within 30 days of delivery for a full refund.
Sale items may be returned within 14 days of delivery for store credit only.
Candles that have been burned cannot be returned.
To start a return, email the order number to our support team.

Damaged items
If an item arrives damaged, send a photo within 7 days of delivery and we will ship a replacement at no cost."""

PROMPT = """You are a customer support bot for an online store. Answer ONLY from the store policy
below. Never use outside knowledge and never guess.

POLICY:
<<<
""" + POLICY + """
>>>

QUESTIONS:
1. I bought a candle on sale last week and have not lit it. How many days do I have to return it?
2. How much do I have to spend to get free shipping? I live in Ohio.
3. Do you offer gift wrapping?

Return ONLY valid JSON, no markdown fences, no prose: an array of exactly 3 objects, one per
question, in order, each with exactly these keys:
  "id": the question number (1, 2 or 3)
  "answer": a short answer to the question
  "quote": the sentence from the policy that supports the answer, copied word for word
If the policy does not answer a question, set "answer" to exactly "NOT IN POLICY" and
"quote" to "" (an empty string)."""

# Low temperature: extraction work runs cold in production. 2048 tokens leaves reasoning
# models room for a short <think> block before the JSON.
OPTIONS = {"temperature": 0.2, "num_predict": 2048, "seed": 42}

CHECKS = ["clean JSON output", "schema: 3 items, exact keys",
          "q1 sale return = 14 days", "q1 quote verbatim",
          "q2 US free shipping = $50", "q2 quote verbatim",
          "q3 says NOT IN POLICY", "q3 no invented quote"]

KEYS = {"id", "answer", "quote"}
MIN_QUOTE_WORDS = 5          # a sentence, not a fragment like "14 days"

def _norm(s):
    """Collapse whitespace and straighten smart quotes; wording must still match exactly."""
    s = s.replace("’", "'").replace("‘", "'").replace("“", '"').replace("”", '"')
    return " ".join(s.split())

def _parse(txt):
    """Return (data, clean). clean is True only if the whole response was bare JSON."""
    txt = txt.strip()
    try:
        return json.loads(txt), True
    except ValueError:
        pass
    candidates = []
    m = re.search(r"```[A-Za-z]*\s*\n(.*?)```", txt, re.S)
    if m: candidates.append(m.group(1))
    for open_, close in (("[", "]"), ("{", "}")):
        i, j = txt.find(open_), txt.rfind(close)
        if 0 <= i < j: candidates.append(txt[i:j + 1])
    for c in candidates:
        try:
            return json.loads(c), False
        except ValueError:
            continue
    return None, False

def _items(data):
    """The list of answer objects, unwrapping {"answers": [...]}-style containers."""
    if isinstance(data, list): return data
    if isinstance(data, dict):
        lists = [v for v in data.values() if isinstance(v, list)]
        if len(lists) == 1: return lists[0]
    return []

def _schema(data):
    if not isinstance(data, list): return False, f"top level is {type(data).__name__}, not a list"
    if len(data) != 3: return False, f"{len(data)} items"
    if not all(isinstance(o, dict) for o in data): return False, "non-object item"
    bad = [sorted(o) for o in data if set(o) != KEYS]
    if bad: return False, f"keys {bad[0]}"
    ids = [o["id"] for o in data]
    if ids != [1, 2, 3]: return False, f"ids {ids}"
    return True, "ok"

def _verbatim(quote, fact):
    q = _norm(quote).strip("'\"")       # quotation marks around the quote are not content
    if not q: return False, "empty"
    if len(q.split()) < MIN_QUOTE_WORDS: return False, f"fragment ({len(q.split())} words): {q}"
    if q not in _norm(POLICY): return False, f"not in policy: {q[:70]}"
    if fact not in q: return False, f"wrong sentence (no '{fact}'): {q[:70]}"
    return True, "ok"

def grade(resp, extract_code):
    out = []
    data, clean = _parse(resp)
    out.append(("clean JSON output", clean, "ok" if clean else
                "parsed after stripping fences/prose" if data is not None else "unparseable"))
    if data is None:
        return out
    out.append(("schema: 3 items, exact keys", *_schema(data)))

    by_id = {}
    for pos, o in enumerate(_items(data)):
        if not isinstance(o, dict): continue
        try: key = int(o.get("id"))
        except (TypeError, ValueError): key = pos + 1
        by_id.setdefault(key, o)
    def field(n, k):
        v = by_id.get(n, {}).get(k)
        return "" if v is None else v if isinstance(v, str) else str(v)

    a1, a2, a3 = field(1, "answer"), field(2, "answer"), field(3, "answer")
    ok = bool(re.search(r"(?<!\d)14(?!\d)|\bfourteen\b", a1, re.I))
    out.append(("q1 sale return = 14 days", ok, a1[:90] or "missing"))
    out.append(("q1 quote verbatim", *_verbatim(field(1, "quote"), "14 days")))
    ok = bool(re.search(r"(?<!\d)50(?!\d)|\bfifty\b", a2, re.I))
    out.append(("q2 US free shipping = $50", ok, a2[:90] or "missing"))
    out.append(("q2 quote verbatim", *_verbatim(field(2, "quote"), "$50")))
    out.append(("q3 says NOT IN POLICY", a3.strip() == "NOT IN POLICY", a3[:90] or "missing"))
    q3 = field(3, "quote").strip()
    out.append(("q3 no invented quote", q3 == "", "empty" if not q3 else f"quoted: {q3[:70]}"))
    return out
