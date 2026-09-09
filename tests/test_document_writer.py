# -*- coding: utf-8 -*-
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at https://www.apache.org/licenses/LICENSE-2.0
"""Writer-Pfade in office/document.py."""
import unittest

import context  # noqa: F401
from fakes import FakeContext, FakeWriterDocument

from librecompass.office.document import OfficeDocument


def make(document):
    ctx = FakeContext(component=document)
    return OfficeDocument(ctx)


class WriterDocumentTest(unittest.TestCase):
    def test_detects_writer(self):
        doc = make(FakeWriterDocument())
        self.assertEqual(doc.doc_type(), "writer")
        self.assertTrue(doc.is_writer())
        self.assertTrue(doc.is_supported())

    def test_no_document(self):
        doc = make(None)
        self.assertIsNone(doc.doc_type())
        self.assertFalse(doc.is_supported())

    def test_read_selection(self):
        doc = make(FakeWriterDocument(selection_texts=("hello",)))
        self.assertEqual(doc.get_selection(), "hello")

    def test_multiple_selection_is_joined(self):
        doc = make(FakeWriterDocument(selection_texts=("a", "b")))
        self.assertEqual(doc.get_selection(), "a\nb")

    def test_empty_selection(self):
        doc = make(FakeWriterDocument(selection_texts=()))
        self.assertEqual(doc.get_selection(), "")

    def test_document_text(self):
        doc = make(FakeWriterDocument(paragraphs=("one", "two")))
        self.assertEqual(doc.get_document_text(), "one\ntwo")

    def test_replace_selection(self):
        document = FakeWriterDocument(selection_texts=("old",))
        self.assertTrue(make(document).replace_selection("new"))
        self.assertEqual(document.selection.getByIndex(0).getString(), "new")

    def test_replace_clears_further_ranges(self):
        document = FakeWriterDocument(selection_texts=("a", "b"))
        make(document).replace_selection("new")
        self.assertEqual(document.selection.getByIndex(0).getString(), "new")
        self.assertEqual(document.selection.getByIndex(1).getString(), "")

    def test_replace_without_selection_inserts(self):
        document = FakeWriterDocument(selection_texts=())
        make(document).replace_selection("text")
        self.assertEqual(document.text.inserted, ["text"])

    def test_insert_at_cursor(self):
        document = FakeWriterDocument()
        self.assertTrue(make(document).insert_at_cursor("added"))
        self.assertEqual(document.text.inserted, ["added"])

    def test_track_changes_is_enabled_and_restored(self):
        document = FakeWriterDocument(selection_texts=("old",))
        make(document).replace_selection("new", track_changes=True)
        self.assertEqual(document.record_changes_history,
                         [("RecordChanges", True), ("RecordChanges", False)])
        self.assertFalse(document.properties["RecordChanges"])

    def test_track_changes_off_by_default(self):
        document = FakeWriterDocument(selection_texts=("old",))
        make(document).replace_selection("new")
        self.assertEqual(document.record_changes_history, [])

    def test_new_document(self):
        document = FakeWriterDocument()
        doc = make(document)
        created = doc.new_document_with_text("content")
        self.assertEqual(created.getText().getString(), "content")

    def test_status_indicator(self):
        document = FakeWriterDocument()
        indicator = make(document).status_indicator("working")
        self.assertEqual(indicator.started, ["working"])


if __name__ == "__main__":
    unittest.main()
