# -*- coding: utf-8 -*-
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at https://www.apache.org/licenses/LICENSE-2.0
"""Hintergrundausführung: Sperre, Ergebnisweitergabe, Fehlerpfad."""
import unittest

import context  # noqa: F401
from fakes import FakeContext, FakeStatusIndicator

from librecompass import async_task


class _Direct(object):
    """Führt den Worker sofort aus - macht den Ablauf deterministisch."""

    def __init__(self):
        self.started = 0

    def __call__(self, worker):
        self.started += 1
        worker()


class AsyncTaskTest(unittest.TestCase):
    def setUp(self):
        async_task._release()
        self.ctx = FakeContext()
        self.spawn = _Direct()

    def tearDown(self):
        async_task._release()

    def _run(self, work, done, indicator=None, label=""):
        return async_task.run(self.ctx, work, done, indicator=indicator,
                              label=label, spawn=self.spawn)

    def test_result_is_passed_through(self):
        seen = []
        self.assertTrue(self._run(lambda: "ANSWER",
                                  lambda r, e: seen.append((r, e))))
        self.assertEqual(seen, [("ANSWER", None)])

    def test_exception_becomes_error_argument(self):
        seen = []

        def work():
            raise RuntimeError("model down")

        self._run(work, lambda r, e: seen.append((r, e)))
        result, error = seen[0]
        self.assertIsNone(result)
        self.assertIn("model down", str(error))

    def test_silent_exception_still_reports_something(self):
        seen = []

        def work():
            raise RuntimeError()

        self._run(work, lambda r, e: seen.append((r, e)))
        self.assertTrue(str(seen[0][1]))

    def test_indicator_is_ended(self):
        indicator = FakeStatusIndicator()
        self._run(lambda: "x", lambda r, e: None, indicator=indicator)
        self.assertEqual(indicator.ended, 1)

    def test_indicator_is_ended_on_error(self):
        indicator = FakeStatusIndicator()

        def work():
            raise RuntimeError("boom")

        self._run(work, lambda r, e: None, indicator=indicator)
        self.assertEqual(indicator.ended, 1)

    def test_second_task_is_refused_while_running(self):
        outcome = []

        def work():
            # Während der Ausführung ist die Sperre gesetzt
            outcome.append(async_task.is_busy())
            outcome.append(self._run(lambda: "second",
                                     lambda r, e: outcome.append("ran")))
            return "first"

        self._run(work, lambda r, e: None)
        self.assertEqual(outcome[0], True)
        self.assertEqual(outcome[1], False)
        self.assertNotIn("ran", outcome)

    def test_lock_is_released_afterwards(self):
        self._run(lambda: "x", lambda r, e: None)
        self.assertFalse(async_task.is_busy())

    def test_lock_is_released_after_error(self):
        def work():
            raise RuntimeError("boom")

        self._run(work, lambda r, e: None)
        self.assertFalse(async_task.is_busy())

    def test_lock_is_released_when_spawn_fails(self):
        def failing(worker):
            raise RuntimeError("no threads")

        with self.assertRaises(RuntimeError):
            async_task.run(self.ctx, lambda: "x", lambda r, e: None,
                           spawn=failing)
        self.assertFalse(async_task.is_busy())

    def test_label_is_visible_while_running(self):
        labels = []
        self._run(lambda: labels.append(async_task.current_label()),
                  lambda r, e: None, label="working")
        self.assertEqual(labels, ["working"])


if __name__ == "__main__":
    unittest.main()
