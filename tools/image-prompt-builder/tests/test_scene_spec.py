import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from image_prompt_builder import SceneSpec


class TestSceneSpec(unittest.TestCase):
    def test_from_extractor_fills_fields_and_flags(self):
        spec = SceneSpec.from_extractor({
            "hair": "  caramel-blonde waves ",
            "outfit": "cream sweater",
            "pose_complex": True,
            "clothed": True,
            "orientation": "landscape",
            "junk_key": "ignored",
        })
        self.assertEqual(spec.hair, "caramel-blonde waves")   # trimmed
        self.assertEqual(spec.outfit, "cream sweater")
        self.assertTrue(spec.pose_complex)
        self.assertTrue(spec.clothed)
        self.assertFalse(spec.partner)                        # default
        self.assertEqual(spec.orientation, "landscape")

    def test_bad_orientation_falls_back(self):
        self.assertEqual(SceneSpec(orientation="sideways").orientation, "portrait")

    def test_matches_when_clause(self):
        spec = SceneSpec(partner=True, rear=False)
        self.assertTrue(spec.matches({}))                     # empty = always
        self.assertTrue(spec.matches({"partner": True}))
        self.assertTrue(spec.matches({"partner": True, "rear": False}))
        self.assertFalse(spec.matches({"partner": True, "rear": True}))

    def test_with_escalation_is_immutable_and_cumulative(self):
        base = SceneSpec(rear=True)
        once = base.with_escalation("rear_boost")
        twice = once.with_escalation("rear_boost")
        self.assertEqual(base.escalations, {})                # original untouched
        self.assertEqual(once.escalations, {"rear_boost": 1})
        self.assertEqual(twice.escalations, {"rear_boost": 2})


if __name__ == "__main__":
    unittest.main()
