"""Unit tests for the policy_grounding grader. No network, no Ollama.

Run from the repo root:  python3 -m unittest discover -s tests -v
"""
import json, os, sys, unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
import gauntlet  # noqa: E402  (needs ROOT on sys.path first)

TASK = dict(gauntlet.load_tasks("policy_grounding"))["policy_grounding"]

Q1 = "Sale items may be returned within 14 days of delivery for store credit only."
Q2 = "Orders to the United States ship free when the order total is $50 or more."

def answers(**over):
    """A perfect answer set; keyword overrides like q1_answer=... replace one field."""
    items = [
        {"id": 1, "answer": "14 days, for store credit.", "quote": Q1},
        {"id": 2, "answer": "$50 or more.", "quote": Q2},
        {"id": 3, "answer": "NOT IN POLICY", "quote": ""},
    ]
    for k, v in over.items():
        n, field = k.split("_", 1)
        items[int(n[1]) - 1][field] = v
    return items

def grade(resp):
    """Grade exactly the way the harness does: grader output, then padding to CHECKS."""
    if not isinstance(resp, str):
        resp = json.dumps(resp)
    results = gauntlet.pad(TASK.grade(resp, gauntlet.extract_code), TASK)
    return {name: ok for name, ok, _ in results}

def failed(scores):
    return sorted(name for name, ok in scores.items() if not ok)


class Fixtures(unittest.TestCase):
    def test_reference_quotes_are_in_policy(self):
        self.assertIn(Q1, TASK.POLICY)
        self.assertIn(Q2, TASK.POLICY)

    def test_prompt_embeds_full_policy(self):
        self.assertIn(TASK.POLICY, TASK.PROMPT)

    def test_task_contract(self):
        self.assertEqual(len(TASK.CHECKS), len(set(TASK.CHECKS)), "duplicate check names")
        self.assertEqual(TASK.OPTIONS["seed"], 42)


class Grading(unittest.TestCase):
    def test_perfect_answer_scores_full(self):
        s = grade(answers())
        self.assertEqual(failed(s), [])
        self.assertEqual(len(s), len(TASK.CHECKS))

    def test_grader_emits_only_declared_checks(self):
        for resp in (answers(), "garbage", {"answers": answers()}, [1, 2]):
            raw = json.dumps(resp) if not isinstance(resp, str) else resp
            names = [n for n, _, _ in TASK.grade(raw, gauntlet.extract_code)]
            self.assertEqual(len(names), len(set(names)))
            self.assertTrue(set(names) <= set(TASK.CHECKS), set(names) - set(TASK.CHECKS))

    def test_fenced_json_costs_only_the_format_point(self):
        s = grade("```json\n" + json.dumps(answers(), indent=2) + "\n```")
        self.assertEqual(failed(s), ["clean JSON output"])

    def test_prose_wrapper_costs_only_the_format_point(self):
        s = grade("Here are the answers:\n" + json.dumps(answers()) + "\nHope that helps!")
        self.assertEqual(failed(s), ["clean JSON output"])

    def test_unparseable_scores_zero_against_full_bar(self):
        s = grade("Sure! You have 14 days and free shipping over $50.")
        self.assertEqual(len(s), len(TASK.CHECKS))
        self.assertEqual(sum(s.values()), 0)

    def test_hallucinated_gift_wrap_fails_both_q3_checks(self):
        s = grade(answers(q3_answer="Yes, gift wrapping is available for $5.",
                          q3_quote="Gift wrapping is available at checkout for $5."))
        self.assertEqual(failed(s), ["q3 no invented quote", "q3 says NOT IN POLICY"])

    def test_null_quote_counts_as_empty(self):
        self.assertEqual(failed(grade(answers(q3_quote=None))), [])

    def test_not_in_policy_must_be_exact(self):
        s = grade(answers(q3_answer="Not mentioned in the policy."))
        self.assertEqual(failed(s), ["q3 says NOT IN POLICY"])

    def test_distractor_30_days_fails_q1(self):
        s = grade(answers(q1_answer="30 days.",
                          q1_quote="Full-price items may be returned within 30 days of delivery for a full refund."))
        self.assertEqual(failed(s), ["q1 quote verbatim", "q1 sale return = 14 days"])

    def test_distractor_canada_threshold_fails_q2(self):
        s = grade(answers(q2_answer="$100.",
                          q2_quote="Orders to Canada ship free when the order total is $100 or more."))
        self.assertEqual(failed(s), ["q2 US free shipping = $50", "q2 quote verbatim"])

    def test_numbers_must_match_whole(self):
        self.assertIn("q2 US free shipping = $50", failed(grade(answers(q2_answer="$500"))))
        self.assertIn("q1 sale return = 14 days", failed(grade(answers(q1_answer="114 days"))))

    def test_spelled_out_numbers_pass(self):
        self.assertEqual(failed(grade(answers(q1_answer="Fourteen days.", q2_answer="Fifty dollars."))), [])

    def test_over_refusal_is_penalised(self):
        s = grade(answers(q1_answer="NOT IN POLICY", q1_quote=""))
        self.assertEqual(failed(s), ["q1 quote verbatim", "q1 sale return = 14 days"])

    def test_paraphrased_quote_fails(self):
        s = grade(answers(q1_quote="Items bought on sale can be returned within 14 days of delivery."))
        self.assertEqual(failed(s), ["q1 quote verbatim"])

    def test_fragment_quote_fails(self):
        self.assertEqual(failed(grade(answers(q1_quote="within 14 days"))), ["q1 quote verbatim"])

    def test_quote_whitespace_and_quotation_marks_are_tolerated(self):
        s = grade(answers(q1_quote='"Sale items may be returned\n within  14 days of delivery"',
                          q2_quote="Orders to the United States ship free when the order total is $50 or more"))
        self.assertEqual(failed(s), [])

    def test_wrapped_object_loses_schema_point_only(self):
        self.assertEqual(failed(grade({"answers": answers()})), ["schema: 3 items, exact keys"])

    def test_extra_key_loses_schema_point_only(self):
        items = answers()
        items[0]["confidence"] = 0.9
        self.assertEqual(failed(grade(items)), ["schema: 3 items, exact keys"])

    def test_string_ids_lose_schema_point_only(self):
        items = answers()
        for o in items: o["id"] = str(o["id"])
        self.assertEqual(failed(grade(items)), ["schema: 3 items, exact keys"])

    def test_missing_item_fails_its_checks(self):
        s = grade(answers()[:2])
        self.assertEqual(failed(s), ["q3 says NOT IN POLICY", "schema: 3 items, exact keys"])


if __name__ == "__main__":
    unittest.main()
