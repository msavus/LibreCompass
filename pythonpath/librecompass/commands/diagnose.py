# -*- coding: utf-8 -*-
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at https://www.apache.org/licenses/LICENSE-2.0
"""Diagnose- und Reparaturbefehle für Menü, Kürzel und Kontextmenü."""
from librecompass.commands.base import Command
from librecompass.i18n import gettext as _
from librecompass.office import diagnostics
from librecompass.ui import dialogs


class DiagnoseCommand(Command):
    needs_document = False

    def execute(self):
        facts = diagnostics.collect(self.ctx, self.doc,
                                    self.settings)
        dialogs.message_box(self.ctx, _("LibreCompass – Diagnostics"),
                            diagnostics.build_report(facts), "infobox")
