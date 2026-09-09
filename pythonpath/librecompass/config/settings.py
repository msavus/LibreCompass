# -*- coding: utf-8 -*-
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at https://www.apache.org/licenses/LICENSE-2.0
"""Einstellungen als JSON-Datei im LibreOffice-Benutzerprofil.

Ablage: ``<Profil>/user/librecompass/settings.json`` (über die
PathSubstitution-Variable ``$(user)``), Fallback ``~/.config/librecompass``.
Daneben liegen ``prompts.json``, ``history.json``, ``knowledge.json``
sowie das Verzeichnis ``plugins/``.
"""
import json
import os

import uno

DEFAULTS = {
    # Ein OpenAI-kompatibler Endpoint deckt alle geplanten Backends ab:
    #   Ollama        http://localhost:11434/v1
    #   llama-server  http://localhost:8080/v1
    #   LM Studio     http://localhost:1234/v1
    #   vLLM          http://localhost:8000/v1
    "base_url": "http://localhost:11434/v1",
    "api_key": "",
    "model": "qwen3",
    "temperature": 0.3,
    "max_tokens": 4096,
    "timeout_seconds": 300,
    # KI-Ersetzungen als nachverfolgte Änderungen (Bearbeiten > Änderungen)
    # einfügen, damit jede Änderung revidierbar bleibt.
    "track_changes": False,
    # Streaming im Panel; bei Problemen auf False setzen (dann synchron).
    "stream": True,
    # Zeichenlimit für "Gesamtes Dokument" als Kontext (Chat/Prompt).
    "max_context_chars": 24000,
    # "auto" folgt dem UI-Gebietsschema von LibreOffice; sonst "en"/"de".
    "language": "auto",
    # Wissensdatenbank (RAG)
    "embedding_model": "nomic-embed-text",
    "chunk_size": 1200,
    "chunk_overlap": 150,
    "rag_top_k": 5,
    "max_index_file_chars": 400000,
    "knowledge_sources": [],
}

CONFIG_FILENAME = "settings.json"
PROMPTS_FILENAME = "prompts.json"
KNOWLEDGE_FILENAME = "knowledge.json"
PLUGINS_DIRNAME = "plugins"


def config_dir(ctx):
    """Konfigurationsverzeichnis ermitteln und anlegen."""
    try:
        smgr = ctx.ServiceManager
        substitution = smgr.createInstanceWithContext(
            "com.sun.star.util.PathSubstitution", ctx)
        url = substitution.substituteVariables("$(user)", True)
        base = uno.fileUrlToSystemPath(url)
    except Exception:
        base = os.path.join(os.path.expanduser("~"), ".config")
    path = os.path.join(base, "librecompass")
    os.makedirs(path, exist_ok=True)
    return path


class Settings(object):
    """Einstellungen mit Attributzugriff (``settings.model`` usw.)."""

    def __init__(self, data, directory):
        self.directory = directory
        self.data = dict(DEFAULTS)
        self.data.update(data or {})

    @classmethod
    def load(cls, ctx):
        directory = config_dir(ctx)
        path = os.path.join(directory, CONFIG_FILENAME)
        data = {}
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as handle:
                    data = json.load(handle)
            except Exception:
                data = {}
        settings = cls(data, directory)
        if not os.path.exists(path):
            settings.save()
        return settings

    def save(self):
        path = os.path.join(self.directory, CONFIG_FILENAME)
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(self.data, handle, ensure_ascii=False, indent=2)

    # ---- abgeleitete Pfade -------------------------------------------------
    def prompts_path(self):
        return os.path.join(self.directory, PROMPTS_FILENAME)

    def knowledge_path(self):
        return os.path.join(self.directory, KNOWLEDGE_FILENAME)

    def plugins_dir(self):
        path = os.path.join(self.directory, PLUGINS_DIRNAME)
        try:
            os.makedirs(path, exist_ok=True)
        except Exception:
            pass
        return path

    def __getattr__(self, name):
        try:
            data = object.__getattribute__(self, "data")
        except AttributeError:
            raise AttributeError(name)
        try:
            return data[name]
        except KeyError:
            raise AttributeError(name)
