# -*- coding: utf-8 -*-
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at https://www.apache.org/licenses/LICENSE-2.0
import json
import os
import shutil
import tempfile
import unittest

import context  # noqa: F401
from fakes import FakeContext

from librecompass.config.settings import DEFAULTS, Settings


class SettingsTest(unittest.TestCase):
    def setUp(self):
        self.profile = tempfile.mkdtemp(prefix="librecompass-profile-")
        self.ctx = FakeContext(profile_dir=self.profile)

    def tearDown(self):
        shutil.rmtree(self.profile, ignore_errors=True)

    def test_creates_file_with_defaults(self):
        settings = Settings.load(self.ctx)
        path = os.path.join(settings.directory, "settings.json")
        self.assertTrue(os.path.exists(path))
        self.assertEqual(settings.model, DEFAULTS["model"])
        self.assertEqual(settings.language, "auto")

    def test_directory_is_inside_profile(self):
        settings = Settings.load(self.ctx)
        self.assertTrue(settings.directory.startswith(self.profile))
        self.assertTrue(settings.directory.endswith("librecompass"))

    def test_roundtrip(self):
        settings = Settings.load(self.ctx)
        settings.data["model"] = "custom-model"
        settings.save()
        again = Settings.load(self.ctx)
        self.assertEqual(again.model, "custom-model")

    def test_missing_keys_get_defaults(self):
        settings = Settings.load(self.ctx)
        with open(os.path.join(settings.directory, "settings.json"),
                  "w", encoding="utf-8") as handle:
            json.dump({"model": "only"}, handle)
        again = Settings.load(self.ctx)
        self.assertEqual(again.model, "only")
        self.assertEqual(again.rag_top_k, DEFAULTS["rag_top_k"])

    def test_corrupt_file_falls_back_to_defaults(self):
        settings = Settings.load(self.ctx)
        with open(os.path.join(settings.directory, "settings.json"),
                  "w", encoding="utf-8") as handle:
            handle.write("broken")
        again = Settings.load(self.ctx)
        self.assertEqual(again.model, DEFAULTS["model"])

    def test_derived_paths(self):
        settings = Settings.load(self.ctx)
        self.assertTrue(settings.prompts_path().endswith("prompts.json"))
        self.assertTrue(settings.knowledge_path().endswith("knowledge.json"))
        self.assertTrue(os.path.isdir(settings.plugins_dir()))

    def test_unknown_attribute_raises(self):
        settings = Settings.load(self.ctx)
        with self.assertRaises(AttributeError):
            settings.does_not_exist


if __name__ == "__main__":
    unittest.main()
