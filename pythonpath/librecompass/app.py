# -*- coding: utf-8 -*-
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at https://www.apache.org/licenses/LICENSE-2.0
"""Befehls-Router: von der UNO-Registrierung entkoppelt testbar."""
from librecompass.ai.client import LLMClient
from librecompass.commands.analyze import AnalyzeCommand
from librecompass.commands.custom_prompt import CustomPromptCommand
from librecompass.commands.context_cmd import (InstallContextMenuCommand,
                                                RemoveContextMenuCommand)
from librecompass.commands.diagnose import DiagnoseCommand
from librecompass.commands.shortcuts_cmd import (InstallShortcutsCommand,
                                                 RemoveShortcutsCommand)
from librecompass.commands.improve import ImproveCommand
from librecompass.commands.knowledge_cmd import KnowledgeCommand
from librecompass.commands.panel_cmd import PanelCommand
from librecompass.commands.plugins_cmd import PluginsCommand
from librecompass.commands.rewrite import RewriteCommand
from librecompass.commands.settings_cmd import SettingsCommand
from librecompass.commands.summarize import SummarizeCommand
from librecompass.commands.translate import TranslateCommand
from librecompass.config.settings import Settings
from librecompass.i18n import apply_settings as apply_language
from librecompass.i18n import gettext as _
from librecompass.office.document import OfficeDocument
from librecompass.ui import dialogs

COMMANDS = {
    "panel": PanelCommand,
    "improve": ImproveCommand,
    "rewrite": RewriteCommand,
    "summarize": SummarizeCommand,
    "translate": TranslateCommand,
    "custom": CustomPromptCommand,
    "analyze": AnalyzeCommand,
    "knowledge": KnowledgeCommand,
    "plugins": PluginsCommand,
    "installcontextmenu": InstallContextMenuCommand,
    "removecontextmenu": RemoveContextMenuCommand,
    "diagnose": DiagnoseCommand,
    "installshortcuts": InstallShortcutsCommand,
    "removeshortcuts": RemoveShortcutsCommand,
    "settings": SettingsCommand,
}


def run_command(ctx, name):
    settings = Settings.load(ctx)
    apply_language(ctx, settings)
    command_class = COMMANDS.get(name)
    if command_class is None:
        dialogs.error(ctx, _("Unknown command: {name}").format(name=name))
        return
    doc = OfficeDocument(ctx)
    # Selbstheilung: Kontextmenü spätestens ab der ersten Benutzung aktiv,
    # auch wenn der Startjob aus Jobs.xcu nicht gelaufen ist.
    try:
        from librecompass.ui import context_menu
        context_menu.ensure_active(ctx, doc.model)
    except Exception:
        pass
    if command_class.needs_document and not doc.is_supported():
        dialogs.info(ctx, _("Please open a document first (Writer, Calc, "
                            "Impress or Draw)."))
        return
    client = LLMClient(settings)
    command_class(ctx, doc, client, settings).execute()
