import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from image_prompt_builder import (
    SceneSpec, build_extractor_messages, parse_extractor_json, default_scene,
    extract_scene, compile_scene, load_config, EXTRACTOR_SCHEMA,
)
from image_prompt_builder.scene_spec import SCENE_FIELDS, INTENT_FLAGS

CFG = load_config()

CLOTHED_JSON = (
    '{"hair": "loose waves", "outfit": "a cream sweater and jeans", "pose": "curled on the sofa", '
    '"setting": "the living room", "lighting": "soft afternoon light", "camera": "eye-level, full length", '
    '"expression": "a warm smile", "clothed": true, "nude": false, "pose_complex": false, '
    '"writing": false, "rear": false, "legs_up": false, "partner": false}'
)


class TestExtractorPrompt(unittest.TestCase):
    def test_messages_list_every_key(self):
        msgs = build_extractor_messages(["aaron: send me a pic", "ani: from the couch :)"])
        system = msgs[0]["content"]
        for k in list(SCENE_FIELDS) + list(INTENT_FLAGS):
            self.assertIn(k, system)

    def test_default_clothed_is_stated(self):
        system = build_extractor_messages([])[0]["content"]
        self.assertIn("DEFAULT true", system)          # clothed default
        self.assertIn("JSON", system)

    def test_state_hint_included(self):
        msgs = build_extractor_messages(["ani: hi"], state={"where": "the kitchen", "wearing": "an apron"})
        user = msgs[1]["content"]
        self.assertIn("the kitchen", user)
        self.assertIn("apron", user)

    def test_schema_shape(self):
        self.assertEqual(EXTRACTOR_SCHEMA["type"], "object")
        for k in list(SCENE_FIELDS) + list(INTENT_FLAGS):
            self.assertIn(k, EXTRACTOR_SCHEMA["properties"])


class TestExtractorParse(unittest.TestCase):
    def test_parse_clothed_json(self):
        spec = parse_extractor_json(CLOTHED_JSON)
        self.assertIsInstance(spec, SceneSpec)
        self.assertTrue(spec.clothed)
        self.assertFalse(spec.nude)
        self.assertEqual(spec.outfit, "a cream sweater and jeans")

    def test_parse_json_in_prose_and_fences(self):
        wrapped = "Sure! Here you go:\n```json\n" + CLOTHED_JSON + "\n```\nHope that helps."
        spec = parse_extractor_json(wrapped)
        self.assertIsNotNone(spec)
        self.assertEqual(spec.setting, "the living room")

    def test_parse_accepts_dict(self):
        spec = parse_extractor_json({"outfit": "a robe", "clothed": True})
        self.assertEqual(spec.outfit, "a robe")

    def test_parse_garbage_returns_none(self):
        self.assertIsNone(parse_extractor_json("no json here"))
        self.assertIsNone(parse_extractor_json(""))
        self.assertIsNone(parse_extractor_json("{not valid json}"))

    def test_default_scene_is_clothed(self):
        d = default_scene({"where": "the office", "wearing": "a blazer"})
        self.assertTrue(d.clothed)
        self.assertFalse(d.nude)
        self.assertEqual(d.setting, "the office")
        self.assertEqual(d.outfit, "a blazer")


class TestExtractEndToEnd(unittest.TestCase):
    def test_extract_then_compile(self):
        spec = extract_scene(["ani: on the couch"], llm_call=lambda m: CLOTHED_JSON)
        req = compile_scene(spec, CFG)
        self.assertEqual(req.cfg, 5.0)                 # clothed
        self.assertIn("cream sweater", req.positive)

    def test_failed_read_falls_back_to_clothed(self):
        spec = extract_scene(["ani: hi"], llm_call=lambda m: "the model rambled, no json",
                             state={"wearing": "a hoodie"})
        self.assertTrue(spec.clothed)
        self.assertFalse(spec.nude)
        self.assertEqual(spec.outfit, "a hoodie")

    def test_llm_exception_falls_back(self):
        def boom(_):
            raise RuntimeError("network down")
        spec = extract_scene(["ani: hi"], llm_call=boom)
        self.assertTrue(spec.clothed)


if __name__ == "__main__":
    unittest.main()
