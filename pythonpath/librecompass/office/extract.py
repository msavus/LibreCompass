# -*- coding: utf-8 -*-
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at https://www.apache.org/licenses/LICENSE-2.0
"""Text aus Dateien gewinnen – für die Wissensdatenbank.

Zwei Wege, in dieser Reihenfolge:

1. **Standardbibliothek** für ODF (odt/ods/odp/odg), OOXML (docx/xlsx/pptx)
   und Klartext (txt/md/csv/json/xml/html). Ein ODF/OOXML-Dokument ist ein
   ZIP mit XML darin – das lässt sich ohne Fremdpakete auslesen.
2. **LibreOffice selbst** für alles andere (PDF, DOC, RTF, EPUB …): Die
   Datei wird unsichtbar geladen, der Text entnommen und das Dokument
   sofort geschlossen. Das erspart PDF-Parser als Abhängigkeit – wer die
   Extension nutzt, hat LibreOffice ohnehin.
"""
import os
import zipfile
from xml.etree import ElementTree

PLAIN_SUFFIXES = (".txt", ".md", ".markdown", ".csv", ".tsv", ".json",
                  ".xml", ".html", ".htm", ".log", ".rst", ".adoc")
ODF_SUFFIXES = (".odt", ".ods", ".odp", ".odg", ".odf", ".fodt")
OOXML_SUFFIXES = (".docx", ".xlsx", ".pptx")
UNO_SUFFIXES = (".pdf", ".doc", ".xls", ".ppt", ".rtf", ".epub", ".wpd")

SUPPORTED_SUFFIXES = (PLAIN_SUFFIXES + ODF_SUFFIXES + OOXML_SUFFIXES
                      + UNO_SUFFIXES)


def is_supported(path):
    return os.path.splitext(path)[1].lower() in SUPPORTED_SUFFIXES


def extract_text(path, ctx=None, limit=400000):
    """Text einer Datei liefern ("" wenn nichts lesbar ist)."""
    suffix = os.path.splitext(path)[1].lower()
    try:
        if suffix in PLAIN_SUFFIXES:
            text = _read_plain(path)
        elif suffix in ODF_SUFFIXES:
            text = _read_odf(path)
        elif suffix in OOXML_SUFFIXES:
            text = _read_ooxml(path, suffix)
        elif ctx is not None:
            text = _read_via_office(path, ctx)
        else:
            text = ""
    except Exception:
        text = ""
    if limit and len(text) > int(limit):
        text = text[:int(limit)]
    return text.strip()


def collect_files(path, limit=500):
    """Datei oder Verzeichnis in eine Liste indexierbarer Dateien auflösen."""
    if os.path.isfile(path):
        return [path] if is_supported(path) else []
    found = []
    for base, dirs, files in os.walk(path):
        dirs[:] = [name for name in sorted(dirs)
                   if not name.startswith(".")]
        for name in sorted(files):
            if name.startswith("."):
                continue
            candidate = os.path.join(base, name)
            if is_supported(candidate):
                found.append(candidate)
            if len(found) >= limit:
                return found
    return found


# ---- Standardbibliothek ----------------------------------------------------
def _read_plain(path):
    with open(path, "r", encoding="utf-8", errors="replace") as handle:
        return handle.read()


def _local_name(tag):
    return tag.rsplit("}", 1)[-1]


def _xml_text(data, block_tags, break_tags=()):
    """Text aus XML sammeln; ``block_tags`` erzeugen Zeilenumbrüche."""
    root = ElementTree.fromstring(data)
    lines = []
    for element in root.iter():
        name = _local_name(element.tag)
        if name in break_tags:
            lines.append("")
        if name not in block_tags:
            continue
        pieces = []
        for node in element.iter():
            if node.text:
                pieces.append(node.text)
            if node is not element and node.tail:
                pieces.append(node.tail)
        line = "".join(pieces).strip()
        if line:
            lines.append(line)
    return "\n".join(lines)


def _read_odf(path):
    with zipfile.ZipFile(path) as archive:
        data = archive.read("content.xml")
    # p = Absatz, h = Überschrift, table-cell für Tabellen/Calc
    return _xml_text(data, block_tags=("p", "h"), break_tags=("table",))


def _read_ooxml(path, suffix):
    with zipfile.ZipFile(path) as archive:
        names = archive.namelist()
        if suffix == ".docx":
            return _xml_text(archive.read("word/document.xml"),
                             block_tags=("p",))
        if suffix == ".pptx":
            slides = sorted(name for name in names
                            if name.startswith("ppt/slides/slide")
                            and name.endswith(".xml"))
            parts = []
            for name in slides:
                text = _xml_text(archive.read(name), block_tags=("p",))
                if text.strip():
                    parts.append(text)
            return "\n\n".join(parts)
        if suffix == ".xlsx":
            shared = []
            if "xl/sharedStrings.xml" in names:
                shared = _shared_strings(archive.read("xl/sharedStrings.xml"))
            sheets = sorted(name for name in names
                            if name.startswith("xl/worksheets/sheet")
                            and name.endswith(".xml"))
            parts = []
            for name in sheets:
                text = _xlsx_sheet_text(archive.read(name), shared)
                if text.strip():
                    parts.append(text)
            return "\n\n".join(parts)
    return ""


def _shared_strings(data):
    root = ElementTree.fromstring(data)
    values = []
    for element in root:
        if _local_name(element.tag) != "si":
            continue
        pieces = [node.text for node in element.iter()
                  if _local_name(node.tag) == "t" and node.text]
        values.append("".join(pieces))
    return values


def _xlsx_sheet_text(data, shared):
    root = ElementTree.fromstring(data)
    lines = []
    for row in root.iter():
        if _local_name(row.tag) != "row":
            continue
        cells = []
        for cell in row:
            if _local_name(cell.tag) != "c":
                continue
            kind = cell.get("t")
            value = ""
            for node in cell:
                name = _local_name(node.tag)
                if name == "v" and node.text is not None:
                    value = node.text
                elif name == "is":
                    value = "".join(sub.text for sub in node.iter()
                                    if _local_name(sub.tag) == "t"
                                    and sub.text)
            if kind == "s" and value.isdigit():
                index = int(value)
                value = shared[index] if index < len(shared) else ""
            if value:
                cells.append(value)
        if cells:
            lines.append("\t".join(cells))
    return "\n".join(lines)


# ---- Umweg über LibreOffice ------------------------------------------------
def _read_via_office(path, ctx):
    """Datei unsichtbar in LibreOffice laden und den Text entnehmen."""
    import uno
    smgr = ctx.ServiceManager
    desktop = smgr.createInstanceWithContext(
        "com.sun.star.frame.Desktop", ctx)
    hidden = uno.createUnoStruct("com.sun.star.beans.PropertyValue")
    hidden.Name = "Hidden"
    hidden.Value = True
    readonly = uno.createUnoStruct("com.sun.star.beans.PropertyValue")
    readonly.Name = "ReadOnly"
    readonly.Value = True
    url = uno.systemPathToFileUrl(os.path.abspath(path))
    document = desktop.loadComponentFromURL(url, "_blank", 0,
                                            (hidden, readonly))
    if document is None:
        return ""
    try:
        return _document_text(document)
    finally:
        try:
            document.close(False)
        except Exception:
            pass


def _document_text(document):
    try:
        if document.supportsService("com.sun.star.text.TextDocument"):
            return document.getText().getString()
    except Exception:
        pass
    parts = []
    try:
        pages = document.getDrawPages()
    except Exception:
        pages = None
    if pages is not None:
        for index in range(pages.getCount()):
            page = pages.getByIndex(index)
            for shape_index in range(page.getCount()):
                try:
                    text = page.getByIndex(shape_index).getString()
                except Exception:
                    text = ""
                if text and text.strip():
                    parts.append(text.strip())
    return "\n".join(parts)
