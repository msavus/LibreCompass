# -*- coding: utf-8 -*-
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at https://www.apache.org/licenses/LICENSE-2.0
"""Basisklasse für alle Befehle.

Ablauf: Auswahl lesen -> Prompt bauen -> Modell fragen -> Ergebnis anwenden.
Der Modellaufruf läuft im Hintergrund (siehe async_task), damit LibreOffice
währenddessen bedienbar bleibt. Das Schreibziel wird vor dem Absenden
festgehalten, damit die Antwort auch dann richtig landet, wenn sich die
Auswahl inzwischen geändert hat.
"""
from librecompass import async_task
from librecompass.ai import prompts
from librecompass.i18n import gettext as _
from librecompass.ui import dialogs


class Command(object):
    needs_document = True

    def __init__(self, ctx, doc, client, settings):
        self.ctx = ctx
        self.doc = doc
        self.client = client
        self.settings = settings

    # ---- Bausteine --------------------------------------------------------
    def require_selection(self):
        text = self.doc.get_selection()
        if not text.strip():
            dialogs.info(self.ctx, _("Please select text or cells first."))
            return None
        return text

    def ask_model(self, instruction, text, mode="replace"):
        """Instruktion + TEXT-Block ans Modell, Ergebnis ins Dokument."""
        self.ask_model_raw(prompts.build_prompt(instruction, text), mode=mode)

    def ask_model_raw(self, prompt, mode="replace", status=None,
                      on_result=None):
        """Modell im Hintergrund fragen.

        ``on_result(text)`` übernimmt das Ergebnis; ohne Angabe wird es
        gemäß ``mode`` ("replace"/"insert") ins festgehaltene Ziel
        geschrieben.
        """
        if async_task.is_busy():
            dialogs.info(self.ctx, _("A request is already running. Please "
                                     "wait for it to finish."))
            return False
        target = self.doc.capture_target()
        indicator = self.doc.status_indicator(
            status or _("LibreCompass: waiting for the model ({model}) …")
            .format(model=self.settings.model))

        def work():
            return self.client.generate(prompt)

        def done(result, error):
            if error is not None:
                dialogs.error(self.ctx, str(error))
                return
            if not result:
                return
            if on_result is not None:
                on_result(result)
                return
            self.write_result(target, result, mode)

        return async_task.run(self.ctx, work, done, indicator=indicator,
                              label=status or "")

    def write_result(self, target, text, mode="replace"):
        if not self.doc.write_target(
                target, text, mode=mode,
                track_changes=bool(self.settings.track_changes)):
            dialogs.info(self.ctx,
                         _("Applying is not supported in this module."))

    # ---- Schnittstelle ------------------------------------------------------
    def execute(self):
        raise NotImplementedError
