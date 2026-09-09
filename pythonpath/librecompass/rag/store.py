# -*- coding: utf-8 -*-
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at https://www.apache.org/licenses/LICENSE-2.0
"""Vektorindex als JSON-Datei, Kosinus-Suche in reinem Python.

Bewusst ohne ChromaDB/FAISS: Das in LibreOffice eingebettete Python bringt
kein pip mit, und C-Extensions gegen die LO-Python-ABI sind unpraktikabel.
Für persönliche Wissensbestände (Größenordnung: einige tausend Abschnitte)
ist eine lineare Suche in Python völlig ausreichend – bei 5000 Abschnitten
à 768 Dimensionen liegt eine Abfrage im Bereich weniger Zehntelsekunden.

Wächst der Bestand darüber hinaus, gehört der Index in einen externen
lokalen Dienst; ``search()`` bleibt dabei die Schnittstelle.
"""
import json
import math
import os

FORMAT_VERSION = 1


class KnowledgeStore(object):
    def __init__(self, path):
        self.path = path
        self.model = ""
        self.dimension = 0
        self.chunks = []

    # ---- Laden / Speichern -------------------------------------------------
    @classmethod
    def load(cls, path):
        store = cls(path)
        if not os.path.exists(path):
            return store
        try:
            with open(path, "r", encoding="utf-8") as handle:
                data = json.load(handle)
        except Exception:
            return store
        if not isinstance(data, dict):
            return store
        store.model = str(data.get("model", ""))
        store.dimension = int(data.get("dimension", 0) or 0)
        chunks = data.get("chunks")
        store.chunks = chunks if isinstance(chunks, list) else []
        return store

    def save(self):
        data = {
            "format": FORMAT_VERSION,
            "model": self.model,
            "dimension": self.dimension,
            "chunks": self.chunks,
        }
        directory = os.path.dirname(self.path)
        if directory:
            os.makedirs(directory, exist_ok=True)
        temporary = self.path + ".tmp"
        with open(temporary, "w", encoding="utf-8") as handle:
            json.dump(data, handle, ensure_ascii=False)
        os.replace(temporary, self.path)

    # ---- Inhalt ---------------------------------------------------------------
    def clear(self):
        self.chunks = []
        self.dimension = 0

    def remove_source(self, source):
        self.chunks = [chunk for chunk in self.chunks
                       if chunk.get("source") != source]

    def sources(self):
        ordered = []
        for chunk in self.chunks:
            source = chunk.get("source", "")
            if source and source not in ordered:
                ordered.append(source)
        return ordered

    def add(self, source, title, texts, vectors, model):
        """Abschnitte einer Quelle aufnehmen (ersetzt vorhandene Einträge)."""
        if len(texts) != len(vectors):
            raise ValueError("Anzahl Texte und Vektoren stimmt nicht überein.")
        if not vectors:
            return 0
        dimension = len(vectors[0])
        if self.chunks and self.dimension and dimension != self.dimension:
            raise ValueError(
                "Embedding-Dimension %d passt nicht zum Index (%d). "
                "Bitte den Index neu aufbauen." % (dimension, self.dimension))
        self.remove_source(source)
        for position, (text, vector) in enumerate(zip(texts, vectors)):
            self.chunks.append({
                "source": source,
                "title": title,
                "position": position,
                "text": text,
                "norm": _norm(vector),
                "vector": [round(float(value), 6) for value in vector],
            })
        self.model = model
        self.dimension = dimension
        return len(texts)

    # ---- Suche -------------------------------------------------------------------
    def search(self, vector, top_k=5):
        """Ähnlichste Abschnitte liefern: Liste von (score, chunk)."""
        if not self.chunks:
            return []
        query_norm = _norm(vector)
        if query_norm == 0.0:
            return []
        scored = []
        for chunk in self.chunks:
            candidate = chunk.get("vector") or []
            if len(candidate) != len(vector):
                continue
            norm = chunk.get("norm") or _norm(candidate)
            if not norm:
                continue
            dot = 0.0
            for left, right in zip(vector, candidate):
                dot += left * right
            scored.append((dot / (query_norm * norm), chunk))
        scored.sort(key=lambda item: item[0], reverse=True)
        return scored[:max(1, int(top_k))]

    def stats(self):
        return {
            "chunks": len(self.chunks),
            "sources": len(self.sources()),
            "model": self.model or "-",
            "dimension": self.dimension,
        }


def _norm(vector):
    total = 0.0
    for value in vector:
        total += float(value) * float(value)
    return math.sqrt(total)
