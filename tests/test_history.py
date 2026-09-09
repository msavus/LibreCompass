# -*- coding: utf-8 -*-
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at https://www.apache.org/licenses/LICENSE-2.0
import unittest

import context  # noqa: F401
from helpers import TempSettings

from librecompass.ai import history


class HistoryTest(unittest.TestCase):
    def setUp(self):
        self.settings = TempSettings()

    def tearDown(self):
        self.settings.cleanup()

    def test_empty_history(self):
        self.assertEqual(history.load(self.settings), [])

    def test_add_and_load(self):
        history.add(self.settings, "Prompt", "p", "a", "qwen3")
        entries = history.load(self.settings)
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0]["response"], "a")
        self.assertEqual(entries[0]["model"], "qwen3")

    def test_trims_to_maximum(self):
        for number in range(history.MAX_ENTRIES + 20):
            history.add(self.settings, "Prompt", str(number), "a", "m")
        entries = history.load(self.settings)
        self.assertEqual(len(entries), history.MAX_ENTRIES)
        self.assertEqual(entries[-1]["prompt"],
                         str(history.MAX_ENTRIES + 19))

    def test_label_is_shortened(self):
        entry = {"time": "2026-07-30 08:00", "kind": "Prompt",
                 "prompt": "word " * 40}
        label = history.label(entry)
        self.assertTrue(label.endswith("…"))
        self.assertLess(len(label), 100)

    def test_corrupt_file_is_ignored(self):
        with open(self.settings.directory + "/history.json", "w") as handle:
            handle.write("{not json")
        self.assertEqual(history.load(self.settings), [])


if __name__ == "__main__":
    unittest.main()
