# -*- coding: utf-8 -*-
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at https://www.apache.org/licenses/LICENSE-2.0
"""AWT-Dialoge, zur Laufzeit gebaut - ohne Basic und ohne .xdl-Dateien.

Enthält Message-Box, Eingabedialog, Auswahlliste, Einstellungsdialog,
Wissensdatenbank- und Plug-in-Dialog sowie den DialogBuilder, den auch
das Panel (ui/panel.py) nutzt. Alle Texte laufen über i18n.
"""
import uno
from com.sun.star.awt.PushButtonType import CANCEL as PUSHBUTTON_CANCEL
from com.sun.star.awt.PushButtonType import OK as PUSHBUTTON_OK

from librecompass.i18n import gettext as _

_BUTTONS_OK = 1  # com.sun.star.awt.MessageBoxButtons.BUTTONS_OK

LANGUAGE_CODES = ("auto", "en", "de")


def _toolkit(ctx):
    return ctx.ServiceManager.createInstanceWithContext(
        "com.sun.star.awt.Toolkit", ctx)


def _parent_window(ctx):
    desktop = ctx.ServiceManager.createInstanceWithContext(
        "com.sun.star.frame.Desktop", ctx)
    frame = desktop.getCurrentFrame()
    return frame.getContainerWindow() if frame else None


def message_box(ctx, title, message, box_type="errorbox"):
    type_name = {
        "errorbox": "ERRORBOX",
        "infobox": "INFOBOX",
        "warningbox": "WARNINGBOX",
    }.get(box_type, "ERRORBOX")
    box = _toolkit(ctx).createMessageBox(
        _parent_window(ctx),
        uno.Enum("com.sun.star.awt.MessageBoxType", type_name),
        _BUTTONS_OK,
        str(title),
        str(message),
    )
    box.execute()


def info(ctx, message):
    message_box(ctx, _("LibreCompass"), message, "infobox")


def error(ctx, message):
    message_box(ctx, _("LibreCompass – Error"), message, "errorbox")


class DialogBuilder(object):
    """Kleiner Helfer, um AWT-Dialoge programmatisch zusammenzusetzen."""

    def __init__(self, ctx, title, width, height):
        smgr = ctx.ServiceManager
        self.ctx = ctx
        self.model = smgr.createInstanceWithContext(
            "com.sun.star.awt.UnoControlDialogModel", ctx)
        self.model.PositionX = 120
        self.model.PositionY = 60
        self.model.Width = width
        self.model.Height = height
        self.model.Title = title
        self.model.Closeable = True
        self.model.Moveable = True
        self.dialog = smgr.createInstanceWithContext(
            "com.sun.star.awt.UnoControlDialog", ctx)
        self._counter = 0

    def _add(self, service, x, y, width, height, **properties):
        self._counter += 1
        name = "control%d" % self._counter
        control = self.model.createInstance(service)
        control.PositionX = x
        control.PositionY = y
        control.Width = width
        control.Height = height
        for key, value in properties.items():
            setattr(control, key, value)
        self.model.insertByName(name, control)
        return name

    def label(self, x, y, width, text):
        return self._add("com.sun.star.awt.UnoControlFixedTextModel",
                         x, y, width, 10, Label=text)

    def edit(self, x, y, width, height=12, text="", multiline=False,
             readonly=False):
        return self._add("com.sun.star.awt.UnoControlEditModel",
                         x, y, width, height,
                         Text=text, MultiLine=multiline, VScroll=multiline,
                         ReadOnly=readonly)

    def checkbox(self, x, y, width, text, state):
        return self._add("com.sun.star.awt.UnoControlCheckBoxModel",
                         x, y, width, 10,
                         Label=text, State=1 if state else 0)

    def listbox(self, x, y, width, items, selected=0, dropdown=True,
                height=13):
        properties = {
            "StringItemList": tuple(items),
            "Dropdown": dropdown,
            "MultiSelection": False,
        }
        if items:
            properties["SelectedItems"] = (int(selected),)
        return self._add("com.sun.star.awt.UnoControlListBoxModel",
                         x, y, width, height, **properties)

    def push_button(self, x, y, width, text, height=13):
        return self._add("com.sun.star.awt.UnoControlButtonModel",
                         x, y, width, height, Label=text)

    def buttons(self, y):
        self._add("com.sun.star.awt.UnoControlButtonModel",
                  self.model.Width - 100, y, 46, 14,
                  Label=_("OK"), PushButtonType=PUSHBUTTON_OK,
                  DefaultButton=True)
        self._add("com.sun.star.awt.UnoControlButtonModel",
                  self.model.Width - 52, y, 46, 14,
                  Label=_("Cancel"), PushButtonType=PUSHBUTTON_CANCEL)

    def run(self):
        """Dialog modal anzeigen; True bei OK. Werte danach auslesen und
        mit close() freigeben."""
        self.dialog.setModel(self.model)
        self.dialog.createPeer(_toolkit(self.ctx), None)
        return self.dialog.execute() == 1

    def value(self, name):
        return self.dialog.getControl(name).getModel().Text

    def checked(self, name):
        return self.dialog.getControl(name).getModel().State == 1

    def selected(self, name):
        items = self.dialog.getControl(name).getModel().SelectedItems
        return int(items[0]) if items else None

    def close(self):
        try:
            self.dialog.dispose()
        except Exception:
            pass


# Rückwärtskompatibler Aliasname
_DialogBuilder = DialogBuilder


def input_dialog(ctx, title, label_text, default="", multiline=False):
    """Text abfragen; None bei Abbruch."""
    height = 96 if multiline else 64
    builder = DialogBuilder(ctx, title, 250, height)
    builder.label(8, 6, 234, label_text)
    field = builder.edit(8, 18, 234,
                         height=44 if multiline else 12,
                         text=default, multiline=multiline)
    builder.buttons(height - 20)
    try:
        if not builder.run():
            return None
        return builder.value(field).strip()
    finally:
        builder.close()


def list_dialog(ctx, title, items, height=170):
    """Eintrag aus einer Liste wählen; Index oder None bei Abbruch."""
    builder = DialogBuilder(ctx, title, 320, height)
    box = builder.listbox(8, 8, 304, items, dropdown=False,
                          height=height - 40)
    builder.buttons(height - 20)
    try:
        if not builder.run():
            return None
        return builder.selected(box)
    finally:
        builder.close()


def settings_dialog(ctx, settings):
    """Einstellungen bearbeiten; True, wenn gespeichert wurde."""
    builder = DialogBuilder(ctx, _("LibreCompass – Settings"), 264, 210)
    builder.label(8, 6, 248, _("Endpoint (OpenAI-compatible, e.g. Ollama):"))
    url_field = builder.edit(8, 17, 248, text=str(settings.base_url))
    builder.label(8, 36, 248, _("Chat model:"))
    model_field = builder.edit(8, 47, 248, text=str(settings.model))
    builder.label(8, 66, 248, _("Embedding model:"))
    embed_field = builder.edit(8, 77, 248, text=str(settings.embedding_model))
    builder.label(8, 96, 120, _("Temperature:"))
    temperature_field = builder.edit(8, 107, 120, text=str(settings.temperature))
    builder.label(136, 96, 120, _("Max. tokens:"))
    tokens_field = builder.edit(136, 107, 120, text=str(settings.max_tokens))
    track_box = builder.checkbox(
        8, 128, 248, _("Record replacements as tracked changes"),
        bool(settings.track_changes))
    stream_box = builder.checkbox(
        8, 142, 248, _("Streaming in the panel (disable if it misbehaves)"),
        bool(settings.stream))
    builder.label(8, 158, 60, _("Language:"))
    current = str(getattr(settings, "language", "auto")).lower()
    if current not in LANGUAGE_CODES:
        current = "auto"
    language_box = builder.listbox(
        70, 156, 100, (_("Automatic"), "English", "Deutsch"),
        selected=LANGUAGE_CODES.index(current))
    builder.label(8, 174, 248, _("Takes effect after reopening the panel."))
    builder.buttons(188)
    try:
        if not builder.run():
            return False
        base_url = builder.value(url_field).strip()
        model = builder.value(model_field).strip()
        embedding = builder.value(embed_field).strip()
        if base_url:
            settings.data["base_url"] = base_url
        if model:
            settings.data["model"] = model
        if embedding:
            settings.data["embedding_model"] = embedding
        try:
            settings.data["temperature"] = float(
                builder.value(temperature_field).replace(",", "."))
        except ValueError:
            pass
        try:
            settings.data["max_tokens"] = int(builder.value(tokens_field))
        except ValueError:
            pass
        settings.data["track_changes"] = builder.checked(track_box)
        settings.data["stream"] = builder.checked(stream_box)
        index = builder.selected(language_box)
        if index is not None and 0 <= index < len(LANGUAGE_CODES):
            settings.data["language"] = LANGUAGE_CODES[index]
        settings.save()
        return True
    finally:
        builder.close()
