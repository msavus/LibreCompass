# -*- coding: utf-8 -*-
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at https://www.apache.org/licenses/LICENSE-2.0
"""Dokumentanalyse: Strukturkennzahlen und Gliederung je Modul.

Der Bericht besteht aus zwei Teilen: harten Zahlen, die direkt über UNO
ermittelt werden (nachprüfbar, ohne Modell), und einer optionalen
Einschätzung des Sprachmodells. Die Trennung ist Absicht – Zahlen sollen
nicht aus einem Modell stammen.
"""
from librecompass.i18n import gettext as _

MAX_OUTLINE_ENTRIES = 60


def analyze(doc):
    """Kennzahlen und Gliederung als Dictionary."""
    kind = doc.doc_type()
    if kind == "writer":
        report = _writer(doc)
    elif kind == "calc":
        report = _calc(doc)
    elif kind in ("impress", "draw"):
        report = _pages(doc, kind)
    else:
        report = {"metrics": [], "outline": []}
    report["module"] = kind or "-"
    return report


def format_report(report):
    """Kennzahlen und Gliederung als Text (für Prompt und Dokument)."""
    lines = ["%s: %s" % (_("Module"), report.get("module", "-")), ""]
    for label, value in report.get("metrics", []):
        lines.append("%s: %s" % (label, value))
    outline = report.get("outline", [])
    if outline:
        lines.append("")
        lines.append(_("Outline") + ":")
        for level, title in outline:
            lines.append("%s- %s" % ("  " * max(0, level - 1), title))
    return "\n".join(lines)


# ---- Writer ----------------------------------------------------------------
def _writer(doc):
    text = doc.get_document_text()
    paragraphs = 0
    outline = []
    try:
        enumeration = doc.model.getText().createEnumeration()
        while enumeration.hasMoreElements():
            element = enumeration.nextElement()
            try:
                if not element.supportsService(
                        "com.sun.star.text.Paragraph"):
                    continue
            except Exception:
                continue
            paragraphs += 1
            style = ""
            try:
                style = str(element.getPropertyValue("ParaStyleName"))
            except Exception:
                pass
            content = ""
            try:
                content = element.getString().strip()
            except Exception:
                pass
            if content and style.lower().startswith("heading"):
                level = _heading_level(style)
                if len(outline) < MAX_OUTLINE_ENTRIES:
                    outline.append((level, content))
    except Exception:
        pass
    metrics = [
        (_("Paragraphs"), paragraphs),
        (_("Words"), len(text.split())),
        (_("Characters"), len(text)),
        (_("Headings"), len(outline)),
        (_("Tables"), _count(doc.model, "getTextTables")),
        (_("Images"), _count(doc.model, "getGraphicObjects")),
    ]
    return {"metrics": metrics, "outline": outline}


def _heading_level(style):
    digits = "".join(char for char in style if char.isdigit())
    try:
        return max(1, min(9, int(digits)))
    except ValueError:
        return 1


def _count(model, getter):
    try:
        return getattr(model, getter)().getCount()
    except Exception:
        return 0


# ---- Calc -------------------------------------------------------------------
def _calc(doc):
    sheets_count = 0
    filled = 0
    formulas = 0
    outline = []
    try:
        sheets = doc.model.getSheets()
        sheets_count = sheets.getCount()
        for index in range(sheets_count):
            sheet = sheets.getByIndex(index)
            cursor = sheet.createCursor()
            cursor.gotoStartOfUsedArea(False)
            cursor.gotoEndOfUsedArea(True)
            address = cursor.getRangeAddress()
            rows = address.EndRow - address.StartRow + 1
            columns = address.EndColumn - address.StartColumn + 1
            sheet_filled, sheet_formulas = _scan_range(cursor, columns, rows)
            filled += sheet_filled
            formulas += sheet_formulas
            if len(outline) < MAX_OUTLINE_ENTRIES:
                outline.append((1, "%s (%d×%d)" % (sheet.getName(),
                                                   rows, columns)))
    except Exception:
        pass
    metrics = [
        (_("Sheets"), sheets_count),
        (_("Filled cells"), filled),
        (_("Formulas"), formulas),
    ]
    return {"metrics": metrics, "outline": outline}


def _scan_range(cell_range, columns, rows, limit=20000):
    filled = 0
    formulas = 0
    scanned = 0
    for row in range(rows):
        for column in range(columns):
            if scanned >= limit:
                return filled, formulas
            scanned += 1
            try:
                cell = cell_range.getCellByPosition(column, row)
            except Exception:
                continue
            if cell.getString().strip():
                filled += 1
            try:
                if cell.getFormula().startswith("="):
                    formulas += 1
            except Exception:
                pass
    return filled, formulas


# ---- Impress / Draw ----------------------------------------------------------
def _pages(doc, kind):
    pages_count = 0
    with_text = 0
    characters = 0
    outline = []
    try:
        pages = doc.model.getDrawPages()
        pages_count = pages.getCount()
        for index in range(pages_count):
            page = pages.getByIndex(index)
            title = ""
            for shape_index in range(page.getCount()):
                try:
                    text = page.getByIndex(shape_index).getString()
                except Exception:
                    text = ""
                if text and text.strip():
                    with_text += 1
                    characters += len(text)
                    if not title:
                        title = text.strip().splitlines()[0]
            if len(outline) < MAX_OUTLINE_ENTRIES:
                outline.append((1, "%d: %s" % (index + 1, title or "—")))
    except Exception:
        pass
    metrics = [
        (_("Slides") if kind == "impress" else _("Pages"), pages_count),
        (_("Shapes with text"), with_text),
        (_("Characters"), characters),
    ]
    return {"metrics": metrics, "outline": outline}
