# -*- coding: utf-8 -*-
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at https://www.apache.org/licenses/LICENSE-2.0
"""Dokumentanalyse: harte Kennzahlen plus Einschätzung des Modells.

Die Kennzahlen kommen aus UNO (nachprüfbar), die Beobachtungen aus dem
Modell. Ergebnis ist ein neues Writer-Dokument - das analysierte Dokument
bleibt unangetastet.
"""
from librecompass.ai import prompts
from librecompass.commands.base import Command
from librecompass.i18n import gettext as _
from librecompass.office import analysis
from librecompass.ui import dialogs


class AnalyzeCommand(Command):
    def execute(self):
        report = analysis.analyze(self.doc)
        structure = analysis.format_report(report)
        text = self.doc.get_document_text()
        if not text.strip():
            dialogs.info(self.ctx, _("The document is empty."))
            return
        limit = int(self.settings.max_context_chars)
        excerpt = text[:limit]
        prompt = "%s\n\n%s:\n%s\n\nTEXT:\n\"\"\"\n%s\n\"\"\"" % (
            prompts.instruction("analysis"), _("Structure"), structure,
            excerpt)
        def apply_result(observations):
            document = "%s\n\n%s\n%s\n\n%s\n%s\n" % (
                _("Document analysis"), _("Structure"), structure,
                _("Observations"), observations)
            self.doc.new_document_with_text(document)

        self.ask_model_raw(prompt, status=_("Analyzing document …"),
                           on_result=apply_result)
