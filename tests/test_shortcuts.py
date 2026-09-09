# -*- coding: utf-8 -*-
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at https://www.apache.org/licenses/LICENSE-2.0
"""Tastenkürzel: Tastencodes, Konflikterkennung, Setzen und Entfernen."""
import unittest

import context  # noqa: F401

from librecompass import i18n
from librecompass.office import shortcuts


class KeyTest(unittest.TestCase):
    def test_key_codes(self):
        self.assertEqual(shortcuts.key_code("A"), 512)
        self.assertEqual(shortcuts.key_code("z"), 512 + 25)
        self.assertEqual(shortcuts.key_code("I"), 512 + 8)

    def test_invalid_key(self):
        for value in ("", "AB", "1", "ä", None):
            with self.assertRaises(ValueError):
                shortcuts.key_code(value)

    def test_modifier_mask(self):
        self.assertEqual(shortcuts.modifier_mask("shift", "mod1", "mod2"), 7)
        self.assertEqual(shortcuts.modifier_mask("mod1"), 2)

    def test_describe(self):
        self.assertEqual(shortcuts.describe("I", 7), "Ctrl+Shift+Alt+I")
        self.assertEqual(shortcuts.describe("a", 2), "Ctrl+A")

    def test_command_urls(self):
        self.assertEqual(shortcuts.command_url("improve"),
                         "service:org.librecompass.Main?improve")

    def test_all_shortcuts_use_three_modifiers(self):
        for _letter, modifiers, _key, _g in shortcuts.SHORTCUTS:
            self.assertEqual(modifiers, 7)

    def test_letters_are_unique(self):
        letters = [letter for letter, _m, _k, _g in shortcuts.SHORTCUTS]
        self.assertEqual(len(letters), len(set(letters)))


class PlanTest(unittest.TestCase):
    def test_all_free(self):
        existing = {(letter, modifiers): None
                    for letter, modifiers, _k, _g in shortcuts.SHORTCUTS}
        to_set, conflicts = shortcuts.plan(existing)
        self.assertEqual(len(to_set), len(shortcuts.SHORTCUTS))
        self.assertEqual(conflicts, [])

    def test_foreign_binding_is_a_conflict(self):
        existing = {(letter, modifiers): None
                    for letter, modifiers, _k, _g in shortcuts.SHORTCUTS}
        existing[("I", 7)] = ".uno:Something"
        to_set, conflicts = shortcuts.plan(existing)
        self.assertEqual(len(to_set), len(shortcuts.SHORTCUTS) - 1)
        self.assertEqual(conflicts, [("Ctrl+Shift+Alt+I", ".uno:Something")])

    def test_own_binding_is_refreshed_not_a_conflict(self):
        existing = {(letter, modifiers): None
                    for letter, modifiers, _k, _g in shortcuts.SHORTCUTS}
        existing[("I", 7)] = "service:org.librecompass.Main?improve"
        to_set, conflicts = shortcuts.plan(existing)
        self.assertEqual(conflicts, [])
        self.assertEqual(len(to_set), len(shortcuts.SHORTCUTS))

    def test_global_scope_only_takes_global_entries(self):
        existing = {("C", 7): None}
        to_set, _conflicts = shortcuts.plan(existing, only_global=True)
        self.assertEqual(len(to_set), 1)
        self.assertTrue(to_set[0][2].endswith("?panel"))


class FakeAccelerators(object):
    """Ersatz für XAcceleratorConfiguration."""

    def __init__(self, bindings=None):
        self.bindings = dict(bindings or {})
        self.stored = 0

    def _key(self, event):
        return (event.KeyCode, event.Modifiers)

    def getCommandByKeyEvent(self, event):
        key = self._key(event)
        if key not in self.bindings:
            raise RuntimeError("NoSuchElement")
        return self.bindings[key]

    def setKeyEvent(self, event, command):
        self.bindings[self._key(event)] = command

    def removeKeyEvent(self, event):
        del self.bindings[self._key(event)]

    def store(self):
        self.stored += 1


class ApplyTest(unittest.TestCase):
    def setUp(self):
        self.global_config = FakeAccelerators()
        self.writer_config = FakeAccelerators()
        self.original = shortcuts._configurations
        shortcuts._configurations = lambda ctx: [
            ("Global", self.global_config),
            ("com.sun.star.text.TextDocument", self.writer_config)]

    def tearDown(self):
        shortcuts._configurations = self.original
        i18n.set_language("en")

    def test_apply_sets_and_stores(self):
        applied, conflicts, errors = shortcuts.apply(None)
        # global: nur der Panel-Eintrag, Writer: alle
        self.assertEqual(applied, 1 + len(shortcuts.SHORTCUTS))
        self.assertEqual(conflicts, [])
        self.assertEqual(errors, [])
        self.assertEqual(self.global_config.stored, 1)
        self.assertEqual(len(self.global_config.bindings), 1)
        self.assertEqual(len(self.writer_config.bindings),
                         len(shortcuts.SHORTCUTS))

    def test_apply_skips_foreign_bindings(self):
        self.writer_config.bindings[(shortcuts.key_code("I"), 7)] = \
            ".uno:Foreign"
        applied, conflicts, _errors = shortcuts.apply(None)
        self.assertEqual(applied, 1 + len(shortcuts.SHORTCUTS) - 1)
        self.assertEqual(conflicts, [("Ctrl+Shift+Alt+I", ".uno:Foreign")])
        self.assertEqual(
            self.writer_config.bindings[(shortcuts.key_code("I"), 7)],
            ".uno:Foreign")

    def test_apply_is_idempotent(self):
        shortcuts.apply(None)
        before = dict(self.writer_config.bindings)
        shortcuts.apply(None)
        self.assertEqual(self.writer_config.bindings, before)

    def test_installed_count(self):
        self.assertEqual(shortcuts.installed_count(None), 0)
        shortcuts.apply(None)
        self.assertEqual(shortcuts.installed_count(None),
                         1 + len(shortcuts.SHORTCUTS))

    def test_remove_only_removes_ours(self):
        self.writer_config.bindings[(shortcuts.key_code("I"), 7)] = \
            ".uno:Foreign"
        shortcuts.apply(None)
        removed = shortcuts.remove(None)
        self.assertEqual(removed, 1 + len(shortcuts.SHORTCUTS) - 1)
        self.assertEqual(
            self.writer_config.bindings[(shortcuts.key_code("I"), 7)],
            ".uno:Foreign")

    def test_errors_are_reported(self):
        class Failing(FakeAccelerators):
            def setKeyEvent(self, event, command):
                raise RuntimeError("read-only")

        shortcuts._configurations = lambda ctx: [("Global", Failing())]
        applied, _conflicts, errors = shortcuts.apply(None)
        self.assertEqual(applied, 0)
        self.assertTrue(errors)

    def test_summary_text(self):
        text = shortcuts.summary(3, [("Ctrl+Shift+Alt+I", ".uno:X")], [])
        self.assertIn("3", text)
        self.assertIn(".uno:X", text)


if __name__ == "__main__":
    unittest.main()
