# -*- coding: utf-8 -*-
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at https://www.apache.org/licenses/LICENSE-2.0
from librecompass.commands.base import Command
from librecompass.i18n import gettext as _
from librecompass.ui import dialogs


class CustomPromptCommand(Command):
    def execute(self):
        instruction = dialogs.input_dialog(
            self.ctx, _("Custom prompt"),
            _("Instruction (applied to the selection; without a selection "
              "the answer is inserted):"),
            multiline=True)
        if not instruction:
            return
        selection = self.doc.get_selection()
        if selection.strip():
            self.ask_model(instruction, selection)
        else:
            self.ask_model_raw(instruction, mode="insert")
