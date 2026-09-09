# -*- coding: utf-8 -*-
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at https://www.apache.org/licenses/LICENSE-2.0
"""Festgehaltenes Schreibziel: Antwort landet dort, wo sie angefordert wurde."""
import unittest

import context  # noqa: F401
from fakes import (FakeCalcDocument, FakeCellRange, FakeContext,
                   FakeDrawDocument, FakePage, FakeSelection, FakeSheet,
                   FakeShape, FakeTextRange, FakeWriterDocument)

from librecompass.office.document import OfficeDocument


class WriterTargetTest(unittest.TestCase):
    def setUp(self):
        self.document = FakeWriterDocument(selection_texts=("old",))
        self.doc = OfficeDocument(FakeContext(component=self.document))

    def test_capture_and_replace(self):
        target = self.doc.capture_target()
        self.assertEqual(target["kind"], "writer")
        self.assertTrue(self.doc.write_target(target, "new"))
        self.assertEqual(self.document.selection.getByIndex(0).getString(),
                         "new")

    def test_selection_change_does_not_move_the_result(self):
        target = self.doc.capture_target()
        original = self.document.selection.getByIndex(0)
        # Der Benutzer markiert zwischenzeitlich etwas anderes
        other = FakeTextRange("somewhere else")
        self.document.controller.selection = FakeSelection([other])
        self.doc.write_target(target, "new")
        self.assertEqual(original.getString(), "new")
        self.assertEqual(other.getString(), "somewhere else")

    def test_insert_uses_captured_cursor(self):
        target = self.doc.capture_target()
        self.assertTrue(self.doc.write_target(target, "added", mode="insert"))
        self.assertEqual(self.document.text.inserted, ["added"])

    def test_track_changes_is_restored(self):
        target = self.doc.capture_target()
        self.doc.write_target(target, "new", track_changes=True)
        self.assertEqual(self.document.record_changes_history,
                         [("RecordChanges", True), ("RecordChanges", False)])

    def test_further_ranges_are_cleared(self):
        document = FakeWriterDocument(selection_texts=("a", "b"))
        doc = OfficeDocument(FakeContext(component=document))
        target = doc.capture_target()
        doc.write_target(target, "new")
        self.assertEqual(document.selection.getByIndex(1).getString(), "")

    def test_missing_target_falls_back(self):
        self.assertTrue(self.doc.write_target(None, "new"))
        self.assertEqual(self.document.selection.getByIndex(0).getString(),
                         "new")


class CalcTargetTest(unittest.TestCase):
    def setUp(self):
        self.sheet = FakeSheet("Sheet1", {(0, 0): "A", (0, 1): "B"})
        cell_range = FakeCellRange(self.sheet, 0, 0, 0, 1)
        document = FakeCalcDocument([self.sheet], selection=cell_range)
        self.doc = OfficeDocument(FakeContext(component=document))
        self.document = document

    def test_capture_records_position(self):
        target = self.doc.capture_target()
        self.assertEqual((target["kind"], target["column"], target["row"],
                          target["below"]), ("calc", 0, 0, 2))

    def test_replace_writes_top_left(self):
        target = self.doc.capture_target()
        self.assertTrue(self.doc.write_target(target, "X"))
        self.assertEqual(self.sheet.getCellByPosition(0, 0).getString(), "X")

    def test_insert_writes_below(self):
        target = self.doc.capture_target()
        self.doc.write_target(target, "TOTAL", mode="insert")
        self.assertEqual(self.sheet.getCellByPosition(0, 2).getString(),
                         "TOTAL")

    def test_selection_change_does_not_move_the_result(self):
        target = self.doc.capture_target()
        self.document.controller.selection = FakeCellRange(self.sheet, 5, 5,
                                                           5, 5)
        self.doc.write_target(target, "X")
        self.assertEqual(self.sheet.getCellByPosition(0, 0).getString(), "X")
        self.assertEqual(self.sheet.getCellByPosition(5, 5).getString(), "")

    def test_no_selection_gives_no_target(self):
        document = FakeCalcDocument([self.sheet], selection=None)
        doc = OfficeDocument(FakeContext(component=document))
        self.assertIsNone(doc.capture_target())


class ShapeTargetTest(unittest.TestCase):
    def setUp(self):
        self.shape = FakeShape("Title")
        page = FakePage("Slide 1", [self.shape])
        self.document = FakeDrawDocument([page],
                                         selection=FakeSelection([self.shape]))
        self.page = page
        self.doc = OfficeDocument(FakeContext(component=self.document))

    def test_replace_captured_shape(self):
        target = self.doc.capture_target()
        self.assertTrue(self.doc.write_target(target, "NEW"))
        self.assertEqual(self.shape.getString(), "NEW")

    def test_insert_appends(self):
        target = self.doc.capture_target()
        self.doc.write_target(target, "MORE", mode="insert")
        self.assertEqual(self.shape.getString(), "Title\nMORE")

    def test_without_shape_insert_creates_one(self):
        document = FakeDrawDocument([FakePage("Slide 1", [])], selection=None)
        doc = OfficeDocument(FakeContext(component=document))
        target = doc.capture_target()
        self.assertTrue(doc.write_target(target, "FRESH", mode="insert"))
        self.assertEqual(document.getDrawPages().getByIndex(0).getCount(), 1)

    def test_without_shape_replace_fails(self):
        document = FakeDrawDocument([FakePage("Slide 1", [])], selection=None)
        doc = OfficeDocument(FakeContext(component=document))
        target = doc.capture_target()
        self.assertFalse(doc.write_target(target, "NEW"))


if __name__ == "__main__":
    unittest.main()
