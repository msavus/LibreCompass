# -*- coding: utf-8 -*-
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at https://www.apache.org/licenses/LICENSE-2.0
from librecompass.ai import prompts
from librecompass.commands.base import Command


class ImproveCommand(Command):
    def execute(self):
        text = self.require_selection()
        if text is None:
            return
        self.ask_model(prompts.instruction("improve"), text)
