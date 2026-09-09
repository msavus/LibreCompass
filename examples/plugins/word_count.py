# -*- coding: utf-8 -*-
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at https://www.apache.org/licenses/LICENSE-2.0
"""Beispiel-Plug-in: ausführbare Aktion ohne Modellaufruf."""
NAME = "Word count"
DESCRIPTION = "Counts words and characters in the selection or document"


def run(api):
    text = api.selection() or api.document_text()
    if not text.strip():
        api.message("Nothing to count.")
        return
    words = len(text.split())
    api.message("%d words, %d characters (module: %s)"
                % (words, len(text), api.module()))
