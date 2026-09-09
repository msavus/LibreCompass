# -*- coding: utf-8 -*-
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at https://www.apache.org/licenses/LICENSE-2.0
"""Modellaufrufe im Hintergrund ausführen, ohne LibreOffice einzufrieren.

Ein Aufruf an llama.cpp dauert je nach Modell und Promptlänge Sekunden bis
Minuten. Läuft er auf dem Hauptthread, steht die gesamte Oberfläche still -
kein Scrollen, kein Tippen, nicht einmal Neuzeichnen.

Ablauf hier: ``work()`` läuft in einem Worker-Thread, ``done(result, error)``
wird über ``main_thread.run_on_main`` zurück auf den Hauptthread gelegt.
Alles, was Dokument oder Oberfläche anfasst, gehört ausschließlich in
``done``.

Zwei Regeln, die aus der Asynchronität folgen:

* **Ein Auftrag zur Zeit.** Sonst schickt ein ungeduldiger Doppelklick
  zwei Anfragen los, die sich beim Zurückschreiben überholen.
* **Das Ziel wird vorher festgehalten.** Wo die Antwort hinsoll, wird beim
  Absenden bestimmt (siehe ``OfficeDocument.capture_target``), nicht beim
  Eintreffen - die Auswahl kann sich zwischenzeitlich geändert haben.
"""
import threading
import traceback

from librecompass import main_thread

_lock = threading.Lock()
_busy = {"running": False, "label": ""}


def is_busy():
    with _lock:
        return _busy["running"]


def current_label():
    with _lock:
        return _busy["label"]


def _acquire(label):
    with _lock:
        if _busy["running"]:
            return False
        _busy["running"] = True
        _busy["label"] = label
        return True


def _release():
    with _lock:
        _busy["running"] = False
        _busy["label"] = ""


def run(ctx, work, done, indicator=None, label="", spawn=None):
    """``work()`` im Hintergrund, ``done(result, error)`` auf dem Hauptthread.

    Liefert False, wenn bereits ein Auftrag läuft. ``indicator`` ist eine
    bereits gestartete Statusanzeige; sie wird nach Abschluss beendet.
    ``spawn`` dient Tests als Ersatz für den Thread-Start.
    """
    if not _acquire(label):
        return False

    def finish(result, error):
        _release()
        if indicator is not None:
            try:
                indicator.end()
            except Exception:
                pass
        done(result, error)

    def worker():
        result, error = None, None
        try:
            result = work()
        except Exception as exc:
            error = exc
            if not str(exc):
                error = RuntimeError(traceback.format_exc())
        main_thread.run_on_main(ctx, lambda: finish(result, error))

    starter = spawn or _start_thread
    try:
        starter(worker)
    except Exception:
        _release()
        raise
    return True


def _start_thread(worker):
    threading.Thread(target=worker, daemon=True).start()
