# -*- coding: utf-8 -*-
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at https://www.apache.org/licenses/LICENSE-2.0
"""Tastenkürzel einrichten bzw. entfernen (Accelerator-API)."""
from librecompass.commands.base import Command
from librecompass.i18n import gettext as _
from librecompass.office import shortcuts
from librecompass.ui import dialogs


class InstallShortcutsCommand(Command):
    needs_document = False

    def execute(self):
        applied, conflicts, errors = shortcuts.apply(self.ctx)
        from librecompass import runtime
        runtime.note(self.settings, shortcuts_applied=applied)
        dialogs.message_box(
            self.ctx, _("LibreCompass"),
            shortcuts.summary(applied, conflicts, errors),
            "errorbox" if errors and not applied else "infobox")


class RemoveShortcutsCommand(Command):
    needs_document = False

    def execute(self):
        removed = shortcuts.remove(self.ctx)
        from librecompass import runtime
        runtime.note(self.settings, shortcuts_applied=0)
        dialogs.info(self.ctx,
                     _("{count} shortcuts removed.").format(count=removed))
