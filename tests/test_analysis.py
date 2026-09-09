# -*- coding: utf-8 -*-
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at https://www.apache.org/licenses/LICENSE-2.0
"""Dokumentanalyse je Modul."""
import unittest

import context  # noqa: F401
from fakes import (FakeCalcDocument, FakeCell, FakeContext, FakeDrawDocument,
                   FakePage, FakeParagraph, FakeSheet, FakeShape,
                   FakeWriterDocument)

from librecompass import i18n
from librecompass.office import analysis
from librecompass.office.document import OfficeDocument


def wrap(document):
    return OfficeDocument(FakeContext(component=document))


class AnalysisTest(unittest.TestCase):
    def tearDown(self):
        i18n.set_language("en")

    def test_writer_metrics(self):
        paragraphs = [
            FakeParagraph("Introduction", "Heading 1"),
            FakeParagraph("Some body text with five words."),
            FakeParagraph("Details", "Heading 2"),
        ]
        document = FakeWriterDocument(paragraphs=paragraphs, tables=2,
                                     images=1)
        report = analysis.analyze(wrap(document))
        metrics = dict(report["metrics"])
        self.assertEqual(report["module"], "writer")
        self.assertEqual(metrics["Paragraphs"], 3)
        self.assertEqual(metrics["Headings"], 2)
        self.assertEqual(metrics["Tables"], 2)
        self.assertEqual(metrics["Images"], 1)
        self.assertEqual(report["outline"],
                         [(1, "Introduction"), (2, "Details")])

    def test_writer_word_and_character_counts(self):
        document = FakeWriterDocument(paragraphs=("one two three",))
        metrics = dict(analysis.analyze(wrap(document))["metrics"])
        self.assertEqual(metrics["Words"], 3)
        self.assertEqual(metrics["Characters"], len("one two three"))

    def test_calc_metrics(self):
        sheet = FakeSheet("Data", {
            (0, 0): "Item", (1, 0): FakeCell("3", "=1+2"),
            (0, 1): "Rent",
        })
        document = FakeCalcDocument([sheet])
        report = analysis.analyze(wrap(document))
        metrics = dict(report["metrics"])
        self.assertEqual(metrics["Sheets"], 1)
        self.assertEqual(metrics["Filled cells"], 3)
        self.assertEqual(metrics["Formulas"], 1)
        self.assertTrue(report["outline"])

    def test_impress_metrics(self):
        pages = [FakePage("Slide 1", [FakeShape("Agenda"), FakeShape("")]),
                 FakePage("Slide 2", [FakeShape("Results")])]
        document = FakeDrawDocument(pages)
        report = analysis.analyze(wrap(document))
        metrics = dict(report["metrics"])
        self.assertEqual(metrics["Slides"], 2)
        self.assertEqual(metrics["Shapes with text"], 2)
        self.assertIn("Agenda", report["outline"][0][1])

    def test_draw_uses_pages_label(self):
        document = FakeDrawDocument([FakePage("Page 1", [FakeShape("X")])],
                                    presentation=False)
        metrics = dict(analysis.analyze(wrap(document))["metrics"])
        self.assertIn("Pages", metrics)

    def test_format_report_contains_outline(self):
        document = FakeWriterDocument(
            paragraphs=[FakeParagraph("Title", "Heading 1")])
        report = analysis.analyze(wrap(document))
        text = analysis.format_report(report)
        self.assertIn("Outline", text)
        self.assertIn("Title", text)

    def test_labels_follow_language(self):
        i18n.set_language("de")
        document = FakeWriterDocument(paragraphs=("text",))
        metrics = dict(analysis.analyze(wrap(document))["metrics"])
        self.assertIn("Absätze", metrics)

    def test_unsupported_module(self):
        report = analysis.analyze(wrap(None))
        self.assertEqual(report["metrics"], [])
        self.assertEqual(report["module"], "-")


if __name__ == "__main__":
    unittest.main()
