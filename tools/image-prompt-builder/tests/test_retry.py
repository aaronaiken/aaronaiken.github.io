import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from image_prompt_builder import SceneSpec, plan_retry


class TestRetry(unittest.TestCase):
    def plan(self, verdict, spec=None, attempt=1, max_attempts=4):
        return plan_retry(spec or SceneSpec(), verdict, attempt=attempt, max_attempts=max_attempts)

    def test_pass_no_retry(self):
        p = self.plan({"ok": True})
        self.assertFalse(p.should_retry)
        self.assertEqual(p.note, "passed")

    def test_budget_exhausted_no_retry(self):
        p = self.plan({"ok": False, "defect": "feet_glitch"}, attempt=4, max_attempts=4)
        self.assertFalse(p.should_retry)
        self.assertEqual(p.note, "budget-exhausted")

    def test_not_rear_escalates_via_recompile(self):
        p = self.plan({"ok": False, "defect": "not_rear"}, spec=SceneSpec(rear=True))
        self.assertTrue(p.should_retry)
        self.assertTrue(p.recompile)
        self.assertEqual(p.spec.escalations, {"rear_boost": 1})

    def test_feet_glitch_recompiles_with_feet_fix(self):
        p = self.plan({"ok": False, "defect": "feet_glitch"}, spec=SceneSpec(partner=True))
        self.assertTrue(p.recompile)
        self.assertEqual(p.spec.escalations, {"feet_fix": 1})

    def test_duplicate_merges_negative_no_recompile(self):
        p = self.plan({"ok": False, "defect": "duplicate"})
        self.assertTrue(p.should_retry)
        self.assertFalse(p.recompile)
        self.assertIn("second body", p.add_negative)
        self.assertGreater(p.cfg_delta, 0)

    def test_broken_limb_raises_steps(self):
        p = self.plan({"ok": False, "defect": "broken_limb"})
        self.assertTrue(p.recompile)
        self.assertEqual(p.spec.escalations, {"clean_limbs": 1})

    def test_backwards_head_suppresses_owl_neck(self):
        p = self.plan({"ok": False, "defect": "backwards_head"})
        self.assertFalse(p.recompile)
        self.assertTrue(any("neck" in t for t in p.add_negative))

    def test_unknown_defect_plain_reroll(self):
        p = self.plan({"ok": False, "defect": "weird"})
        self.assertTrue(p.should_retry)
        self.assertFalse(p.recompile)
        self.assertEqual(p.note, "plain re-roll")


if __name__ == "__main__":
    unittest.main()
