# -*- coding: utf-8 -*-
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at https://www.apache.org/licenses/LICENSE-2.0
"""Dialog für installierte Plug-ins: ausführen oder Prompt übernehmen."""
import os

from librecompass import plugins as plugin_api
from librecompass.i18n import gettext as _
from librecompass.ui import dialogs


def open_dialog(ctx, settings, doc, client, on_prompt=None):
    """Plug-in-Dialog anzeigen.

    ``on_prompt`` erhält den Prompt-Text, wenn der Benutzer "Prompt
    einfügen" wählt (z. B. um ihn ins Panel zu übernehmen).
    """
    found = plugin_api.discover(settings)
    directory = settings.plugins_dir()
    if not found:
        dialogs.info(ctx, "%s\n%s" % (
            _("No plugins installed. Place .py files in:"), directory))
        return

    builder = dialogs.DialogBuilder(ctx, _("LibreCompass – Plugins"), 320, 190)
    builder.label(8, 6, 304, _("Installed plugins:"))
    listbox = builder.listbox(8, 18, 304, [item.label() for item in found],
                             dropdown=False, height=110)
    builder.label(8, 132, 304, directory)
    run_button = builder.push_button(8, 148, 80, _("Run"))
    prompt_button = builder.push_button(92, 148, 96, _("Insert prompt"))
    close_button = builder.push_button(320 - 74, 148, 66, _("Close"))

    dialog = builder.dialog
    dialog.setModel(builder.model)
    dialog.createPeer(dialogs._toolkit(ctx), None)

    def selected():
        items = dialog.getControl(listbox).getModel().SelectedItems
        if not items:
            return None
        position = int(items[0])
        return found[position] if 0 <= position < len(found) else None

    result = {"prompt": None}

    def handle(command):
        if command == "close":
            dialog.endExecute()
            return
        plugin = selected()
        if plugin is None:
            return
        if command == "prompt":
            if not plugin.has_prompt:
                dialogs.info(ctx, _("Plugin \"{name}\" has no prompt.").format(
                    name=plugin.name))
                return
            result["prompt"] = plugin.prompt
            dialog.endExecute()
            return
        if command == "close":
            dialog.endExecute()
            return
        if command == "run":
            if not plugin.is_runnable:
                dialogs.info(ctx, _("Plugin \"{name}\" is not runnable.")
                             .format(name=plugin.name))
                return
            api = plugin_api.PluginAPI(
                ctx, doc, client, settings,
                lambda text, title=None: dialogs.info(ctx, text))
            failure = plugin_api.run_plugin(plugin, api)
            if failure:
                dialogs.error(ctx, "%s\n\n%s"
                              % (os.path.basename(plugin.path), failure))
            dialog.endExecute()

    from librecompass.ui.knowledge_dialog import _Listener
    listener = _Listener(handle)
    for name, command in ((run_button, "run"), (prompt_button, "prompt"),
                          (close_button, "close")):
        control = dialog.getControl(name)
        control.setActionCommand(command)
        control.addActionListener(listener)

    try:
        dialog.execute()
    finally:
        builder.close()

    if result["prompt"] and on_prompt is not None:
        on_prompt(result["prompt"])
    return result["prompt"]
