# -*- coding: utf-8 -*-
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at https://www.apache.org/licenses/LICENSE-2.0
import unittest

import context  # noqa: F401
from helpers import TempSettings

from librecompass import i18n
from librecompass.ai import prompts


class PromptTest(unittest.TestCase):
    def setUp(self):
        self.settings = TempSettings()

    def tearDown(self):
        self.settings.cleanup()
        i18n.set_language("en")

    def test_build_prompt_contains_text_block(self):
        prompt = prompts.build_prompt("Do it.", "content")
        self.assertIn("Do it.", prompt)
        self.assertIn("TEXT:", prompt)
        self.assertIn("content", prompt)

    def test_rules_follow_language(self):
        i18n.set_language("en")
        self.assertIn("Return the result only",
                      prompts.build_prompt("x", "y"))
        i18n.set_language("de")
        self.assertIn("ausschließlich", prompts.build_prompt("x", "y"))

    def test_instruction_translation(self):
        i18n.set_language("de")
        self.assertIn("Verbessere", prompts.instruction("improve"))
        i18n.set_language("en")
        self.assertIn("Improve", prompts.instruction("improve"))

    def test_instruction_formatting(self):
        i18n.set_language("en")
        self.assertIn("Dutch",
                      prompts.instruction("translate", language="Dutch"))

    def test_default_library_language(self):
        i18n.set_language("de")
        names = [entry["name"] for entry in prompts.default_library()]
        self.assertIn("Verbessern", names)
        i18n.set_language("en")
        names = [entry["name"] for entry in prompts.default_library()]
        self.assertIn("Improve", names)

    def test_library_is_created_and_saved(self):
        library = prompts.load_library(self.settings)
        self.assertTrue(library)
        prompts.save_to_library(self.settings, "Mine", "Do something.")
        names = [entry["name"] for entry in
                 prompts.load_library(self.settings)]
        self.assertIn("Mine", names)

    def test_saving_replaces_same_name(self):
        prompts.save_to_library(self.settings, "Mine", "one")
        prompts.save_to_library(self.settings, "Mine", "two")
        matches = [entry for entry in prompts.load_library(self.settings)
                   if entry["name"] == "Mine"]
        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0]["prompt"], "two")

    def test_rag_messages(self):
        messages = prompts.build_rag_messages("Question?", "Excerpt")
        self.assertEqual(messages[0]["role"], "system")
        self.assertIn("Excerpt", messages[0]["content"])
        self.assertEqual(messages[-1]["content"], "Question?")


if __name__ == "__main__":
    unittest.main()
