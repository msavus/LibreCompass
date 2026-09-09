# -*- coding: utf-8 -*-
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at https://www.apache.org/licenses/LICENSE-2.0
"""Kapselt alle UNO-Zugriffe auf das aktive Dokument – für alle Module.

Vollständig unterstützt: Writer, Calc, Impress, Draw. In übrigen Modulen
(Math, Base, Start Center) bleiben Panel und Chat nutzbar; Auswahl lesen
und automatisches Übernehmen entfallen dort ("Neues Dokument" geht immer).

Modulverhalten beim Schreiben:
- Writer:        Auswahl ersetzen bzw. an der Cursorposition einfügen;
                 optional als nachverfolgte Änderungen (RecordChanges).
- Calc:          Ersetzen schreibt in die oberste linke Zelle der Auswahl,
                 Einfügen in die Zelle unterhalb der Auswahl. Andere Zellen
                 werden nie angetastet.
- Impress/Draw:  Ersetzen setzt den Text der ersten markierten Form;
                 Einfügen hängt an die markierte Form an, ohne Markierung
                 wird eine neue Textbox auf der aktuellen Folie/Seite
                 angelegt.
"""
import uno

_MAX_TEXT_CHARS = 200000  # weiche Grenze beim Einsammeln von Dokumenttext
_MAX_CELLS = 20000        # Zellen-Obergrenze pro Bereich

_TYPES = (
    ("com.sun.star.text.TextDocument", "writer"),
    ("com.sun.star.sheet.SpreadsheetDocument", "calc"),
    ("com.sun.star.presentation.PresentationDocument", "impress"),
    ("com.sun.star.drawing.DrawingDocument", "draw"),
)


class OfficeDocument(object):
    def __init__(self, ctx):
        self.ctx = ctx
        smgr = ctx.ServiceManager
        self.desktop = smgr.createInstanceWithContext(
            "com.sun.star.frame.Desktop", ctx)
        self.model = self.desktop.getCurrentComponent()

    # ---- Zustand -----------------------------------------------------------
    def doc_type(self):
        if self.model is None:
            return None
        for service, name in _TYPES:
            try:
                if self.model.supportsService(service):
                    return name
            except Exception:
                return None
        return None

    def is_supported(self):
        return self.doc_type() is not None

    def is_writer(self):
        return self.doc_type() == "writer"

    def _controller(self):
        return self.model.getCurrentController()

    @staticmethod
    def _supports(obj, service):
        try:
            return obj is not None and obj.supportsService(service)
        except Exception:
            return False

    # ---- Lesen ----------------------------------------------------------------
    def get_selection(self):
        kind = self.doc_type()
        try:
            if kind == "writer":
                return self._writer_selection()
            if kind == "calc":
                return self._calc_selection_text()
            if kind in ("impress", "draw"):
                return self._items_text(self._controller().getSelection())
        except Exception:
            pass
        return ""

    def _writer_selection(self):
        selection = self._controller().getSelection()
        if selection is None:
            return ""
        parts = []
        for index in range(selection.getCount()):
            parts.append(selection.getByIndex(index).getString())
        return "\n".join(part for part in parts if part)

    def _calc_selection_text(self):
        selection = self._controller().getSelection()
        if self._supports(selection, "com.sun.star.sheet.SheetCellRanges"):
            parts = []
            for index in range(selection.getCount()):
                parts.append(self._range_text(selection.getByIndex(index)))
            return "\n".join(part for part in parts if part)
        if self._supports(selection, "com.sun.star.sheet.SheetCellRange"):
            return self._range_text(selection)
        return ""

    def _range_text(self, cell_range):
        """Zellbereich als Text: Spalten mit Tab, Zeilen mit Zeilenumbruch."""
        columns = cell_range.Columns.Count
        rows = cell_range.Rows.Count
        if columns * rows > _MAX_CELLS:
            rows = max(1, _MAX_CELLS // max(columns, 1))
        lines = []
        for row in range(rows):
            cells = []
            for column in range(columns):
                cells.append(
                    cell_range.getCellByPosition(column, row).getString())
            lines.append("\t".join(cells).rstrip())
        return "\n".join(line for line in lines if line.strip())

    def _items_text(self, selection):
        """Text markierter Formen bzw. Textbereiche (Impress/Draw)."""
        if selection is None:
            return ""
        try:
            count = selection.getCount()
        except Exception:
            return ""
        parts = []
        for index in range(count):
            item = selection.getByIndex(index)
            try:
                text = item.getString()
            except Exception:
                text = ""
            if text.strip():
                parts.append(text.strip())
        return "\n\n".join(parts)

    def get_document_text(self):
        kind = self.doc_type()
        try:
            if kind == "writer":
                return self.model.getText().getString()
            if kind == "calc":
                return self._calc_document_text()
            if kind in ("impress", "draw"):
                return self._pages_text()
        except Exception:
            pass
        return ""

    def _calc_document_text(self):
        parts = []
        total = 0
        sheets = self.model.getSheets()
        for index in range(sheets.getCount()):
            sheet = sheets.getByIndex(index)
            cursor = sheet.createCursor()
            cursor.gotoStartOfUsedArea(False)
            cursor.gotoEndOfUsedArea(True)
            text = self._range_text(cursor)
            if text.strip():
                parts.append("== Tabelle: %s ==\n%s"
                             % (sheet.getName(), text))
                total += len(parts[-1])
            if total > _MAX_TEXT_CHARS:
                break
        return "\n\n".join(parts)

    def _pages_text(self):
        parts = []
        total = 0
        pages = self.model.getDrawPages()
        for index in range(pages.getCount()):
            page = pages.getByIndex(index)
            texts = []
            for shape_index in range(page.getCount()):
                shape = page.getByIndex(shape_index)
                try:
                    text = shape.getString()
                except Exception:
                    text = ""
                if text.strip():
                    texts.append(text.strip())
            if texts:
                try:
                    name = page.getName()
                except Exception:
                    name = str(index + 1)
                parts.append("== Seite %s ==\n%s" % (name, "\n".join(texts)))
                total += len(parts[-1])
            if total > _MAX_TEXT_CHARS:
                break
        return "\n\n".join(parts)

    # ---- Schreiben ----------------------------------------------------------------
    def replace_selection(self, text, track_changes=False):
        """Antwort übernehmen; False, wenn das Modul es nicht unterstützt."""
        kind = self.doc_type()
        if kind == "writer":
            previous = self._enable_track_changes() if track_changes else None
            try:
                self._writer_replace(text)
            finally:
                self._restore_track_changes(previous)
            return True
        if kind == "calc":
            return self._calc_write(text, below=False)
        if kind in ("impress", "draw"):
            return self._shape_write(text, append=False)
        return False

    def insert_at_cursor(self, text, track_changes=False):
        kind = self.doc_type()
        if kind == "writer":
            previous = self._enable_track_changes() if track_changes else None
            try:
                cursor = self._controller().getViewCursor()
                cursor.getText().insertString(cursor, text, False)
            finally:
                self._restore_track_changes(previous)
            return True
        if kind == "calc":
            return self._calc_write(text, below=True)
        if kind in ("impress", "draw"):
            return self._shape_write(text, append=True)
        return False

    def _writer_replace(self, text):
        selection = self._controller().getSelection()
        if selection is None or selection.getCount() == 0:
            cursor = self._controller().getViewCursor()
            cursor.getText().insertString(cursor, text, False)
            return
        selection.getByIndex(0).setString(text)
        for index in range(1, selection.getCount()):
            selection.getByIndex(index).setString("")

    def _calc_write(self, text, below):
        selection = self._controller().getSelection()
        cell_range = None
        if (self._supports(selection, "com.sun.star.sheet.SheetCellRanges")
                and selection.getCount() > 0):
            cell_range = selection.getByIndex(0)
        elif self._supports(selection, "com.sun.star.sheet.SheetCellRange"):
            cell_range = selection
        if cell_range is None:
            return False
        address = cell_range.getRangeAddress()
        sheet = cell_range.getSpreadsheet()
        row = address.EndRow + 1 if below else address.StartRow
        try:
            cell = sheet.getCellByPosition(address.StartColumn, row)
        except Exception:
            return False
        cell.setString(text)
        return True

    def _shape_write(self, text, append):
        selection = self._controller().getSelection()
        try:
            count = selection.getCount() if selection is not None else 0
        except Exception:
            count = 0
        if count > 0:
            item = selection.getByIndex(0)
            try:
                if append:
                    existing = item.getString()
                    item.setString(
                        (existing + "\n" if existing.strip() else "") + text)
                else:
                    item.setString(text)
                return True
            except Exception:
                pass
        if append:
            return self._new_text_shape(text)
        return False

    def _new_text_shape(self, text):
        """Neue Textbox auf der aktuellen Folie/Seite anlegen."""
        try:
            page = self._controller().getCurrentPage()
            shape = self.model.createInstance("com.sun.star.drawing.TextShape")
            size = uno.createUnoStruct("com.sun.star.awt.Size")
            size.Width, size.Height = 12000, 3000
            position = uno.createUnoStruct("com.sun.star.awt.Point")
            position.X, position.Y = 2000, 2000
            shape.setSize(size)
            shape.setPosition(position)
            page.add(shape)
            try:
                shape.setPropertyValue("TextAutoGrowHeight", True)
            except Exception:
                pass
            shape.setString(text)
            return True
        except Exception:
            return False


    # ---- Schreibziel festhalten ---------------------------------------------
    # Bei asynchronen Anfragen liegen zwischen Absenden und Antwort Sekunden
    # bis Minuten. Die Auswahl kann sich in der Zeit ändern, deshalb wird das
    # Ziel beim Absenden festgehalten und die Antwort später genau dorthin
    # geschrieben - nicht in die dann aktuelle Auswahl.
    def capture_target(self):
        """Momentaufnahme des Schreibziels; None, wenn keines bestimmbar ist."""
        kind = self.doc_type()
        try:
            if kind == "writer":
                return self._capture_writer()
            if kind == "calc":
                return self._capture_calc()
            if kind in ("impress", "draw"):
                return self._capture_shape()
        except Exception:
            return None
        return None

    def _capture_writer(self):
        controller = self._controller()
        ranges = []
        selection = controller.getSelection()
        if selection is not None:
            for index in range(selection.getCount()):
                ranges.append(selection.getByIndex(index))
        cursor = None
        try:
            view_cursor = controller.getViewCursor()
            text = view_cursor.getText()
            cursor = (text, text.createTextCursorByRange(view_cursor))
        except Exception:
            cursor = None
        return {"kind": "writer", "ranges": ranges, "cursor": cursor}

    def _capture_calc(self):
        selection = self._controller().getSelection()
        cell_range = None
        if (self._supports(selection, "com.sun.star.sheet.SheetCellRanges")
                and selection.getCount() > 0):
            cell_range = selection.getByIndex(0)
        elif self._supports(selection, "com.sun.star.sheet.SheetCellRange"):
            cell_range = selection
        if cell_range is None:
            return None
        address = cell_range.getRangeAddress()
        return {"kind": "calc", "sheet": cell_range.getSpreadsheet(),
                "column": address.StartColumn, "row": address.StartRow,
                "below": address.EndRow + 1}

    def _capture_shape(self):
        selection = self._controller().getSelection()
        shape = None
        try:
            if selection is not None and selection.getCount() > 0:
                shape = selection.getByIndex(0)
        except Exception:
            shape = None
        page = None
        try:
            page = self._controller().getCurrentPage()
        except Exception:
            page = None
        return {"kind": self.doc_type(), "shape": shape, "page": page}

    def write_target(self, target, text, mode="replace", track_changes=False):
        """Antwort in das festgehaltene Ziel schreiben.

        ``mode`` ist "replace" oder "insert". Liefert False, wenn das Ziel
        nicht mehr beschreibbar ist (Dokument geschlossen, Form gelöscht).
        """
        if not target:
            # Ohne Momentaufnahme auf das übliche Verhalten zurückfallen.
            if mode == "insert":
                return self.insert_at_cursor(text, track_changes)
            return self.replace_selection(text, track_changes)
        kind = target.get("kind")
        try:
            if kind == "writer":
                return self._write_writer(target, text, mode, track_changes)
            if kind == "calc":
                return self._write_calc(target, text, mode)
            if kind in ("impress", "draw"):
                return self._write_shape(target, text, mode)
        except Exception:
            return False
        return False

    def _write_writer(self, target, text, mode, track_changes):
        previous = self._enable_track_changes() if track_changes else None
        try:
            ranges = target.get("ranges") or []
            if mode == "replace" and ranges:
                ranges[0].setString(text)
                for extra in ranges[1:]:
                    extra.setString("")
                return True
            cursor = target.get("cursor")
            if cursor is not None:
                text_object, position = cursor
                text_object.insertString(position, text, False)
                return True
            if ranges:
                ranges[0].setString(text)
                return True
            return False
        finally:
            self._restore_track_changes(previous)

    def _write_calc(self, target, text, mode):
        sheet = target.get("sheet")
        if sheet is None:
            return False
        row = target["below"] if mode == "insert" else target["row"]
        sheet.getCellByPosition(target["column"], row).setString(text)
        return True

    def _write_shape(self, target, text, mode):
        shape = target.get("shape")
        if shape is not None:
            if mode == "insert":
                existing = shape.getString()
                shape.setString(
                    (existing + "\n" if existing.strip() else "") + text)
            else:
                shape.setString(text)
            return True
        if mode == "insert":
            return self._new_text_shape(text)
        return False

    def new_document_with_text(self, text):
        """Neues Writer-Dokument anlegen und mit ``text`` befüllen."""
        document = self.desktop.loadComponentFromURL(
            "private:factory/swriter", "_blank", 0, ())
        document.getText().setString(text)
        return document

    # ---- Änderungsverfolgung (nur Writer) ------------------------------------------
    def _enable_track_changes(self):
        try:
            previous = self.model.getPropertyValue("RecordChanges")
            self.model.setPropertyValue("RecordChanges", True)
            return previous
        except Exception:
            return None

    def _restore_track_changes(self, previous):
        if previous is None:
            return
        try:
            self.model.setPropertyValue("RecordChanges", previous)
        except Exception:
            pass

    # ---- Statusanzeige ---------------------------------------------------------------
    def status_indicator(self, text):
        try:
            indicator = self._controller().getFrame().createStatusIndicator()
            indicator.start(text, 0)
            return indicator
        except Exception:
            return None
