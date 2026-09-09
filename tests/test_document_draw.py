# -*- coding: utf-8 -*-
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at https://www.apache.org/licenses/LICENSE-2.0
"""Impress-/Draw-Pfade in office/document.py."""
import unittest

import context  # noqa: F401
from fakes import (FakeContext, FakeDrawDocument, FakePage, FakeSelection,
                   FakeShape)

from librecompass.office.document import OfficeDocument


def build(shapes=("Title", "Body text"), selected=1, presentation=True):
    shape_objects = [FakeShape(text) for text in shapes]
    page = FakePage("Slide 1", shape_objects)
    selection = None
    if selected:
        selection = FakeSelection(shape_objects[:selected])
    document = FakeDrawDocument([page], selection=selection,
                                presentation=presentation)
    ctx = FakeContext(component=document)
    return document, page, shape_objects, OfficeDocument(ctx)


class DrawDocumentTest(unittest.TestCase):
    def test_detects_impress_and_draw(self):
        _, _, _, doc = build()
        self.assertEqual(doc.doc_type(), "impress")
        _, _, _, draw = build(presentation=False)
        self.assertEqual(draw.doc_type(), "draw")

    def test_selection_reads_shape_text(self):
        _, _, _, doc = build(selected=2)
        self.assertEqual(doc.get_selection(), "Title\n\nBody text")

    def test_document_text_lists_pages(self):
        _, _, _, doc = build()
        text = doc.get_document_text()
        self.assertIn("Slide 1", text)
        self.assertIn("Body text", text)

    def test_replace_first_selected_shape(self):
        _, _, shapes, doc = build(selected=1)
        self.assertTrue(doc.replace_selection("NEW"))
        self.assertEqual(shapes[0].getString(), "NEW")
        self.assertEqual(shapes[1].getString(), "Body text")

    def test_insert_appends_to_shape(self):
        _, _, shapes, doc = build(selected=1)
        self.assertTrue(doc.insert_at_cursor("MORE"))
        self.assertEqual(shapes[0].getString(), "Title\nMORE")

    def test_replace_without_selection_fails(self):
        _, _, _, doc = build(selected=0)
        self.assertFalse(doc.replace_selection("NEW"))

    def test_insert_without_selection_creates_text_shape(self):
        document, page, shapes, doc = build(selected=0)
        before = page.getCount()
        self.assertTrue(doc.insert_at_cursor("FRESH"))
        self.assertEqual(page.getCount(), before + 1)
        created = page.getByIndex(page.getCount() - 1)
        self.assertEqual(created.getString(), "FRESH")
        self.assertEqual(document.created[0][0],
                         "com.sun.star.drawing.TextShape")
        self.assertTrue(created.properties.get("TextAutoGrowHeight"))


if __name__ == "__main__":
    unittest.main()
