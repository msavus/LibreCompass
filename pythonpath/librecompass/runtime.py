# -*- coding: utf-8 -*-
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at https://www.apache.org/licenses/LICENSE-2.0
"""Laufzeitspuren auf Platte - damit die Diagnose weiß, was passiert ist.

Startjob und Kontextmenü-Registrierung laufen in anderen Aufrufen als der
Diagnosebefehl. Modulvariablen sind zwischen ihnen nicht zuverlässig
gemeinsam, ein Vermerk in einer kleinen JSON-Datei dagegen schon. Damit
lässt sich die entscheidende Frage beantworten: Ist der Startjob überhaupt
gelaufen - oder nur konfiguriert?
"""
import json
import os
import time

FILENAME = "runtime.json"


def _path(settings):
    return os.path.join(settings.directory, FILENAME)


def load(settings):
    try:
        with open(_path(settings), "r", encoding="utf-8") as handle:
            data = json.load(handle)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def note(settings, **values):
    """Werte vermerken (bestehende bleiben erhalten)."""
    data = load(settings)
    data.update(values)
    data["updated"] = time.strftime("%Y-%m-%d %H:%M:%S")
    try:
        with open(_path(settings), "w", encoding="utf-8") as handle:
            json.dump(data, handle, ensure_ascii=False, indent=2)
    except Exception:
        pass
    return data
