# -*- coding: utf-8 -*-
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at https://www.apache.org/licenses/LICENSE-2.0
"""UNO-Registrierung für LibreCompass.

Zwei Komponenten:

* ``LibreCompassJob`` nimmt die service:-URLs aus Addons.xcu,
  Accelerators.xcu und dem Kontextmenü entgegen (z. B.
  ``service:org.librecompass.Main?improve``) und delegiert an das Paket
  unter ``pythonpath/librecompass/``.
* ``ContextMenuJob`` wird über Jobs.xcu beim Start (``onFirstVisibleTask``)
  aufgerufen, versorgt alle offenen Dokumente mit dem Kontextmenü-
  Interceptor und meldet sich für alle weiteren am
  ``GlobalEventBroadcaster`` an.

Beide bleiben bewusst dünn; die gesamte Logik lebt im Paket.
"""
import os
import sys
import traceback

import unohelper
from com.sun.star.task import XJob, XJobExecutor

# Der Python-Loader von LibreOffice fügt das Komponentenverzeichnis zum
# sys.path hinzu; das pythonpath/-Verzeichnis defensiv ebenfalls eintragen.
_HERE = os.path.dirname(os.path.abspath(__file__))
_PYTHONPATH = os.path.join(_HERE, "pythonpath")
if _PYTHONPATH not in sys.path:
    sys.path.insert(0, _PYTHONPATH)

# Bei Umbenennung des Projekts: diese Namen, die Kennung in
# description.xml sowie die service:-URLs in Addons.xcu, Accelerators.xcu
# und ui/context_menu.py gemeinsam ändern.
IMPLEMENTATION_NAME = "org.librecompass.Main"
CONTEXT_MENU_NAME = "org.librecompass.ContextMenuJob"


class LibreCompassJob(unohelper.Base, XJobExecutor):
    """Empfängt Befehle über das service:-Protokoll."""

    def __init__(self, ctx):
        self.ctx = ctx

    def trigger(self, arg):
        command = (arg or "").strip()
        try:
            from librecompass.app import run_command
            run_command(self.ctx, command)
        except Exception:
            self._report(traceback.format_exc())

    def _report(self, details):
        try:
            from librecompass.ui.dialogs import message_box
            message_box(self.ctx, "LibreCompass", details)
        except Exception:
            sys.stderr.write(details + "\n")


class ContextMenuJob(unohelper.Base, XJob):
    """Startjob: hängt den Kontextmenü-Interceptor an alle Dokumente.

    Wird über Jobs.xcu an ``onFirstVisibleTask`` gebunden. Er versorgt die
    bereits offenen Dokumente und meldet sich anschließend am
    GlobalEventBroadcaster an, damit auch später geöffnete Dokumente das
    Menü bekommen. Fehler werden geschluckt: Der Start von LibreOffice darf
    daran nie scheitern.
    """

    def __init__(self, ctx):
        self.ctx = ctx

    def execute(self, arguments):
        try:
            from librecompass.config.settings import Settings
            from librecompass.i18n import apply_settings
            from librecompass.ui import context_menu
            try:
                apply_settings(self.ctx, Settings.load(self.ctx))
            except Exception:
                pass
            attached = context_menu.attach_global_listener(self.ctx)
            desktop = self.ctx.ServiceManager.createInstanceWithContext(
                "com.sun.star.frame.Desktop", self.ctx)
            count = context_menu.register_all_open(desktop)
            # Vermerk auf Platte: nur so lässt sich später feststellen, ob
            # der Job wirklich lief und nicht bloß konfiguriert ist.
            try:
                import time

                from librecompass import runtime
                runtime.note(settings,
                             startup_job_at=time.strftime("%Y-%m-%d %H:%M:%S"),
                             listener_attached=bool(attached),
                             documents_registered=count)
            except Exception:
                pass
            # Falls der Job doch einmal mit einem Dokument aufgerufen wird
            model = context_menu.model_from_job_arguments(arguments)
            if model is not None:
                context_menu.register_for_model(model)
        except Exception:
            sys.stderr.write(traceback.format_exc() + "\n")
        return ()


g_ImplementationHelper = unohelper.ImplementationHelper()
g_ImplementationHelper.addImplementation(
    LibreCompassJob,
    IMPLEMENTATION_NAME,
    (IMPLEMENTATION_NAME, "com.sun.star.task.Job"),
)
g_ImplementationHelper.addImplementation(
    ContextMenuJob,
    CONTEXT_MENU_NAME,
    (CONTEXT_MENU_NAME, "com.sun.star.task.Job"),
)
