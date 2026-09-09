# -*- coding: utf-8 -*-
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at https://www.apache.org/licenses/LICENSE-2.0
"""LibreCompass-Einträge im Kontextmenü (Rechtsklick).

LibreOffice bietet für Kontextmenüs keine reine Konfigurationslösung wie
``Addons.xcu`` für die Menüleiste. Der dokumentierte Weg ist ein
``XContextMenuInterceptor``, der am Controller eines Dokuments registriert
wird. Damit das ohne Zutun des Benutzers passiert, hängt ``Jobs.xcu`` den
Job ``org.librecompass.ContextMenuJob`` an ``onFirstVisibleTask`` - das
einzige im Job-Framework dokumentierte und erprobte Startereignis. Der Job
versorgt alle bereits offenen Dokumente und meldet sich anschließend beim
``GlobalEventBroadcaster`` an, um jedes weitere Dokument zu erfassen
(siehe registration.py).

Frühere Fassung hing an ``OnViewCreated``/``OnLoad``/``OnNew``; diese
Namen sind als Job-Ereignisse nicht belegt, der Job lief nie an.

Aufgeteilt in reine Logik (``menu_entries``, ``build_menu``) und die
UNO-Anbindung (``Interceptor``, ``register_for_model``), damit der
Menüaufbau ohne LibreOffice testbar bleibt.

Grundsatz: Ein Fehler hier darf niemals das Öffnen eines Dokuments oder
das Kontextmenü selbst stören - deshalb ist alles defensiv gekapselt.
"""
import unohelper
from com.sun.star.document import XDocumentEventListener
from com.sun.star.ui import XContextMenuInterceptor
from com.sun.star.ui.ContextMenuInterceptorAction import (
    CONTINUE_MODIFIED, IGNORED)

from librecompass.i18n import gettext as _

SERVICE_URL = "service:org.librecompass.Main?%s"
ROOT_LABEL = "LibreCompass"

# (msgid, Befehlsschlüssel) - None erzeugt einen Trenner im Untermenü
ENTRIES = (
    ("Improve selection", "improve"),
    ("Rewrite selection …", "rewrite"),
    ("Summarize", "summarize"),
    ("Translate …", "translate"),
    ("Custom prompt …", "custom"),
    (None, None),
    ("LibreCompass panel", "panel"),
)

# Bereits versorgte Dokumente, damit mehrfach ausgelöste Ereignisse das
# Menü nicht doppelt einhängen.
#
# Der Schlüssel ist die RuntimeUID des Dokuments, NICHT id(controller):
# PyUNO liefert bei jedem getCurrentController() ein neues Proxy-Objekt,
# dessen id() sich unterscheidet. Mit id() als Schlüssel meldete die
# Prüfung "nicht registriert", obwohl registriert war - und es wurde bei
# jedem Aufruf erneut registriert.
_REGISTERED = {}
_MAX_TRACKED = 200
# Letzter Registrierungsversuch, damit die Diagnose den Grund nennen kann.
_LAST_ERROR = [None]


def document_key(model):
    """Stabiler Schlüssel für ein Dokument über Aufrufgrenzen hinweg."""
    for getter in ("RuntimeUID", "URL"):
        try:
            value = getattr(model, getter, None)
            if value:
                return "%s:%s" % (getter, value)
        except Exception:
            continue
    try:
        # Kein stabiler Schlüssel verfügbar: erneutes Registrieren ist
        # unschädlich, weil build_menu doppelte Einträge abfängt.
        return "id:%d" % id(model)
    except Exception:
        return None


def last_error():
    return _LAST_ERROR[0]


def menu_entries():
    """Beschriftete Einträge in der aktiven Sprache: (Label, CommandURL)."""
    entries = []
    for message, key in ENTRIES:
        if key is None:
            entries.append((None, None))
        else:
            entries.append((_(message), SERVICE_URL % key))
    return entries


def has_menu(container, label=ROOT_LABEL):
    """Steht unser Eintrag schon im Menü?

    Interceptoren werden verkettet und bekommen denselben Container. Ohne
    diese Prüfung erschiene das Untermenü mehrfach, sobald mehr als ein
    Interceptor registriert ist.
    """
    try:
        count = container.getCount()
    except Exception:
        return False
    for index in range(count):
        try:
            if getattr(container.getByIndex(index), "Text", None) == label:
                return True
        except Exception:
            continue
    return False


def build_menu(container, entries, label=ROOT_LABEL):
    """Untermenü im ``ActionTriggerContainer`` anlegen und anhängen.

    ``container`` ist zugleich die Fabrik für ActionTrigger-Objekte
    (XMultiServiceFactory). Liefert den erzeugten Wurzeleintrag, oder None,
    wenn der Eintrag bereits vorhanden ist.
    """
    if has_menu(container, label):
        return None
    submenu = container.createInstance(
        "com.sun.star.ui.ActionTriggerContainer")
    position = 0
    for label_text, command in entries:
        if command is None:
            item = submenu.createInstance(
                "com.sun.star.ui.ActionTriggerSeparator")
        else:
            item = submenu.createInstance("com.sun.star.ui.ActionTrigger")
            item.Text = label_text
            item.CommandURL = command
        submenu.insertByIndex(position, item)
        position += 1

    separator = container.createInstance(
        "com.sun.star.ui.ActionTriggerSeparator")
    root = container.createInstance("com.sun.star.ui.ActionTrigger")
    root.Text = label
    root.SubContainer = submenu

    count = container.getCount()
    container.insertByIndex(count, separator)
    container.insertByIndex(count + 1, root)
    return root


class Interceptor(unohelper.Base, XContextMenuInterceptor):
    """Hängt das LibreCompass-Untermenü an jedes Kontextmenü."""

    def notifyContextMenuExecute(self, event):
        try:
            build_menu(event.ActionTriggerContainer, menu_entries())
            return CONTINUE_MODIFIED
        except Exception:
            # Lieber kein Eintrag als ein kaputtes Kontextmenü.
            return IGNORED


def register_for_model(model):
    """Interceptor am Controller des Dokuments registrieren (einmalig)."""
    if model is None:
        _LAST_ERROR[0] = "kein Dokument"
        return False
    try:
        controller = model.getCurrentController()
    except Exception as exc:
        _LAST_ERROR[0] = "getCurrentController: %s" % exc
        return False
    if controller is None:
        _LAST_ERROR[0] = "kein Controller"
        return False
    key = document_key(model)
    if key is not None and key in _REGISTERED:
        return False
    try:
        interceptor = Interceptor()
        controller.registerContextMenuInterceptor(interceptor)
    except Exception as exc:
        _LAST_ERROR[0] = "registerContextMenuInterceptor: %s" % exc
        return False
    _LAST_ERROR[0] = None
    if len(_REGISTERED) > _MAX_TRACKED:
        _REGISTERED.clear()
    if key is not None:
        _REGISTERED[key] = interceptor
    return True


def model_from_job_arguments(arguments):
    """Das Dokument aus den Argumenten eines Job-Aufrufs herausziehen.

    Struktur laut Job-Framework: eine Sequenz von NamedValue, darin
    ``Environment`` mit ``Model`` (Dokumentereignis) oder ``Frame``.
    """
    for argument in arguments or ():
        if getattr(argument, "Name", "") != "Environment":
            continue
        for entry in argument.Value or ():
            name = getattr(entry, "Name", "")
            if name == "Model":
                return entry.Value
            if name == "Frame":
                frame = entry.Value
                try:
                    return frame.getController().getModel()
                except Exception:
                    return None
    return None


def is_registered_for(model):
    """Ist der Interceptor für dieses Dokument aktiv?"""
    if model is None:
        return False
    key = document_key(model)
    return key is not None and key in _REGISTERED


def register_all_open(desktop):
    """Alle bereits geöffneten Dokumente versorgen; Anzahl der Neuzugänge."""
    count = 0
    try:
        components = desktop.getComponents().createEnumeration()
    except Exception:
        return 0
    while True:
        try:
            if not components.hasMoreElements():
                break
            component = components.nextElement()
        except Exception:
            break
        try:
            if register_for_model(component):
                count += 1
        except Exception:
            continue
    return count


class DocumentListener(unohelper.Base, XDocumentEventListener):
    """Hängt den Interceptor an jedes neu geöffnete Dokument.

    Verlässlicher als eine Bindung an Dokumentereignisse in Jobs.xcu: der
    GlobalEventBroadcaster ist eine dokumentierte Schnittstelle und meldet
    jedes Dokument, egal wie es geöffnet wurde.
    """

    EVENTS = ("OnViewCreated", "OnLoad", "OnNew")

    def documentEventOccured(self, event):
        try:
            if event.EventName in self.EVENTS:
                register_for_model(event.Source)
        except Exception:
            pass

    def disposing(self, event):
        pass


_LISTENER = []


def attach_global_listener(ctx):
    """Einmalig am GlobalEventBroadcaster anmelden."""
    if _LISTENER:
        return False
    try:
        broadcaster = ctx.ServiceManager.createInstanceWithContext(
            "com.sun.star.frame.GlobalEventBroadcaster", ctx)
        listener = DocumentListener()
        broadcaster.addDocumentEventListener(listener)
    except Exception:
        return False
    _LISTENER.append(listener)
    return True


def ensure_active(ctx, model):
    """Listener anmelden und dieses Dokument versorgen.

    Wird bei jedem LibreCompass-Befehl aufgerufen: Selbst wenn der Startjob
    nicht lief, ist das Kontextmenü spätestens nach der ersten Benutzung
    der Extension aktiv.
    """
    attached = attach_global_listener(ctx)
    registered = register_for_model(model) if model is not None else False
    return attached, registered
