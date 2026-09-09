# -*- coding: utf-8 -*-
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at https://www.apache.org/licenses/LICENSE-2.0
"""Attrappen für UNO-Objekte: Kontext, Desktop und Dokumente je Modul.

Damit werden die modulspezifischen Pfade in ``office/document.py`` und
``office/analysis.py`` prüfbar, ohne LibreOffice zu starten. Nachgebildet
ist nur der Teil der UNO-API, den die Extension tatsächlich benutzt.
"""


# ---- Writer ----------------------------------------------------------------
class FakeTextRange(object):
    def __init__(self, text=""):
        self.text = text

    def getString(self):
        return self.text

    def setString(self, value):
        self.text = value


class FakeSelection(object):
    def __init__(self, ranges):
        self.ranges = list(ranges)

    def getCount(self):
        return len(self.ranges)

    def getByIndex(self, index):
        return self.ranges[index]

    def supportsService(self, name):
        return False


class FakeParagraph(object):
    def __init__(self, text, style="Default Paragraph Style"):
        self.text = text
        self.style = style

    def supportsService(self, name):
        return name == "com.sun.star.text.Paragraph"

    def getString(self):
        return self.text

    def getPropertyValue(self, name):
        if name == "ParaStyleName":
            return self.style
        raise KeyError(name)


class FakeEnumeration(object):
    def __init__(self, items):
        self.items = list(items)
        self.position = 0

    def hasMoreElements(self):
        return self.position < len(self.items)

    def nextElement(self):
        item = self.items[self.position]
        self.position += 1
        return item


class FakeText(object):
    def __init__(self, paragraphs):
        self.paragraphs = list(paragraphs)
        self.inserted = []

    def getString(self):
        return "\n".join(item.text for item in self.paragraphs)

    def setString(self, value):
        self.paragraphs = [FakeParagraph(value)]

    def createEnumeration(self):
        return FakeEnumeration(self.paragraphs)

    def insertString(self, cursor, text, absorb):
        self.inserted.append(text)

    def createTextCursorByRange(self, position):
        return FakeViewCursor(self)


class FakeViewCursor(object):
    def __init__(self, text):
        self._text = text

    def getText(self):
        return self._text


class FakeCounter(object):
    """Zählt wie UNO-Container: Eigenschaft ``Count`` und ``getCount()``."""

    def __init__(self, count):
        self.count = count
        self.Count = count

    def getCount(self):
        return self.count


class FakeController(object):
    def __init__(self, selection=None, view_cursor=None, page=None):
        self.selection = selection
        self.view_cursor = view_cursor
        self.page = page
        self.indicator = FakeStatusIndicator()

    def getSelection(self):
        return self.selection

    def getViewCursor(self):
        return self.view_cursor

    def getCurrentPage(self):
        return self.page

    def getFrame(self):
        return self

    def createStatusIndicator(self):
        return self.indicator

    def getContainerWindow(self):
        return None


class FakeStatusIndicator(object):
    def __init__(self):
        self.started = []
        self.ended = 0

    def start(self, text, value):
        self.started.append(text)

    def end(self):
        self.ended += 1


class FakeWriterDocument(object):
    SERVICE = "com.sun.star.text.TextDocument"

    def __init__(self, paragraphs=("Hello world",), selection_texts=(),
                 tables=0, images=0):
        self.text = FakeText([FakeParagraph(item) if isinstance(item, str)
                              else item for item in paragraphs])
        ranges = [FakeTextRange(value) for value in selection_texts]
        self.selection = FakeSelection(ranges)
        self.controller = FakeController(
            selection=self.selection,
            view_cursor=FakeViewCursor(self.text))
        self.properties = {"RecordChanges": False}
        self.record_changes_history = []
        self._tables = FakeCounter(tables)
        self._images = FakeCounter(images)

    def supportsService(self, name):
        return name == self.SERVICE

    def getCurrentController(self):
        return self.controller

    def getText(self):
        return self.text

    def getTextTables(self):
        return self._tables

    def getGraphicObjects(self):
        return self._images

    def getPropertyValue(self, name):
        return self.properties[name]

    def setPropertyValue(self, name, value):
        self.properties[name] = value
        self.record_changes_history.append((name, value))


# ---- Calc -------------------------------------------------------------------
class FakeCell(object):
    def __init__(self, value="", formula=""):
        self.value = value
        self.formula = formula

    def getString(self):
        return self.value

    def setString(self, value):
        self.value = value
        self.formula = value

    def getFormula(self):
        return self.formula or self.value


class FakeRangeAddress(object):
    def __init__(self, start_column, start_row, end_column, end_row, sheet=0):
        self.StartColumn = start_column
        self.StartRow = start_row
        self.EndColumn = end_column
        self.EndRow = end_row
        self.Sheet = sheet


class FakeCellRange(object):
    SERVICE = "com.sun.star.sheet.SheetCellRange"

    def __init__(self, sheet, start_column, start_row, end_column, end_row):
        self.sheet = sheet
        self.address = FakeRangeAddress(start_column, start_row,
                                        end_column, end_row)
        self.Columns = FakeCounter(end_column - start_column + 1)
        self.Rows = FakeCounter(end_row - start_row + 1)

    def supportsService(self, name):
        return name == self.SERVICE

    def getRangeAddress(self):
        return self.address

    def getSpreadsheet(self):
        return self.sheet

    def getCellByPosition(self, column, row):
        return self.sheet.getCellByPosition(self.address.StartColumn + column,
                                            self.address.StartRow + row)

    # Cursor-Verhalten: der Bereich stellt sich auf den benutzten Bereich ein
    def gotoStartOfUsedArea(self, expand):
        used = self.sheet.used_area()
        self.address.StartColumn, self.address.StartRow = used[0], used[1]
        self._sync()

    def gotoEndOfUsedArea(self, expand):
        used = self.sheet.used_area()
        self.address.EndColumn, self.address.EndRow = used[2], used[3]
        self._sync()

    def _sync(self):
        self.Columns = FakeCounter(
            max(0, self.address.EndColumn - self.address.StartColumn + 1))
        self.Rows = FakeCounter(
            max(0, self.address.EndRow - self.address.StartRow + 1))


class FakeCellRanges(object):
    SERVICE = "com.sun.star.sheet.SheetCellRanges"

    def __init__(self, ranges):
        self.ranges = list(ranges)

    def supportsService(self, name):
        return name == self.SERVICE

    def getCount(self):
        return len(self.ranges)

    def getByIndex(self, index):
        return self.ranges[index]


class FakeSheet(object):
    def __init__(self, name, cells=None):
        self.name = name
        self.cells = {}
        for position, value in (cells or {}).items():
            self.cells[position] = (FakeCell(value)
                                    if isinstance(value, str) else value)

    def getName(self):
        return self.name

    def getCellByPosition(self, column, row):
        return self.cells.setdefault((column, row), FakeCell())

    def used_area(self):
        filled = [key for key, cell in self.cells.items()
                  if cell.getString().strip()]
        if not filled:
            return (0, 0, 0, 0)
        columns = [key[0] for key in filled]
        rows = [key[1] for key in filled]
        return (min(columns), min(rows), max(columns), max(rows))

    def createCursor(self):
        return FakeCellRange(self, 0, 0, 0, 0)


class FakeSheets(object):
    def __init__(self, sheets):
        self.sheets = list(sheets)

    def getCount(self):
        return len(self.sheets)

    def getByIndex(self, index):
        return self.sheets[index]


class FakeCalcDocument(object):
    SERVICE = "com.sun.star.sheet.SpreadsheetDocument"

    def __init__(self, sheets, selection=None):
        self.sheets = FakeSheets(sheets)
        self.controller = FakeController(selection=selection)

    def supportsService(self, name):
        return name == self.SERVICE

    def getCurrentController(self):
        return self.controller

    def getSheets(self):
        return self.sheets


# ---- Impress / Draw ---------------------------------------------------------
class FakeShape(object):
    def __init__(self, text=""):
        self.text = text
        self.size = None
        self.position = None
        self.properties = {}

    def getString(self):
        return self.text

    def setString(self, value):
        self.text = value

    def setSize(self, size):
        self.size = size

    def setPosition(self, position):
        self.position = position

    def setPropertyValue(self, name, value):
        self.properties[name] = value


class FakePage(object):
    def __init__(self, name, shapes=()):
        self.name = name
        self.shapes = list(shapes)

    def getName(self):
        return self.name

    def getCount(self):
        return len(self.shapes)

    def getByIndex(self, index):
        return self.shapes[index]

    def add(self, shape):
        self.shapes.append(shape)


class FakePages(object):
    def __init__(self, pages):
        self.pages = list(pages)

    def getCount(self):
        return len(self.pages)

    def getByIndex(self, index):
        return self.pages[index]


class FakeDrawDocument(object):
    def __init__(self, pages, selection=None, presentation=True):
        self.SERVICE = ("com.sun.star.presentation.PresentationDocument"
                        if presentation
                        else "com.sun.star.drawing.DrawingDocument")
        self.pages = FakePages(pages)
        self.created = []
        self.controller = FakeController(
            selection=selection,
            page=pages[0] if pages else None)

    def supportsService(self, name):
        return name == self.SERVICE

    def getCurrentController(self):
        return self.controller

    def getDrawPages(self):
        return self.pages

    def createInstance(self, name):
        shape = FakeShape()
        self.created.append((name, shape))
        return shape


# ---- Kontext / Desktop ------------------------------------------------------
class FakeDesktop(object):
    def __init__(self, component=None):
        self.component = component
        self.loaded = []
        self.new_documents = []

    def getCurrentComponent(self):
        return self.component

    def getCurrentFrame(self):
        return None

    def loadComponentFromURL(self, url, target, flags, arguments):
        if url == "private:factory/swriter":
            document = FakeWriterDocument(paragraphs=())
            self.new_documents.append(document)
            return document
        self.loaded.append(url)
        return FakeWriterDocument(paragraphs=("loaded",))


class FakePathSubstitution(object):
    def __init__(self, directory):
        self.directory = directory

    def substituteVariables(self, variable, enabled):
        return "file://" + self.directory


class FakeConfigurationAccess(object):
    def __init__(self, locale):
        self.locale = locale

    def getByName(self, name):
        if name == "ooLocale":
            return self.locale
        raise KeyError(name)


class FakeConfigurationProvider(object):
    def __init__(self, locale):
        self.locale = locale

    def createInstanceWithArguments(self, service, arguments):
        return FakeConfigurationAccess(self.locale)


class FakeServiceManager(object):
    def __init__(self, ctx):
        self.ctx = ctx

    def createInstanceWithContext(self, name, ctx):
        if name == "com.sun.star.frame.Desktop":
            return self.ctx.desktop
        if name == "com.sun.star.util.PathSubstitution":
            return FakePathSubstitution(self.ctx.profile_dir)
        if name == "com.sun.star.configuration.ConfigurationProvider":
            return FakeConfigurationProvider(self.ctx.locale)
        raise RuntimeError("Service nicht in der Attrappe: %s" % name)


class FakeContext(object):
    def __init__(self, component=None, profile_dir="/tmp", locale="en-US"):
        self.desktop = FakeDesktop(component)
        self.profile_dir = profile_dir
        self.locale = locale
        self.ServiceManager = FakeServiceManager(self)

    def set_component(self, component):
        self.desktop.component = component


# ---- Modell-Attrappe -------------------------------------------------------
class FakeClient(object):
    """Ersatz für LLMClient: deterministisch, ohne Netzwerk."""

    def __init__(self, answer="ANSWER", dimension=8):
        self.answer = answer
        self.dimension = dimension
        self.prompts = []
        self.embedded = []

    def generate(self, prompt):
        self.prompts.append(prompt)
        return self.answer

    def chat(self, messages):
        self.prompts.append(messages)
        return self.answer

    def embeddings(self, inputs, model=None):
        self.embedded.extend(inputs)
        return [self._vector(text) for text in inputs]

    def _vector(self, text):
        vector = [0.0] * self.dimension
        for position, char in enumerate(text.lower()):
            vector[(ord(char) + position) % self.dimension] += 1.0
        if not any(vector):
            vector[0] = 1.0
        return vector


# ---- Kontextmenü ------------------------------------------------------------
class FakeActionTrigger(object):
    """ActionTrigger bzw. Separator; der Diensttyp wird mitgeführt."""

    def __init__(self, service):
        self.service = service
        self.Text = None
        self.CommandURL = None
        self.SubContainer = None

    @property
    def is_separator(self):
        return self.service.endswith("ActionTriggerSeparator")


class FakeActionTriggerContainer(object):
    """Container und Fabrik in einem - wie im echten Kontextmenü-Ereignis."""

    def __init__(self, existing=0):
        self.items = [FakeActionTrigger("existing") for _ in range(existing)]
        self.created = []

    def createInstance(self, service):
        if service.endswith("ActionTriggerContainer"):
            child = FakeActionTriggerContainer()
        else:
            child = FakeActionTrigger(service)
        self.created.append(service)
        return child

    def getCount(self):
        return len(self.items)

    def getByIndex(self, index):
        return self.items[index]

    def insertByIndex(self, index, item):
        self.items.insert(index, item)


class FakeContextMenuEvent(object):
    def __init__(self, container):
        self.ActionTriggerContainer = container


class FakeNamedValue(object):
    def __init__(self, name, value):
        self.Name = name
        self.Value = value


# ---- Kontextmenü-Konfiguration ----------------------------------------------
class FakeProperty(object):
    def __init__(self, name, value):
        self.Name = name
        self.Value = value


class FakeItemContainer(object):
    """XIndexContainer der Menükonfiguration, zugleich Fabrik für Untermenüs."""

    def __init__(self, items=()):
        self.items = list(items)
        self.created = []

    def createInstanceWithContext(self, ctx):
        child = FakeItemContainer()
        self.created.append(child)
        return child

    def getCount(self):
        return len(self.items)

    def getByIndex(self, index):
        return self.items[index]

    def insertByIndex(self, index, item):
        self.items.insert(index, item)

    def removeByIndex(self, index):
        del self.items[index]


class FakeUIConfigurationManager(object):
    def __init__(self, resources=None, readonly=False):
        self.settings = {name: FakeItemContainer()
                         for name in (resources or ())}
        self.replaced = []
        self.stored = 0
        self.readonly = readonly

    def getSettings(self, resource, writable):
        if resource not in self.settings:
            raise RuntimeError("NoSuchElement: %s" % resource)
        return self.settings[resource]

    def replaceSettings(self, resource, settings):
        if self.readonly:
            raise RuntimeError("read-only configuration")
        self.settings[resource] = settings
        self.replaced.append(resource)

    def store(self):
        self.stored += 1
