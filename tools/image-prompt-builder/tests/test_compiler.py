import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from image_prompt_builder import SceneSpec, compile_scene, load_config

CFG = load_config()


class TestCompiler(unittest.TestCase):
    def compile(self, spec, **kw):
        return compile_scene(spec, CFG, **kw)

    # --- structure / always-on guards ---
    def test_base_guards_always_present(self):
        req = self.compile(SceneSpec(outfit="a linen dress"))
        for term in ("cartoon", "two women", "extra limb"):   # base + dup + anatomy
            self.assertIn(term, req.negative)
        self.assertIn("solo, a single woman", req.positive)
        self.assertTrue(req.positive.startswith("RAW photo, photorealistic,"))
        self.assertTrue(req.positive.endswith("natural skin texture."))

    def test_negative_is_deduped(self):
        req = self.compile(SceneSpec(writing=True))
        terms = [t.strip() for t in req.negative.split(",")]
        self.assertEqual(len(terms), len(set(terms)))

    def test_hair_leads_scene_body(self):
        req = self.compile(SceneSpec(hair="caramel-blonde waves", outfit="a robe"))
        i_hair = req.positive.index("caramel-blonde waves")
        i_outfit = req.positive.index("a robe")
        self.assertLess(i_hair, i_outfit)

    def test_subject_identity_slot_injected(self):
        req = self.compile(SceneSpec(outfit="a robe"), subject_identity="SUBJECT_ANCHOR")
        self.assertIn("SUBJECT_ANCHOR", req.positive)

    # --- engine dials ---
    def test_defaults(self):
        req = self.compile(SceneSpec(nude=True))
        self.assertEqual(req.cfg, 4.0)
        self.assertEqual(req.steps, 35)
        self.assertEqual((req.width, req.height), (896, 1152))

    def test_clothed_raises_cfg_and_adds_extra(self):
        req = self.compile(SceneSpec(clothed=True, outfit="a wool coat"))
        self.assertEqual(req.cfg, 5.0)
        self.assertIn("garments clearly worn", req.positive)

    def test_complex_pose_bumps_steps(self):
        req = self.compile(SceneSpec(nude=True, pose_complex=True))
        self.assertEqual(req.steps, 40)
        self.assertEqual(req.cfg, 4.5)

    def test_complex_pose_negates_overhead_angle(self):
        req = self.compile(SceneSpec(clothed=True, pose_complex=True, outfit="a robe"))
        self.assertIn("overhead shot", req.negative)
        self.assertIn("bird's eye view", req.negative)

    def test_clothed_wins_cfg_pose_owns_steps(self):
        # clothed complex pose: cfg from `clothed` (prio 5), steps from `complex_pose`.
        req = self.compile(SceneSpec(clothed=True, pose_complex=True, outfit="a gown"))
        self.assertEqual(req.cfg, 5.0)
        self.assertEqual(req.steps, 40)

    def test_landscape_orientation(self):
        req = self.compile(SceneSpec(outfit="x", orientation="landscape"))
        self.assertEqual((req.width, req.height), (1152, 896))

    # --- writing (fully SFW, filled) ---
    def test_writing_anchors_laptop_and_negates_pen(self):
        req = self.compile(SceneSpec(writing=True, setting="at her desk"))
        self.assertIn("MacBook", req.positive)
        self.assertIn("pen", req.negative)
        self.assertIn("handwriting", req.negative)

    # --- explicit-payload profiles: STRUCTURAL behavior only (content left blank) ---
    def test_partner_drops_solo_and_sets_qa(self):
        req = self.compile(SceneSpec(partner=True))
        self.assertNotIn("solo, a single woman", req.positive)   # solo guard inverted
        self.assertTrue(req.partner_qa)
        self.assertIn("partner", req.meta["applied_profiles"])
        self.assertEqual(req.cfg, 4.5)                           # pose cfg

    def test_rear_sets_rear_qa(self):
        req = self.compile(SceneSpec(rear=True))
        self.assertTrue(req.require_rear_qa)
        self.assertIn("rear", req.meta["applied_profiles"])

    def test_partner_feet_fix_pose_gated(self):
        upright = self.compile(SceneSpec(partner=True, rear=False, legs_up=False))
        self.assertIn("partner_feet_fix", upright.meta["applied_profiles"])
        rear = self.compile(SceneSpec(partner=True, rear=True))
        self.assertNotIn("partner_feet_fix", rear.meta["applied_profiles"])

    def test_negative_accepts_comma_string(self):
        # A row whose `negative` is a single comma-string (an ani.py-style paste) is split.
        from image_prompt_builder.profiles import _as_term_list
        self.assertEqual(_as_term_list("a, b ,c"), ["a", "b", "c"])
        self.assertEqual(_as_term_list(["a", "b"]), ["a", "b"])
        self.assertEqual(_as_term_list(""), [])

    # --- determinism ---
    def test_deterministic(self):
        spec = SceneSpec(hair="waves", outfit="a robe", setting="a warm room", clothed=True)
        self.assertEqual(self.compile(spec).positive, self.compile(spec).positive)

    # --- escalation feeds back into compile ---
    def test_clean_limbs_escalation_bumps_steps(self):
        base = self.compile(SceneSpec(nude=True))
        esc = self.compile(SceneSpec(nude=True).with_escalation("clean_limbs"))
        self.assertEqual(esc.steps, base.steps + 5)


if __name__ == "__main__":
    unittest.main()
