# -*- coding: utf-8 -*-
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at https://www.apache.org/licenses/LICENSE-2.0
"""Kontextmenü dauerhaft in die Modulkonfiguration eintragen.

Der Interceptor-Weg (``ui/context_menu.py``) hängt an einem Startjob und
existiert nur zur Laufzeit. Hier ist der zweite, unabhängige Weg: Die
Einträge werden über den UI-Konfigurationsmanager in die Popup-Menüs der
Module geschrieben - dieselbe Stelle, die auch Extras > Anpassen >
Kontextmenüs bearbeitet. Sie überstehen damit einen Neustart und brauchen
weder Job noch Listener.

Das ist derselbe Mechanismus wie bei den Tastenkürzeln
(``office/shortcuts.py``), und der ist auf dieser LibreOffice-Version
nachweislich erreichbar.

Aufteilung wie überall: reine Logik (``menu_item``, ``find_entry``) getrennt
von den UNO-Aufrufen (``install``, ``remove``, ``installed_modules``).
"""
from librecompass.i18n import gettext as _

COMMAND_PREFIX = "service:org.librecompass.Main"
ROOT_LABEL = "LibreCompass"

# com.sun.star.ui.ItemType
ITEM_DEFAULT = 0
ITEM_SEPARATOR_LINE = 1

# Popup-Menüs je Modul. Mehrere pro Modul, weil LibreOffice je nach
# angeklicktem Objekt ein anderes Kontextmenü zeigt.
RESOURCES = (
    ("com.sun.star.text.TextDocument",
     ("private:resource/popupmenu/text",)),
    ("com.sun.star.sheet.SpreadsheetDocument",
     ("private:resource/popupmenu/cell",)),
    ("com.sun.star.presentation.PresentationDocument",
     ("private:resource/popupmenu/drawtext",
      "private:resource/popupmenu/draw")),
    ("com.sun.star.drawing.DrawingDocument",
     ("private:resource/popupmenu/drawtext",
      "private:resource/popupmenu/draw")),
)

# (msgid, Befehlsschlüssel); None erzeugt einen Trenner im Untermenü
ENTRIES = (
    ("Improve selection", "improve"),
    ("Rewrite selection …", "rewrite"),
    ("Summarize", "summarize"),
    ("Translate …", "translate"),
    ("Custom prompt …", "custom"),
    (None, None),
    ("LibreCompass panel", "panel"),
)


# ---- reine Logik -----------------------------------------------------------
def entry_labels():
    """Beschriftete Einträge in der aktiven Sprache: (Label, CommandURL)."""
    result = []
    for message, key in ENTRIES:
        if key is None:
            result.append((None, None))
        else:
            result.append((_(message), "%s?%s" % (COMMAND_PREFIX, key)))
    return result


def is_ours(properties):
    """Gehört ein Menüeintrag zu LibreCompass?

    ``properties`` ist die Eigenschaftsliste eines Eintrags als Folge von
    Objekten mit ``Name``/``Value`` - so liefert sie der
    Konfigurationsmanager.
    """
    label = None
    command = None
    for entry in properties or ():
        name = getattr(entry, "Name", None)
        if name == "Label":
            label = getattr(entry, "Value", None)
        elif name == "CommandURL":
            command = getattr(entry, "Value", None)
    if command and str(command).startswith(COMMAND_PREFIX):
        return True
    return label == ROOT_LABEL


def is_separator(properties):
    """Trennlinie? (Unsere Einträge stehen hinter einer solchen.)"""
    for entry in properties or ():
        if getattr(entry, "Name", None) == "Type":
            return getattr(entry, "Value", None) == ITEM_SEPARATOR_LINE
    return False


def find_entries(settings):
    """Indizes unserer Einträge in einem Menü, absteigend sortiert.

    Absteigend, damit sich beim Entfernen die folgenden Indizes nicht
    verschieben.
    """
    found = []
    try:
        count = settings.getCount()
    except Exception:
        return found
    for index in range(count):
        try:
            if is_ours(settings.getByIndex(index)):
                found.append(index)
        except Exception:
            continue
    return sorted(found, reverse=True)


def purge(settings):
    """Eigene Einträge entfernen; liefert die Anzahl.

    Räumt anschließend eine Trennlinie am Menüende mit weg: Sie stammt von
    uns (wir hängen immer Trenner + Eintrag ans Ende an), und eine
    Trennlinie als letzter Eintrag wäre ohnehin sinnlos.
    """
    removed = 0
    for index in find_entries(settings):
        try:
            settings.removeByIndex(index)
            removed += 1
        except Exception:
            continue
    try:
        last = settings.getCount() - 1
        if last >= 0 and is_separator(settings.getByIndex(last)):
            settings.removeByIndex(last)
            removed += 1
    except Exception:
        pass
    return removed


# ---- UNO-Anbindung ---------------------------------------------------------
def _property(name, value):
    import uno
    entry = uno.createUnoStruct("com.sun.star.beans.PropertyValue")
    entry.Name = name
    entry.Value = value
    return entry


def _item(label, command, submenu=None):
    """Menüeintrag als Eigenschaftsfolge, wie ihn die Konfiguration erwartet."""
    properties = [
        _property("CommandURL", command),
        _property("Label", label),
        _property("Type", ITEM_DEFAULT),
    ]
    if submenu is not None:
        properties.append(_property("ItemDescriptorContainer", submenu))
    return tuple(properties)


def _separator():
    return (_property("Type", ITEM_SEPARATOR_LINE),)


def _managers(ctx):
    """(Modulkennung, XUIConfigurationManager)-Paare."""
    result = []
    try:
        supplier = ctx.ServiceManager.createInstanceWithContext(
            "com.sun.star.ui.ModuleUIConfigurationManagerSupplier", ctx)
    except Exception:
        return result
    for module, resources in RESOURCES:
        try:
            result.append((module, supplier.getUIConfigurationManager(module),
                           resources))
        except Exception:
            continue
    return result


def _build_submenu(settings, ctx):
    """Untermenü als ItemDescriptorContainer füllen."""
    submenu = settings.createInstanceWithContext(ctx)
    position = 0
    for label, command in entry_labels():
        item = _separator() if command is None else _item(label, command)
        submenu.insertByIndex(position, item)
        position += 1
    return submenu


def install(ctx):
    """Einträge in alle Modul-Kontextmenüs schreiben.

    Liefert (Anzahl geänderter Menüs, Fehlerliste). Vorhandene Einträge
    werden zuvor entfernt, damit nichts doppelt erscheint.
    """
    changed = 0
    errors = []
    for module, manager, resources in _managers(ctx):
        touched = False
        for resource in resources:
            try:
                settings = manager.getSettings(resource, True)
            except Exception:
                # Nicht jedes Modul kennt jede Ressource - das ist normal.
                continue
            try:
                purge(settings)
                submenu = _build_submenu(settings, ctx)
                count = settings.getCount()
                settings.insertByIndex(count, _separator())
                settings.insertByIndex(
                    count + 1, _item(ROOT_LABEL, "", submenu))
                manager.replaceSettings(resource, settings)
                changed += 1
                touched = True
            except Exception as exc:
                errors.append("%s %s: %s"
                              % (module.rsplit(".", 1)[-1], resource, exc))
        if touched:
            try:
                manager.store()
            except Exception as exc:
                errors.append("%s: %s" % (module.rsplit(".", 1)[-1], exc))
    return changed, errors


def remove(ctx):
    """Eigene Einträge wieder aus den Kontextmenüs nehmen."""
    removed = 0
    for module, manager, resources in _managers(ctx):
        touched = False
        for resource in resources:
            try:
                settings = manager.getSettings(resource, True)
            except Exception:
                continue
            if not find_entries(settings):
                continue
            try:
                count = purge(settings)
                manager.replaceSettings(resource, settings)
                removed += count
                touched = True
            except Exception:
                continue
        if touched:
            try:
                manager.store()
            except Exception:
                pass
    return removed


def installed_modules(ctx):
    """Module, in deren Kontextmenü unsere Einträge stehen."""
    found = []
    for module, manager, resources in _managers(ctx):
        for resource in resources:
            try:
                settings = manager.getSettings(resource, False)
            except Exception:
                continue
            if find_entries(settings):
                found.append(module.rsplit(".", 1)[-1])
                break
    return found


def summary(changed, errors):
    lines = [_("Context menu added to {count} menus.").format(count=changed)]
    if errors:
        lines.append("")
        lines.append(_("Errors:"))
        lines.extend("  " + entry for entry in errors[:8])
    return "\n".join(lines)
