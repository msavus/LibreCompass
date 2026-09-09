# -*- coding: utf-8 -*-
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at https://www.apache.org/licenses/LICENSE-2.0
from librecompass.ai import prompts
from librecompass.commands.base import Command
from librecompass.i18n import gettext as _
from librecompass.ui import dialogs


class SummarizeCommand(Command):
    def execute(self):
        instruction = prompts.instruction("summarize")
        selection = self.doc.get_selection()
        if selection.strip():
            self.ask_model(instruction, selection)
            return
        # Keine Auswahl: gesamtes Dokument zusammenfassen und einfügen.
        text = self.doc.get_document_text()
        if not text.strip():
            dialogs.info(self.ctx, _("The document is empty."))
            return
        target = self.doc.capture_target()

        def apply_result(result):
            self.write_result(target, "\n\n%s\n%s\n" % (_("Summary:"), result),
                              mode="insert")

        self.ask_model_raw(prompts.build_prompt(instruction, text),
                           on_result=apply_result)
