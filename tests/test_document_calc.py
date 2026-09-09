# -*- coding: utf-8 -*-
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at https://www.apache.org/licenses/LICENSE-2.0
"""Calc-Pfade in office/document.py - zuvor nur strukturell geprüft."""
import unittest

import context  # noqa: F401
from fakes import (FakeCalcDocument, FakeCellRange, FakeCellRanges,
                   FakeContext, FakeSheet)

from librecompass.office.document import OfficeDocument


def build(cells=None, selection_box=(0, 0, 1, 1), ranges=False,
          extra_sheet=None):
    sheet = FakeSheet("Sheet1", cells if cells is not None else {
        (0, 0): "Region", (1, 0): "Sales",
        (0, 1): "North", (1, 1): "100",
    })
    sheets = [sheet]
    if extra_sheet is not None:
        sheets.append(extra_sheet)
    selection = None
    if selection_box is not None:
        cell_range = FakeCellRange(sheet, *selection_box)
        selection = FakeCellRanges([cell_range]) if ranges else cell_range
    document = FakeCalcDocument(sheets, selection=selection)
    ctx = FakeContext(component=document)
    return document, sheet, OfficeDocument(ctx)


class CalcDocumentTest(unittest.TestCase):
    def test_detects_calc(self):
        _, _, doc = build()
        self.assertEqual(doc.doc_type(), "calc")
        self.assertFalse(doc.is_writer())
        self.assertTrue(doc.is_supported())

    def test_selection_uses_tabs_and_newlines(self):
        _, _, doc = build()
        self.assertEqual(doc.get_selection(),
                         "Region\tSales\nNorth\t100")

    def test_selection_from_cell_ranges(self):
        _, _, doc = build(ranges=True)
        self.assertIn("Region\tSales", doc.get_selection())

    def test_no_selection(self):
        _, _, doc = build(selection_box=None)
        self.assertEqual(doc.get_selection(), "")

    def test_document_text_lists_sheets(self):
        other = FakeSheet("Costs", {(0, 0): "Item", (0, 1): "Rent"})
        _, _, doc = build(extra_sheet=other)
        text = doc.get_document_text()
        self.assertIn("Sheet1", text)
        self.assertIn("Costs", text)
        self.assertIn("Rent", text)

    def test_replace_writes_top_left_cell_only(self):
        _, sheet, doc = build()
        self.assertTrue(doc.replace_selection("SUMMARY"))
        self.assertEqual(sheet.getCellByPosition(0, 0).getString(), "SUMMARY")
        # Nachbarzellen bleiben unangetastet
        self.assertEqual(sheet.getCellByPosition(1, 0).getString(), "Sales")
        self.assertEqual(sheet.getCellByPosition(0, 1).getString(), "North")

    def test_insert_writes_below_selection(self):
        _, sheet, doc = build()
        self.assertTrue(doc.insert_at_cursor("TOTAL"))
        self.assertEqual(sheet.getCellByPosition(0, 2).getString(), "TOTAL")
        self.assertEqual(sheet.getCellByPosition(0, 0).getString(), "Region")

    def test_write_without_selection_fails_cleanly(self):
        _, _, doc = build(selection_box=None)
        self.assertFalse(doc.replace_selection("x"))
        self.assertFalse(doc.insert_at_cursor("x"))

    def test_track_changes_is_ignored_in_calc(self):
        _, sheet, doc = build()
        self.assertTrue(doc.replace_selection("X", track_changes=True))
        self.assertEqual(sheet.getCellByPosition(0, 0).getString(), "X")


if __name__ == "__main__":
    unittest.main()
