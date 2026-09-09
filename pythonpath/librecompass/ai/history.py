# -*- coding: utf-8 -*-
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at https://www.apache.org/licenses/LICENSE-2.0
"""Verlauf (Version 0.3): letzte Prompts/Antworten in history.json."""
import json
import os
import time

FILENAME = "history.json"
MAX_ENTRIES = 200


def _path(settings):
    return os.path.join(settings.directory, FILENAME)


def load(settings):
    path = _path(settings)
    if not os.path.exists(path):
        return []
    try:
        with open(path, "r", encoding="utf-8") as handle:
            entries = json.load(handle)
        if isinstance(entries, list):
            return entries
    except Exception:
        pass
    return []


def add(settings, kind, prompt, response, model):
    entries = load(settings)
    entries.append({
        "time": time.strftime("%Y-%m-%d %H:%M"),
        "kind": kind,
        "model": model,
        "prompt": prompt,
        "response": response,
    })
    entries = entries[-MAX_ENTRIES:]
    try:
        with open(_path(settings), "w", encoding="utf-8") as handle:
            json.dump(entries, handle, ensure_ascii=False, indent=2)
    except Exception:
        pass
    return entries


def label(entry):
    prompt = " ".join((entry.get("prompt") or "").split())
    if len(prompt) > 60:
        prompt = prompt[:57] + "…"
    return "%s | %s | %s" % (entry.get("time", "?"),
                             entry.get("kind", "?"), prompt)
