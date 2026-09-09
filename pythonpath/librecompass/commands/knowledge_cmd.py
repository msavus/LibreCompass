# -*- coding: utf-8 -*-
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at https://www.apache.org/licenses/LICENSE-2.0
from librecompass.commands.base import Command
from librecompass.ui import knowledge_dialog


class KnowledgeCommand(Command):
    # Die Wissensdatenbank ist unabhängig vom offenen Dokument nutzbar.
    needs_document = False

    def execute(self):
        knowledge_dialog.open_dialog(self.ctx, self.settings, self.client,
                                     self.doc)
