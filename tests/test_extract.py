# -*- coding: utf-8 -*-
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at https://www.apache.org/licenses/LICENSE-2.0
"""Textextraktion: ODF, OOXML und Klartext ohne LibreOffice."""
import os
import shutil
import tempfile
import unittest
import zipfile

import context  # noqa: F401

from librecompass.office import extract

ODT_CONTENT = """<?xml version="1.0" encoding="UTF-8"?>
<office:document-content
  xmlns:office="urn:oasis:names:tc:opendocument:xmlns:office:1.0"
  xmlns:text="urn:oasis:names:tc:opendocument:xmlns:text:1.0">
  <office:body><office:text>
    <text:h text:outline-level="1">Chapter One</text:h>
    <text:p>First paragraph with <text:span>inline</text:span> markup.</text:p>
    <text:p/>
    <text:p>Second paragraph.</text:p>
  </office:text></office:body>
</office:document-content>"""

DOCX_CONTENT = """<?xml version="1.0" encoding="UTF-8"?>
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:body>
    <w:p><w:r><w:t>Docx line one</w:t></w:r></w:p>
    <w:p><w:r><w:t>Docx </w:t></w:r><w:r><w:t>line two</w:t></w:r></w:p>
  </w:body>
</w:document>"""

SHARED = """<?xml version="1.0" encoding="UTF-8"?>
<sst xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
  <si><t>Region</t></si><si><t>North</t></si>
</sst>"""

SHEET = """<?xml version="1.0" encoding="UTF-8"?>
<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
  <sheetData>
    <row r="1"><c r="A1" t="s"><v>0</v></c><c r="B1"><v>42</v></c></row>
    <row r="2"><c r="A2" t="s"><v>1</v></c><c r="B2"><v>7</v></c></row>
  </sheetData>
</worksheet>"""


class ExtractTest(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.mkdtemp(prefix="librecompass-extract-")

    def tearDown(self):
        shutil.rmtree(self.directory, ignore_errors=True)

    def _path(self, name):
        return os.path.join(self.directory, name)

    def test_plain_text(self):
        path = self._path("notes.md")
        with open(path, "w", encoding="utf-8") as handle:
            handle.write("# Title\n\nSome text.")
        self.assertIn("Some text.", extract.extract_text(path))

    def test_odt(self):
        path = self._path("doc.odt")
        with zipfile.ZipFile(path, "w") as archive:
            archive.writestr("content.xml", ODT_CONTENT)
        text = extract.extract_text(path)
        self.assertIn("Chapter One", text)
        self.assertIn("inline", text)
        self.assertIn("Second paragraph.", text)

    def test_docx(self):
        path = self._path("doc.docx")
        with zipfile.ZipFile(path, "w") as archive:
            archive.writestr("word/document.xml", DOCX_CONTENT)
        text = extract.extract_text(path)
        self.assertIn("Docx line one", text)
        self.assertIn("Docx line two", text)

    def test_xlsx_uses_shared_strings(self):
        path = self._path("book.xlsx")
        with zipfile.ZipFile(path, "w") as archive:
            archive.writestr("xl/sharedStrings.xml", SHARED)
            archive.writestr("xl/worksheets/sheet1.xml", SHEET)
        text = extract.extract_text(path)
        self.assertIn("Region", text)
        self.assertIn("North", text)
        self.assertIn("42", text)

    def test_limit_is_applied(self):
        path = self._path("big.txt")
        with open(path, "w", encoding="utf-8") as handle:
            handle.write("x" * 5000)
        self.assertEqual(len(extract.extract_text(path, limit=100)), 100)

    def test_unsupported_suffix(self):
        path = self._path("image.png")
        with open(path, "wb") as handle:
            handle.write(b"\x89PNG")
        self.assertFalse(extract.is_supported(path))
        self.assertEqual(extract.extract_text(path), "")

    def test_broken_archive_returns_empty(self):
        path = self._path("broken.odt")
        with open(path, "wb") as handle:
            handle.write(b"not a zip")
        self.assertEqual(extract.extract_text(path), "")

    def test_pdf_without_context_returns_empty(self):
        path = self._path("file.pdf")
        with open(path, "wb") as handle:
            handle.write(b"%PDF-1.4")
        self.assertTrue(extract.is_supported(path))
        self.assertEqual(extract.extract_text(path), "")

    def test_collect_files_walks_directory(self):
        os.makedirs(self._path("sub"))
        for name in ("a.txt", "sub/b.md", "sub/c.png", ".hidden.txt"):
            with open(self._path(name), "w", encoding="utf-8") as handle:
                handle.write("x")
        found = extract.collect_files(self.directory)
        names = sorted(os.path.basename(path) for path in found)
        self.assertEqual(names, ["a.txt", "b.md"])

    def test_collect_files_single_file(self):
        path = self._path("single.txt")
        with open(path, "w", encoding="utf-8") as handle:
            handle.write("x")
        self.assertEqual(extract.collect_files(path), [path])


if __name__ == "__main__":
    unittest.main()
