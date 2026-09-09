# -*- coding: utf-8 -*-
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at https://www.apache.org/licenses/LICENSE-2.0
"""Zugriffe auf UI und Dokument aus Worker-Threads auf den Hauptthread bringen.

Streaming läuft in einem Hintergrund-Thread (siehe ui/panel.py). Änderungen
an Dialog-Controls oder am Dokument gehören aber auf den Hauptthread von
LibreOffice. Der kanonische Weg dafür ist der ``com.sun.star.awt.AsyncCallback``-
Dienst: Er stellt einen Callback in die Ereignisschleife des Hauptthreads.

Fällt der Dienst aus, wird der Callback als Best-Effort direkt ausgeführt
(die UNO-Bridge verkraftet das in der Praxis meist, garantiert ist es nicht).
"""
import sys
import traceback

import unohelper
from com.sun.star.awt import XCallback


class _Callback(unohelper.Base, XCallback):
    def __init__(self, func):
        self.func = func

    def notify(self, data):
        try:
            self.func()
        except Exception:
            sys.stderr.write(traceback.format_exc() + "\n")


def run_on_main(ctx, func):
    """``func`` (ohne Argumente) auf dem Hauptthread ausführen."""
    try:
        service = ctx.ServiceManager.createInstanceWithContext(
            "com.sun.star.awt.AsyncCallback", ctx)
        service.addCallback(_Callback(func), None)
    except Exception:
        try:
            func()
        except Exception:
            sys.stderr.write(traceback.format_exc() + "\n")
