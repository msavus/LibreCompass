# -*- coding: utf-8 -*-
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at https://www.apache.org/licenses/LICENSE-2.0
import os
import unittest

import context  # noqa: F401
from fakes import FakeClient, FakeContext, FakeWriterDocument
from helpers import TempSettings, write_file

from librecompass import plugins
from librecompass.office.document import OfficeDocument

PROMPT_PLUGIN = '''NAME = "Bullets"
DESCRIPTION = "Turns text into bullets"
PROMPT = "Rewrite as bullet list."
'''

RUN_PLUGIN = '''NAME = "Counter"

def run(api):
    api.message("words: %d" % len(api.selection().split()))
'''

BROKEN_PLUGIN = "this is not valid python ("

EMPTY_PLUGIN = 'NAME = "Nothing"\n'

FAILING_PLUGIN = '''NAME = "Boom"

def run(api):
    raise RuntimeError("failed inside plugin")
'''


class PluginTest(unittest.TestCase):
    def setUp(self):
        self.settings = TempSettings()
        self.directory = self.settings.plugins_dir()

    def tearDown(self):
        self.settings.cleanup()

    def test_no_plugins(self):
        self.assertEqual(plugins.discover(self.settings), [])

    def test_prompt_plugin(self):
        write_file(self.directory, "bullets.py", PROMPT_PLUGIN)
        found = plugins.discover(self.settings)
        self.assertEqual(len(found), 1)
        self.assertEqual(found[0].name, "Bullets")
        self.assertTrue(found[0].has_prompt)
        self.assertFalse(found[0].is_runnable)
        self.assertIn("Turns text", found[0].label())

    def test_runnable_plugin(self):
        write_file(self.directory, "counter.py", RUN_PLUGIN)
        found = plugins.discover(self.settings)
        self.assertTrue(found[0].is_runnable)

    def test_broken_plugin_is_skipped(self):
        write_file(self.directory, "broken.py", BROKEN_PLUGIN)
        write_file(self.directory, "bullets.py", PROMPT_PLUGIN)
        found = plugins.discover(self.settings)
        self.assertEqual([item.name for item in found], ["Bullets"])

    def test_plugin_without_prompt_or_run_is_skipped(self):
        write_file(self.directory, "empty.py", EMPTY_PLUGIN)
        self.assertEqual(plugins.discover(self.settings), [])

    def test_underscore_files_are_ignored(self):
        write_file(self.directory, "_helper.py", PROMPT_PLUGIN)
        self.assertEqual(plugins.discover(self.settings), [])

    def test_running_plugin_uses_api(self):
        write_file(self.directory, "counter.py", RUN_PLUGIN)
        plugin = plugins.discover(self.settings)[0]
        document = FakeWriterDocument(selection_texts=("one two three",))
        ctx = FakeContext(component=document)
        messages = []
        api = plugins.PluginAPI(
            ctx, OfficeDocument(ctx), FakeClient(), self.settings,
            lambda text, title=None: messages.append(text))
        self.assertIsNone(plugins.run_plugin(plugin, api))
        self.assertEqual(messages, ["words: 3"])

    def test_failing_plugin_returns_traceback(self):
        write_file(self.directory, "boom.py", FAILING_PLUGIN)
        plugin = plugins.discover(self.settings)[0]
        ctx = FakeContext(component=FakeWriterDocument())
        api = plugins.PluginAPI(ctx, OfficeDocument(ctx), FakeClient(),
                               self.settings, lambda text, title=None: None)
        failure = plugins.run_plugin(plugin, api)
        self.assertIn("failed inside plugin", failure)

    def test_api_write_paths(self):
        document = FakeWriterDocument(selection_texts=("old",))
        ctx = FakeContext(component=document)
        api = plugins.PluginAPI(ctx, OfficeDocument(ctx), FakeClient(),
                               self.settings, lambda text, title=None: None)
        self.assertTrue(api.replace_selection("new"))
        self.assertEqual(document.selection.getByIndex(0).getString(), "new")
        self.assertEqual(api.module(), "writer")
        self.assertEqual(api.ask("prompt"), "ANSWER")

    def test_plugins_dir_exists(self):
        self.assertTrue(os.path.isdir(self.directory))


if __name__ == "__main__":
    unittest.main()
