# -*- coding: utf-8 -*-
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at https://www.apache.org/licenses/LICENSE-2.0
"""Dauerhafte Kontextmenü-Einträge in der Modulkonfiguration."""
import unittest

import context  # noqa: F401
from fakes import (FakeItemContainer, FakeProperty,
                   FakeUIConfigurationManager)

from librecompass import i18n
from librecompass.office import context_config

WRITER = "com.sun.star.text.TextDocument"
TEXT_MENU = "private:resource/popupmenu/text"


class EntryTest(unittest.TestCase):
    def tearDown(self):
        i18n.set_language("en")

    def test_entries_carry_service_urls(self):
        commands = [command for _l, command in context_config.entry_labels()
                    if command]
        self.assertIn("service:org.librecompass.Main?improve", commands)
        self.assertTrue(all(url.startswith("service:") for url in commands))

    def test_entries_follow_language(self):
        i18n.set_language("de")
        labels = [label for label, _c in context_config.entry_labels()
                  if label]
        self.assertIn("Auswahl verbessern", labels)

    def test_entries_contain_a_separator(self):
        self.assertIn((None, None), context_config.entry_labels())


class RecognitionTest(unittest.TestCase):
    def test_recognizes_own_command(self):
        item = (FakeProperty("CommandURL",
                             "service:org.librecompass.Main?improve"),)
        self.assertTrue(context_config.is_ours(item))

    def test_recognizes_own_root_by_label(self):
        item = (FakeProperty("Label", "LibreCompass"),
                FakeProperty("CommandURL", ""))
        self.assertTrue(context_config.is_ours(item))

    def test_ignores_foreign_entries(self):
        item = (FakeProperty("CommandURL", ".uno:Paste"),
                FakeProperty("Label", "Paste"))
        self.assertFalse(context_config.is_ours(item))

    def test_empty_entry(self):
        self.assertFalse(context_config.is_ours(()))
        self.assertFalse(context_config.is_ours(None))

    def test_find_entries_returns_descending_indices(self):
        settings = FakeItemContainer([
            (FakeProperty("CommandURL", ".uno:Cut"),),
            (FakeProperty("CommandURL",
                          "service:org.librecompass.Main?panel"),),
            (FakeProperty("CommandURL", ".uno:Paste"),),
            (FakeProperty("Label", "LibreCompass"),),
        ])
        self.assertEqual(context_config.find_entries(settings), [3, 1])


class InstallTest(unittest.TestCase):
    def setUp(self):
        self.manager = FakeUIConfigurationManager([TEXT_MENU])
        self.original = context_config._managers
        context_config._managers = lambda ctx: [
            (WRITER, self.manager, (TEXT_MENU,))]

    def tearDown(self):
        context_config._managers = self.original

    def test_install_adds_separator_and_root(self):
        changed, errors = context_config.install(None)
        self.assertEqual(changed, 1)
        self.assertEqual(errors, [])
        settings = self.manager.settings[TEXT_MENU]
        self.assertEqual(settings.getCount(), 2)
        self.assertEqual(self.manager.stored, 1)

    def test_installed_root_carries_a_submenu(self):
        context_config.install(None)
        settings = self.manager.settings[TEXT_MENU]
        root = settings.getByIndex(settings.getCount() - 1)
        names = {entry.Name: entry.Value for entry in root}
        self.assertEqual(names["Label"], "LibreCompass")
        submenu = names["ItemDescriptorContainer"]
        self.assertEqual(submenu.getCount(), len(context_config.ENTRIES))

    def test_install_is_idempotent(self):
        context_config.install(None)
        context_config.install(None)
        settings = self.manager.settings[TEXT_MENU]
        self.assertEqual(settings.getCount(), 2)

    def test_install_keeps_existing_entries(self):
        settings = self.manager.settings[TEXT_MENU]
        settings.insertByIndex(0, (FakeProperty("CommandURL", ".uno:Paste"),))
        context_config.install(None)
        self.assertEqual(settings.getByIndex(0)[0].Value, ".uno:Paste")

    def test_installed_modules(self):
        self.assertEqual(context_config.installed_modules(None), [])
        context_config.install(None)
        self.assertEqual(context_config.installed_modules(None),
                         ["TextDocument"])

    def test_remove(self):
        context_config.install(None)
        removed = context_config.remove(None)
        self.assertEqual(removed, 2)
        self.assertEqual(self.manager.settings[TEXT_MENU].getCount(), 0)
        self.assertEqual(context_config.installed_modules(None), [])

    def test_remove_leaves_foreign_entries(self):
        settings = self.manager.settings[TEXT_MENU]
        settings.insertByIndex(0, (FakeProperty("CommandURL", ".uno:Paste"),))
        context_config.install(None)
        context_config.remove(None)
        self.assertEqual(settings.getCount(), 1)
        self.assertEqual(settings.getByIndex(0)[0].Value, ".uno:Paste")

    def test_unknown_resource_is_skipped(self):
        context_config._managers = lambda ctx: [
            (WRITER, self.manager, ("private:resource/popupmenu/nope",))]
        changed, errors = context_config.install(None)
        self.assertEqual(changed, 0)
        self.assertEqual(errors, [])

    def test_readonly_configuration_is_reported(self):
        self.manager.readonly = True
        changed, errors = context_config.install(None)
        self.assertEqual(changed, 0)
        self.assertTrue(errors)

    def test_summary_mentions_errors(self):
        text = context_config.summary(0, ["Writer text: read-only"])
        self.assertIn("read-only", text)


if __name__ == "__main__":
    unittest.main()
