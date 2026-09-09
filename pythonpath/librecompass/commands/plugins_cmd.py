# -*- coding: utf-8 -*-
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at https://www.apache.org/licenses/LICENSE-2.0
from librecompass.commands.base import Command
from librecompass.ui import plugin_dialog


class PluginsCommand(Command):
    needs_document = False

    def execute(self):
        plugin_dialog.open_dialog(self.ctx, self.settings, self.doc,
                                  self.client)
