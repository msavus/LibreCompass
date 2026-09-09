# -*- coding: utf-8 -*-
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at https://www.apache.org/licenses/LICENSE-2.0
"""Kontextmenü einrichten bzw. entfernen.

Zwei Wege gleichzeitig: dauerhaft in der Modulkonfiguration (überlebt den
Neustart, unabhängig von Job und Listener) und sofort im laufenden
Dokument über den Interceptor.
"""
from librecompass.commands.base import Command
from librecompass.i18n import gettext as _
from librecompass.office import context_config
from librecompass.ui import context_menu, dialogs


class InstallContextMenuCommand(Command):
    needs_document = False

    def execute(self):
        changed, errors = context_config.install(self.ctx)
        # Zusätzlich sofort im laufenden Dokument aktivieren.
        context_menu.attach_global_listener(self.ctx)
        active = False
        if self.doc.model is not None:
            context_menu.register_for_model(self.doc.model)
            active = context_menu.is_registered_for(self.doc.model)

        lines = [context_config.summary(changed, errors)]
        if active:
            lines.append(_("Also active in the current document."))
        elif context_menu.last_error():
            lines.append("")
            lines.append("%s %s" % (_("Interceptor:"),
                                    context_menu.last_error()))
        if changed:
            lines.append("")
            lines.append(_("Right-click in a document to use it. In already "
                           "open documents it may take a restart."))
        dialogs.message_box(
            self.ctx, _("LibreCompass"), "\n".join(lines),
            "errorbox" if errors and not changed else "infobox")


class RemoveContextMenuCommand(Command):
    needs_document = False

    def execute(self):
        removed = context_config.remove(self.ctx)
        dialogs.info(self.ctx,
                     _("{count} context menu entries removed.")
                     .format(count=removed))
