# -*- coding: utf-8 -*-
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at https://www.apache.org/licenses/LICENSE-2.0
"""Beispiel-Plug-in: Modellaufruf plus eigenes Ergebnisdokument.

Zeigt das übliche Muster: lesen -> fragen -> in ein neues Dokument
schreiben, damit das Original unangetastet bleibt.
"""
NAME = "Terminology check"
DESCRIPTION = "Lists inconsistent terms and suggests one variant each"

INSTRUCTION = (
    "List terms that are used inconsistently in the text below (spelling "
    "variants, synonyms for the same concept, mixed languages). For each, "
    "suggest one variant to standardize on. If everything is consistent, "
    "say so in one sentence.\n\nTEXT:\n\"\"\"\n%s\n\"\"\"")


def run(api):
    text = api.selection() or api.document_text()
    if not text.strip():
        api.message("Nothing to check.")
        return
    limit = int(api.setting("max_context_chars", 24000))
    result = api.ask(INSTRUCTION % text[:limit])
    api.new_document("Terminology check\n\n" + result)
