# -*- coding: utf-8 -*-
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at https://www.apache.org/licenses/LICENSE-2.0
"""Das LibreCompass-Panel: nicht-modales Fenster mit dem Sidebar-Layout.

Setzt die Versionen 0.2/0.3 um (Modellauswahl, Streaming, Konfiguration,
Chat, Promptbibliothek, Verlauf) und ergänzt in 1.0 die Wissensdatenbank
als Kontextquelle sowie den Zugang zu Plug-ins.

Bewusst als nicht-modaler AWT-Dialog statt echter Sidebar
(XUIElementFactory + Sidebar.xcu) - gleiche Funktion bei einem Bruchteil
der Komplexität.

Threading-Regel: HTTP läuft im Worker-Thread, jede Änderung an Controls
oder am Dokument geht über main_thread.run_on_main() zurück auf den
Hauptthread.
"""
import threading
import time
import traceback

import unohelper
from com.sun.star.awt import XActionListener

from librecompass import main_thread
from librecompass.ai import history, prompts
from librecompass.ai.client import LLMClient, LLMError
from librecompass.config.settings import Settings
from librecompass.i18n import apply_settings as apply_language
from librecompass.i18n import gettext as _
from librecompass.office.document import OfficeDocument
from librecompass.rag import index as rag_index
from librecompass.ui import dialogs, knowledge_dialog, plugin_dialog

CONTEXT_SELECTION, CONTEXT_DOCUMENT, CONTEXT_KNOWLEDGE, CONTEXT_NONE = range(4)
MODE_REPLACE, MODE_INSERT, MODE_NEW = range(3)

_PANEL = None


def open_panel(ctx):
    """Panel öffnen bzw. das bestehende wieder anzeigen (Singleton)."""
    global _PANEL
    if _PANEL is not None:
        try:
            _PANEL.show()
            return
        except Exception:
            _PANEL = None
    _PANEL = Panel(ctx)
    _PANEL.show()


class _ButtonListener(unohelper.Base, XActionListener):
    def __init__(self, panel):
        self.panel = panel

    def actionPerformed(self, event):
        try:
            self.panel.handle_action(event.ActionCommand)
        except Exception:
            dialogs.error(self.panel.ctx, traceback.format_exc())

    def disposing(self, event):
        pass


class Panel(object):
    WIDTH = 304
    HEIGHT = 322

    def __init__(self, ctx):
        self.ctx = ctx
        self.settings = Settings.load(ctx)
        apply_language(ctx, self.settings)
        self.client = LLMClient(self.settings)
        self.library = []
        self.chat_messages = []
        self.last_response = ""
        self.last_sources = []
        self._busy = False
        self._stop = False
        self._controls = {}
        self._build()
        self._reload_library()
        self._load_models_async()

    # ---- Aufbau ------------------------------------------------------------
    def _build(self):
        builder = dialogs.DialogBuilder(self.ctx, _("LibreCompass"),
                                        self.WIDTH, self.HEIGHT)
        c = self._controls

        builder.label(8, 8, 34, _("Model:"))
        c["models"] = builder.listbox(44, 6, 210, (str(self.settings.model),))
        c["refresh"] = builder.push_button(258, 6, 38, "\u21bb")

        builder.label(8, 26, 34, _("Prompt:"))
        c["library"] = builder.listbox(44, 24, 150, ())
        c["insert_prompt"] = builder.push_button(198, 24, 50, _("Insert"))
        c["save_prompt"] = builder.push_button(252, 24, 44, _("Save"))
        c["prompt"] = builder.edit(8, 42, 288, height=42, multiline=True)

        builder.label(8, 90, 34, _("Context:"))
        c["context"] = builder.listbox(
            44, 88, 110,
            (_("Selection"), _("Whole document"), _("Knowledge base"),
             _("No context")),
            selected=CONTEXT_SELECTION)
        c["chat"] = builder.checkbox(162, 89, 134,
                                     _("Chat mode (keeps history)"), False)

        c["send"] = builder.push_button(8, 108, 64, _("Send"))
        c["stop"] = builder.push_button(76, 108, 48, _("Stop"))
        c["clear_chat"] = builder.push_button(128, 108, 74, _("Clear chat"))
        c["history"] = builder.push_button(206, 108, 90, _("History"))

        builder.label(8, 128, 100, _("Answer:"))
        c["response"] = builder.edit(8, 140, 288, height=112, multiline=True,
                                     readonly=True)

        builder.label(8, 260, 72, _("Apply as:"))
        c["mode"] = builder.listbox(
            82, 258, 120,
            (_("Replace selection"), _("Insert at cursor"), _("New document")),
            selected=MODE_REPLACE)
        c["apply"] = builder.push_button(208, 258, 88, _("Apply"))

        c["knowledge"] = builder.push_button(8, 280, 96,
                                             _("Knowledge base …"))
        c["plugins"] = builder.push_button(108, 280, 64, _("Plugins …"))
        c["settings"] = builder.push_button(176, 280, 76, _("Settings …"))
        c["close"] = builder.push_button(256, 280, 40, _("Close"))

        self.builder = builder
        self.dialog = builder.dialog
        self.dialog.setModel(builder.model)
        self.dialog.createPeer(dialogs._toolkit(self.ctx), None)

        listener = _ButtonListener(self)
        for command in ("refresh", "insert_prompt", "save_prompt", "send",
                        "stop", "clear_chat", "history", "apply",
                        "knowledge", "plugins", "settings", "close"):
            control = self.dialog.getControl(c[command])
            control.setActionCommand(command)
            control.addActionListener(listener)
        self._enable("stop", False)

    def show(self):
        self.dialog.setVisible(True)
        try:
            self.dialog.getPeer().toFront()
        except Exception:
            pass

    # ---- Control-Helfer ------------------------------------------------------
    def _model_of(self, key):
        return self.dialog.getControl(self._controls[key]).getModel()

    def _text(self, key):
        return self._model_of(key).Text

    def _set_text(self, key, value):
        self._model_of(key).Text = value

    def _checked(self, key):
        return self._model_of(key).State == 1

    def _selected(self, key):
        items = self._model_of(key).SelectedItems
        return int(items[0]) if items else 0

    def _set_items(self, key, items, selected=0):
        model = self._model_of(key)
        model.StringItemList = tuple(items)
        if items:
            model.SelectedItems = (int(selected),)

    def _enable(self, key, enabled):
        try:
            self._model_of(key).Enabled = bool(enabled)
        except Exception:
            pass

    # ---- Aktionen --------------------------------------------------------------
    def handle_action(self, command):
        handler = getattr(self, "handle_" + command, None)
        if handler is not None:
            handler()

    def handle_close(self):
        self.dialog.setVisible(False)

    def handle_settings(self):
        if dialogs.settings_dialog(self.ctx, self.settings):
            apply_language(self.ctx, self.settings)

    def handle_clear_chat(self):
        self.chat_messages = []
        self.last_response = ""
        self.last_sources = []
        self._set_text("response", "")

    def handle_insert_prompt(self):
        if not self.library:
            return
        index = self._selected("library")
        if 0 <= index < len(self.library):
            self._set_text("prompt", self.library[index].get("prompt", ""))

    def handle_save_prompt(self):
        prompt = self._text("prompt").strip()
        if not prompt:
            dialogs.info(self.ctx, _("No prompt to save."))
            return
        name = dialogs.input_dialog(self.ctx, _("Save prompt"),
                                    _("Name for the prompt library:"))
        if not name:
            return
        self.library = prompts.save_to_library(self.settings, name, prompt)
        self._reload_library(select_name=name)

    def handle_history(self):
        entries = history.load(self.settings)
        if not entries:
            dialogs.info(self.ctx, _("No history yet."))
            return
        newest_first = list(reversed(entries))
        index = dialogs.list_dialog(self.ctx, _("History"),
                                    [history.label(e) for e in newest_first])
        if index is None:
            return
        entry = newest_first[index]
        self._set_text("prompt", entry.get("prompt", ""))
        self.last_response = entry.get("response", "")
        self._set_text("response", self.last_response)

    def handle_knowledge(self):
        knowledge_dialog.open_dialog(self.ctx, self.settings, self.client,
                                     OfficeDocument(self.ctx))

    def handle_plugins(self):
        plugin_dialog.open_dialog(
            self.ctx, self.settings, OfficeDocument(self.ctx), self.client,
            on_prompt=lambda text: self._set_text("prompt", text))

    def handle_refresh(self):
        self._load_models_async()

    def handle_stop(self):
        self._stop = True

    def handle_apply(self):
        text = self.last_response.strip()
        if not text:
            dialogs.info(self.ctx, _("No answer to apply yet."))
            return
        mode = self._selected("mode")
        doc = OfficeDocument(self.ctx)
        track = bool(self.settings.track_changes)
        if mode == MODE_NEW:
            doc.new_document_with_text(text)
            return
        if mode == MODE_REPLACE:
            ok = doc.replace_selection(text, track_changes=track)
        else:
            ok = doc.insert_at_cursor(text, track_changes=track)
        if not ok:
            dialogs.info(self.ctx, _("Applying is not supported in this "
                                     "module – please use the \"New "
                                     "document\" mode."))

    # ---- Senden / Streaming ------------------------------------------------------
    def handle_send(self):
        if self._busy:
            return
        prompt_text = self._text("prompt").strip()
        if not prompt_text:
            dialogs.info(self.ctx, _("Please enter a prompt first."))
            return
        model_index = self._selected("models")
        model_items = self._model_of("models").StringItemList
        if model_items and 0 <= model_index < len(model_items):
            self.settings.data["model"] = str(model_items[model_index])
            self.settings.save()

        doc = OfficeDocument(self.ctx)
        context_choice = self._selected("context")
        chat_mode = self._checked("chat")
        # Dokumenttext MUSS auf dem Hauptthread gelesen werden; die Einbettung
        # der Frage und die Suche in der Wissensdatenbank sind HTTP-Aufrufe
        # und gehören deshalb in den Worker.
        document_context = self._context_text(doc, context_choice)

        if chat_mode:
            existing = self._text("response")
            base_text = (existing + "\n\n" if existing.strip() else "")
            base_text += "%s\n%s\n\n%s\n" % (_("You:"), prompt_text,
                                             _("Assistant:"))
        else:
            base_text = ""
        self._set_text("response", base_text)

        self._busy = True
        self._stop = False
        self._enable("send", False)
        self._enable("stop", True)
        worker = threading.Thread(
            target=self._worker,
            args=(prompt_text, context_choice, chat_mode, base_text,
                  document_context),
            daemon=True)
        worker.start()

    def _build_messages(self, prompt_text, context_choice, chat_mode,
                        document_context):
        """Nachrichten aufbauen. Läuft im Worker-Thread - hier darf kein
        Dokument- oder Control-Zugriff mehr stattfinden."""
        sources = []
        if context_choice == CONTEXT_KNOWLEDGE:
            hits = rag_index.retrieve(self.settings, self.client, prompt_text)
            if not hits:
                raise LLMError(_("The knowledge base is empty. Please index "
                                 "sources first."))
            context, sources = rag_index.build_context(
                hits, max_chars=int(self.settings.max_context_chars))
            messages = prompts.build_rag_messages(prompt_text, context)
            if chat_mode and self.chat_messages:
                return self.chat_messages + [messages[-1]], sources
            if chat_mode:
                self.chat_messages = [messages[0]]
            return messages, sources
        if chat_mode:
            if not self.chat_messages:
                self.chat_messages = [
                    self._system_message(document_context)]
            return (self.chat_messages
                    + [{"role": "user", "content": prompt_text}], sources)
        if document_context:
            return ([{"role": "user",
                      "content": prompts.build_prompt(prompt_text,
                                                      document_context)}],
                    sources)
        return [{"role": "user", "content": prompt_text}], sources

    def _system_message(self, document_context):
        parts = [prompts.instruction("chat_system")]
        if document_context:
            parts.append(prompts.instruction("document_context")
                         + "\n\"\"\"\n" + document_context + "\n\"\"\"")
        return {"role": "system", "content": "\n\n".join(parts)}

    def _context_text(self, doc, choice):
        if choice in (CONTEXT_NONE, CONTEXT_KNOWLEDGE) or not doc.is_supported():
            return ""
        if choice == CONTEXT_SELECTION:
            return doc.get_selection().strip()
        text = doc.get_document_text()
        limit = int(self.settings.max_context_chars)
        if len(text) > limit:
            text = text[:limit] + "\n[… …]"
        return text.strip()

    def _worker(self, prompt_text, context_choice, chat_mode, base_text,
                document_context):
        chunks = []
        last_push = [0.0]

        def on_delta(delta):
            chunks.append(delta)
            now = time.time()
            if now - last_push[0] >= 0.2:
                last_push[0] = now
                partial = "".join(chunks)
                main_thread.run_on_main(
                    self.ctx,
                    lambda text=base_text + partial:
                        self._set_text("response", text))

        error = None
        reply = ""
        sources = []
        try:
            messages, sources = self._build_messages(
                prompt_text, context_choice, chat_mode, document_context)
            if bool(self.settings.stream):
                reply = self.client.stream_chat(
                    messages, on_delta, should_stop=lambda: self._stop)
            else:
                reply = self.client.chat(messages)
        except LLMError as exc:
            error = str(exc)
        except Exception:
            error = traceback.format_exc()
        main_thread.run_on_main(
            self.ctx,
            lambda: self._finish(prompt_text, reply, error, chat_mode,
                                 base_text, sources))

    def _finish(self, prompt_text, reply, error, chat_mode, base_text,
                sources=()):
        self._busy = False
        self._enable("send", True)
        self._enable("stop", False)
        if error is not None:
            dialogs.error(self.ctx, error)
            return
        self.last_sources = list(sources)
        self.last_response = reply
        display = base_text + reply
        if self.last_sources:
            display += "\n\n%s\n%s" % (_("Sources used:"),
                                       "\n".join(self.last_sources))
        self._set_text("response", display)
        if chat_mode:
            self.chat_messages.append({"role": "user",
                                       "content": prompt_text})
            self.chat_messages.append({"role": "assistant",
                                       "content": reply})
        history.add(self.settings, "Chat" if chat_mode else "Prompt",
                    prompt_text, reply, str(self.settings.model))

    # ---- Modelle / Bibliothek ------------------------------------------------------
    def _reload_library(self, select_name=None):
        self.library = prompts.load_library(self.settings)
        names = [entry.get("name", "?") for entry in self.library]
        selected = 0
        if select_name and select_name in names:
            selected = names.index(select_name)
        self._set_items("library", names, selected)

    def _load_models_async(self):
        def worker():
            try:
                models = self.client.models()
            except Exception:
                models = []
            main_thread.run_on_main(self.ctx,
                                    lambda: self._fill_models(models))

        threading.Thread(target=worker, daemon=True).start()

    def _fill_models(self, models):
        current = str(self.settings.model)
        if not models:
            models = [current]
        selected = models.index(current) if current in models else 0
        self._set_items("models", models, selected)
