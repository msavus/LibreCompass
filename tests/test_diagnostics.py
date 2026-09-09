# -*- coding: utf-8 -*-
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at https://www.apache.org/licenses/LICENSE-2.0
"""Diagnose: Auswertung der Befunde und Berichtstext."""
import unittest

import context  # noqa: F401

from librecompass import i18n
from librecompass.office import diagnostics


def facts(**overrides):
    base = {
        "version": "1.5.0",
        "office": "LibreOffice 7.6",
        "bindings": {"Global": ([], 0), "TextDocument": ([], 0)},
        "job_registered": False,
        "job_events": [],
        "interceptor_here": False,
        "module": "writer",
    }
    base.update(overrides)
    return base


class ReportTest(unittest.TestCase):
    def tearDown(self):
        i18n.set_language("en")

    def test_everything_missing(self):
        report = diagnostics.build_report(facts())
        self.assertIn("MISSING", report)
        self.assertIn("Set up shortcuts", report)
        self.assertIn("Set up context menu", report)

    def test_everything_present(self):
        report = diagnostics.build_report(facts(
            bindings={"Global": (["Ctrl+Shift+Alt+C"], 1),
                      "TextDocument": (["Ctrl+Shift+Alt+I"], 1)},
            job_registered=True,
            job_events=["onFirstVisibleTask"],
            job_ran="2026-08-02 09:00:00",
            context_modules=["TextDocument", "SpreadsheetDocument"],
            interceptor_here=True))
        self.assertNotIn("MISSING", report)
        self.assertNotIn("What to do:", report)
        self.assertIn("Ctrl+Shift+Alt+C", report)
        self.assertIn("onFirstVisibleTask", report)

    def test_persistent_menu_present_needs_no_hint(self):
        report = diagnostics.build_report(facts(
            context_modules=["TextDocument"], interceptor_here=False))
        self.assertNotIn("Set up context menu", report)
        self.assertIn("TextDocument", report)

    def test_registration_error_is_shown(self):
        report = diagnostics.build_report(facts(
            interceptor_error="registerContextMenuInterceptor: boom"))
        self.assertIn("boom", report)

    def test_startup_job_state_is_reported(self):
        report = diagnostics.build_report(facts(
            job_registered=True, job_events=["onFirstVisibleTask"],
            job_ran=None))
        self.assertIn("Startup job actually ran:", report)

    def test_unreadable_bindings_are_named_as_such(self):
        report = diagnostics.build_report(facts(bindings={}))
        self.assertIn("could not be read", report)

    def test_shortcuts_present_context_menu_missing(self):
        report = diagnostics.build_report(facts(
            bindings={"Global": (["Ctrl+Shift+Alt+C"], 1)}))
        self.assertIn("Set up context menu", report)
        self.assertNotIn("Set up shortcuts", report)

    def test_report_is_translated(self):
        i18n.set_language("de")
        report = diagnostics.build_report(facts())
        self.assertIn("FEHLT", report)
        self.assertIn("Tastenkürzel", report)

    def test_version_and_office_are_shown(self):
        report = diagnostics.build_report(facts())
        self.assertIn("1.5.0", report)
        self.assertIn("LibreOffice 7.6", report)


class KeyScanTest(unittest.TestCase):
    class _Node(object):
        def __init__(self, entries):
            self.entries = entries

        def getElementNames(self):
            return tuple(self.entries)

        def getByName(self, name):
            value = self.entries[name]
            if isinstance(value, str):
                return KeyScanTest._Command(value)
            raise KeyError(name)

    class _Command(object):
        def __init__(self, command):
            self.command = command

        def getByName(self, name):
            if name == "Command":
                return self.command
            raise KeyError(name)

    def test_only_our_commands_are_reported(self):
        node = self._Node({"I_SHIFT_MOD1_MOD2": "service:org.librecompass.Main?improve",
                           "A_MOD1": ".uno:SelectAll"})
        self.assertEqual(diagnostics._keys_with_our_commands(node),
                         ["I_SHIFT_MOD1_MOD2"])

    def test_missing_node(self):
        self.assertEqual(diagnostics._keys_with_our_commands(None), [])

    def test_unreadable_entries_are_skipped(self):
        class Broken(object):
            def getElementNames(self):
                return ("X",)

            def getByName(self, name):
                raise RuntimeError("no")

        self.assertEqual(diagnostics._keys_with_our_commands(Broken()), [])


if __name__ == "__main__":
    unittest.main()
