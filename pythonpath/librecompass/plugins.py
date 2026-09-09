# -*- coding: utf-8 -*-
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at https://www.apache.org/licenses/LICENSE-2.0
"""Plug-in-System: eigene Aktionen als einzelne Python-Dateien.

Plug-ins liegen als ``.py``-Dateien in ``<Profil>/user/librecompass/plugins/``.
Ein Plug-in beschreibt sich über Modulvariablen; alles ist optional außer
``NAME`` und mindestens einem von ``PROMPT`` oder ``run``::

    NAME = "Bullet points"
    DESCRIPTION = "Turns the selection into a bullet list"
    PROMPT = "Rewrite the following text as a concise bullet list."

Für mehr Kontrolle statt ``PROMPT`` eine Funktion ``run(api)``::

    NAME = "Word count"

    def run(api):
        text = api.selection() or api.document_text()
        api.message("%d words" % len(text.split()))

Das ``api``-Objekt (siehe ``PluginAPI``) erlaubt Lesen der Auswahl bzw. des
Dokuments, Anfragen an das Modell, Übernehmen von Text und Meldungen. Es
ist die einzige zugesagte Schnittstelle – der übrige Code kann sich ändern.

Sicherheitshinweis: Plug-ins sind gewöhnlicher Python-Code mit allen
Rechten des LibreOffice-Prozesses. Nur selbst geschriebene oder geprüfte
Dateien ablegen.
"""
import importlib.util
import os
import traceback

MODULE_PREFIX = "librecompass_plugin_"


class Plugin(object):
    def __init__(self, name, description, prompt, runner, path):
        self.name = name
        self.description = description
        self.prompt = prompt
        self.runner = runner
        self.path = path

    @property
    def has_prompt(self):
        return bool(self.prompt)

    @property
    def is_runnable(self):
        return callable(self.runner)

    def label(self):
        return ("%s – %s" % (self.name, self.description)
                if self.description else self.name)


def discover(settings):
    """Alle gültigen Plug-ins laden; defekte werden übersprungen."""
    directory = settings.plugins_dir()
    plugins = []
    try:
        names = sorted(os.listdir(directory))
    except Exception:
        return plugins
    for filename in names:
        if not filename.endswith(".py") or filename.startswith("_"):
            continue
        plugin = _load(os.path.join(directory, filename))
        if plugin is not None:
            plugins.append(plugin)
    return plugins


def _load(path):
    stem = os.path.splitext(os.path.basename(path))[0]
    try:
        spec = importlib.util.spec_from_file_location(
            MODULE_PREFIX + stem, path)
        if spec is None or spec.loader is None:
            return None
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
    except Exception:
        # Ein defektes Plug-in darf die Extension nicht lahmlegen.
        return None
    name = str(getattr(module, "NAME", "") or stem)
    prompt = getattr(module, "PROMPT", "") or ""
    runner = getattr(module, "run", None)
    if not prompt and not callable(runner):
        return None
    return Plugin(name, str(getattr(module, "DESCRIPTION", "") or ""),
                  str(prompt), runner, path)


class PluginAPI(object):
    """Stabile Schnittstelle für Plug-ins (siehe Modul-Dokumentation)."""

    def __init__(self, ctx, doc, client, settings, notify):
        self._ctx = ctx
        self._doc = doc
        self._client = client
        self._settings = settings
        self._notify = notify

    # ---- Lesen ---------------------------------------------------------------
    def selection(self):
        return self._doc.get_selection()

    def document_text(self):
        return self._doc.get_document_text()

    def module(self):
        return self._doc.doc_type()

    def setting(self, name, default=None):
        return self._settings.data.get(name, default)

    # ---- Modell --------------------------------------------------------------
    def ask(self, prompt):
        """Einzelanfrage an das Modell (synchron)."""
        return self._client.generate(prompt)

    def chat(self, messages):
        return self._client.chat(messages)

    # ---- Schreiben -----------------------------------------------------------
    def replace_selection(self, text):
        return self._doc.replace_selection(
            text, track_changes=bool(self._settings.track_changes))

    def insert(self, text):
        return self._doc.insert_at_cursor(
            text, track_changes=bool(self._settings.track_changes))

    def new_document(self, text):
        return self._doc.new_document_with_text(text)

    def message(self, text, title=None):
        self._notify(str(text), title)


def run_plugin(plugin, api):
    """Plug-in ausführen; Fehler werden als Text zurückgegeben, nie geworfen."""
    if not plugin.is_runnable:
        return "not-runnable"
    try:
        plugin.runner(api)
        return None
    except Exception:
        return traceback.format_exc()
