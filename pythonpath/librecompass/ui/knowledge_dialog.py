# -*- coding: utf-8 -*-
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at https://www.apache.org/licenses/LICENSE-2.0
"""Dialog zur Verwaltung der Wissensdatenbank.

Quellen hinzufügen (Datei oder Ordner), entfernen, Index neu aufbauen oder
leeren. Indexierung läuft synchron mit Fortschritt in der Statusleiste –
sie ist ein bewusster, seltener Vorgang.
"""
import os

import unohelper
from com.sun.star.awt import XActionListener

from librecompass import main_thread
from librecompass.i18n import gettext as _
from librecompass.rag import index as rag_index
from librecompass.ui import dialogs


class _Listener(unohelper.Base, XActionListener):
    def __init__(self, handler):
        self.handler = handler

    def actionPerformed(self, event):
        self.handler(event.ActionCommand)

    def disposing(self, event):
        pass


def open_dialog(ctx, settings, client, doc=None):
    KnowledgeDialog(ctx, settings, client, doc).run()


class KnowledgeDialog(object):
    WIDTH = 340
    HEIGHT = 214

    def __init__(self, ctx, settings, client, doc=None):
        self.ctx = ctx
        self.settings = settings
        self.client = client
        self.doc = doc
        self.busy = False
        self.builder = dialogs.DialogBuilder(
            ctx, _("LibreCompass – Knowledge base"), self.WIDTH, self.HEIGHT)
        self.controls = {}
        self._build()

    def _build(self):
        builder = self.builder
        c = self.controls
        builder.label(8, 6, 320, _("Indexed sources:"))
        c["sources"] = builder.listbox(8, 18, 324, (), dropdown=False,
                                       height=104)
        c["stats"] = builder.label(8, 126, 324, "")
        c["add_file"] = builder.push_button(8, 140, 80, _("Add file …"))
        c["add_folder"] = builder.push_button(92, 140, 84, _("Add folder …"))
        c["remove"] = builder.push_button(180, 140, 70, _("Remove"))
        c["rebuild"] = builder.push_button(8, 158, 100, _("Rebuild index"))
        c["clear"] = builder.push_button(112, 158, 80, _("Clear index"))
        c["close"] = builder.push_button(self.WIDTH - 74, 190, 66, _("Close"))

        self.dialog = builder.dialog
        self.dialog.setModel(builder.model)
        self.dialog.createPeer(dialogs._toolkit(self.ctx), None)
        listener = _Listener(self.handle)
        for key in ("add_file", "add_folder", "remove", "rebuild", "clear",
                    "close"):
            control = self.dialog.getControl(c[key])
            control.setActionCommand(key)
            control.addActionListener(listener)
        self._refresh()

    def run(self):
        try:
            self.dialog.execute()
        finally:
            self.builder.close()

    # ---- Anzeige -----------------------------------------------------------
    def _model_of(self, key):
        return self.dialog.getControl(self.controls[key]).getModel()

    def _refresh(self):
        store = rag_index.load_store(self.settings)
        sources = store.sources()
        model = self._model_of("sources")
        model.StringItemList = tuple(
            "%s  (%s)" % (os.path.basename(path), path) for path in sources)
        if sources:
            model.SelectedItems = (0,)
        self._sources = sources
        stats = store.stats()
        if stats["chunks"]:
            text = _("{chunks} chunks from {sources} sources, embedding "
                     "model {model}").format(**stats)
        else:
            text = _("The index is empty.")
        self._model_of("stats").Label = text

    def _selected_source(self):
        items = self._model_of("sources").SelectedItems
        if not items or not self._sources:
            return None
        position = int(items[0])
        if 0 <= position < len(self._sources):
            return self._sources[position]
        return None

    # ---- Aktionen ------------------------------------------------------------
    def handle(self, command):
        try:
            handler = getattr(self, "_on_" + command, None)
            if handler is not None:
                handler()
        except Exception as exc:
            dialogs.error(self.ctx, str(exc))

    def _on_close(self):
        self.dialog.endExecute()

    def _on_add_file(self):
        self._add(_("Path of the file or folder to index:"))

    def _on_add_folder(self):
        self._add(_("Path of the file or folder to index:"))

    def _add(self, label):
        path = dialogs.input_dialog(self.ctx, _("Add file …"), label)
        if not path:
            return
        path = os.path.expanduser(path.strip())
        if not os.path.exists(path):
            dialogs.error(self.ctx, path)
            return
        self._index([path])

    def _on_remove(self):
        source = self._selected_source()
        if source is None:
            return
        rag_index.remove_source(self.settings, source)
        self._refresh()

    def _on_rebuild(self):
        sources = list(self._sources)
        if not sources:
            dialogs.info(self.ctx, _("The index is empty."))
            return
        rag_index.clear(self.settings)
        self._index(sources)

    def _on_clear(self):
        rag_index.clear(self.settings)
        self._refresh()

    def _index(self, paths):
        """Im Hintergrund indexieren; Fortschritt in die Beschriftung."""
        if self.busy:
            return
        self.busy = True
        self._enable_buttons(False)
        self._model_of("stats").Label = _("Indexing …")

        def progress(number, total, path):
            text = "%s %d/%d – %s" % (_("Indexing …"), number, total,
                                      os.path.basename(path))
            main_thread.run_on_main(
                self.ctx,
                lambda label=text: self._set_stats(label))

        def worker():
            result, failure = None, None
            try:
                result = rag_index.index_paths(
                    self.settings, self.client, paths, ctx=self.ctx,
                    progress=progress)
            except Exception as exc:
                failure = exc
            main_thread.run_on_main(
                self.ctx, lambda: self._indexing_done(result, failure))

        threading.Thread(target=worker, daemon=True).start()

    def _set_stats(self, text):
        try:
            self._model_of("stats").Label = text
        except Exception:
            pass

    def _enable_buttons(self, enabled):
        for key in ("add_file", "add_folder", "remove", "rebuild", "clear"):
            try:
                self._model_of(key).Enabled = bool(enabled)
            except Exception:
                pass

    def _indexing_done(self, result, failure):
        self.busy = False
        self._enable_buttons(True)
        self._refresh()
        if failure is not None:
            dialogs.error(self.ctx, str(failure))
            return
        chunks, _files, errors = result
        if chunks:
            message = _("Indexed {count} chunks.").format(count=chunks)
        else:
            message = _("Nothing to index – no readable text found.")
        if errors:
            details = "\n".join("%s: %s" % (os.path.basename(path), reason)
                                for path, reason in errors[:10])
            message += "\n\n" + details
        dialogs.info(self.ctx, message)
