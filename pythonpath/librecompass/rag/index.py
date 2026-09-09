# -*- coding: utf-8 -*-
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at https://www.apache.org/licenses/LICENSE-2.0
"""Wissensdatenbank: Indexieren und Abrufen.

Ablauf beim Indexieren: Datei(en) einsammeln → Text extrahieren →
Abschnitte bilden → Embeddings über ``/v1/embeddings`` holen → in
``knowledge.json`` ablegen. Beim Abrufen wird die Frage eingebettet und
per Kosinus-Ähnlichkeit gegen den Index gesucht.
"""
import os

from librecompass.office import extract
from librecompass.rag import chunk as chunker
from librecompass.rag.store import KnowledgeStore

BATCH_SIZE = 16


def load_store(settings):
    return KnowledgeStore.load(settings.knowledge_path())


def index_paths(settings, client, paths, ctx=None, progress=None):
    """Dateien/Ordner indexieren; liefert (Abschnitte, Dateien, Fehlerliste)."""
    store = load_store(settings)
    model = str(settings.embedding_model)
    if store.chunks and store.model and store.model != model:
        # Vektoren verschiedener Modelle sind nicht vergleichbar.
        store.clear()
    files = []
    for path in paths:
        files.extend(extract.collect_files(path))
    seen = set()
    ordered = []
    for path in files:
        key = os.path.abspath(path)
        if key not in seen:
            seen.add(key)
            ordered.append(key)

    total_chunks = 0
    indexed_files = 0
    errors = []
    for number, path in enumerate(ordered, start=1):
        if progress is not None:
            progress(number, len(ordered), path)
        text = extract.extract_text(
            path, ctx=ctx, limit=int(settings.max_index_file_chars))
        if not text:
            errors.append((path, "kein lesbarer Text"))
            continue
        pieces = chunker.split_text(text, size=int(settings.chunk_size),
                                    overlap=int(settings.chunk_overlap))
        if not pieces:
            continue
        try:
            vectors = _embed_all(client, pieces, model)
        except Exception as exc:
            errors.append((path, str(exc)))
            continue
        total_chunks += store.add(path, os.path.basename(path), pieces,
                                  vectors, model)
        indexed_files += 1
    store.save()
    _remember_sources(settings, store)
    return total_chunks, indexed_files, errors


def _embed_all(client, texts, model):
    vectors = []
    for start in range(0, len(texts), BATCH_SIZE):
        batch = texts[start:start + BATCH_SIZE]
        vectors.extend(client.embeddings(batch, model=model))
    return vectors


def _remember_sources(settings, store):
    settings.data["knowledge_sources"] = store.sources()
    try:
        settings.save()
    except Exception:
        pass


def remove_source(settings, source):
    store = load_store(settings)
    store.remove_source(source)
    store.save()
    _remember_sources(settings, store)
    return store


def clear(settings):
    store = load_store(settings)
    store.clear()
    store.save()
    _remember_sources(settings, store)
    return store


def retrieve(settings, client, question, top_k=None):
    """Passende Abschnitte zur Frage liefern: Liste von (score, chunk)."""
    store = load_store(settings)
    if not store.chunks:
        return []
    vector = client.embeddings([question],
                               model=str(settings.embedding_model))[0]
    return store.search(vector, top_k or int(settings.rag_top_k))


def build_context(hits, max_chars=None):
    """Gefundene Abschnitte als Kontexttext mit Quellenangaben aufbereiten."""
    parts = []
    used = []
    total = 0
    for score, hit in hits:
        title = hit.get("title") or os.path.basename(hit.get("source", ""))
        block = "[%s #%s]\n%s" % (title, hit.get("position", 0) + 1,
                                  hit.get("text", ""))
        if max_chars and total + len(block) > int(max_chars):
            break
        parts.append(block)
        total += len(block)
        source = hit.get("source", "")
        if source and source not in used:
            used.append(source)
    return "\n\n".join(parts), used
