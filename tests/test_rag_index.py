# -*- coding: utf-8 -*-
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at https://www.apache.org/licenses/LICENSE-2.0
"""Indexierung und Retrieval mit einer Modell-Attrappe."""
import os
import unittest

import context  # noqa: F401
from fakes import FakeClient
from helpers import TempSettings, write_file

from librecompass.rag import index as rag_index


class RagIndexTest(unittest.TestCase):
    def setUp(self):
        self.settings = TempSettings(chunk_size=200, chunk_overlap=0,
                                     rag_top_k=3)
        self.client = FakeClient()
        self.docs = os.path.join(self.settings.directory, "docs")
        os.makedirs(self.docs, exist_ok=True)

    def tearDown(self):
        self.settings.cleanup()

    def _write(self, name, content):
        return write_file(self.docs, name, content)

    def test_index_and_retrieve(self):
        self._write("compass.txt",
                    "The compass gives direction. The helm stays with you.")
        self._write("ollama.txt",
                    "Ollama serves local models over an HTTP endpoint.")
        chunks, files, errors = rag_index.index_paths(
            self.settings, self.client, [self.docs])
        self.assertEqual(files, 2)
        self.assertGreaterEqual(chunks, 2)
        self.assertEqual(errors, [])
        hits = rag_index.retrieve(self.settings, self.client,
                                  "Which endpoint serves local models?")
        self.assertTrue(hits)
        texts = " ".join(hit["text"] for _score, hit in hits)
        self.assertIn("Ollama", texts)

    def test_sources_are_remembered(self):
        path = self._write("a.txt", "content one")
        rag_index.index_paths(self.settings, self.client, [path])
        self.assertEqual(self.settings.data["knowledge_sources"], [path])

    def test_reindexing_does_not_duplicate(self):
        path = self._write("a.txt", "content one")
        first, _f, _e = rag_index.index_paths(self.settings, self.client,
                                              [path])
        second, _f, _e = rag_index.index_paths(self.settings, self.client,
                                               [path])
        store = rag_index.load_store(self.settings)
        self.assertEqual(first, second)
        self.assertEqual(len(store.chunks), first)

    def test_unreadable_file_is_reported(self):
        path = self._write("empty.txt", "   ")
        chunks, files, errors = rag_index.index_paths(
            self.settings, self.client, [path])
        self.assertEqual(chunks, 0)
        self.assertEqual(files, 0)
        self.assertEqual(len(errors), 1)

    def test_changing_embedding_model_resets_index(self):
        path = self._write("a.txt", "content one")
        rag_index.index_paths(self.settings, self.client, [path])
        self.settings.data["embedding_model"] = "other-model"
        other = FakeClient(dimension=12)
        rag_index.index_paths(self.settings, other, [path])
        store = rag_index.load_store(self.settings)
        self.assertEqual(store.model, "other-model")
        self.assertEqual(store.dimension, 12)

    def test_remove_and_clear(self):
        path = self._write("a.txt", "content one")
        rag_index.index_paths(self.settings, self.client, [path])
        rag_index.remove_source(self.settings, path)
        self.assertEqual(rag_index.load_store(self.settings).sources(), [])
        rag_index.index_paths(self.settings, self.client, [path])
        rag_index.clear(self.settings)
        self.assertEqual(rag_index.load_store(self.settings).chunks, [])

    def test_retrieve_on_empty_index(self):
        self.assertEqual(
            rag_index.retrieve(self.settings, self.client, "question"), [])

    def test_build_context_labels_sources(self):
        path = self._write("guide.txt", "The helm stays with the user.")
        rag_index.index_paths(self.settings, self.client, [path])
        hits = rag_index.retrieve(self.settings, self.client, "helm")
        text, sources = rag_index.build_context(hits)
        self.assertIn("guide.txt", text)
        self.assertIn(path, sources)

    def test_build_context_respects_limit(self):
        for number in range(5):
            self._write("f%d.txt" % number, "word " * 80)
        rag_index.index_paths(self.settings, self.client, [self.docs])
        hits = rag_index.retrieve(self.settings, self.client, "word",
                                  top_k=5)
        text, _sources = rag_index.build_context(hits, max_chars=200)
        self.assertLessEqual(len(text), 250)

    def test_progress_callback(self):
        self._write("a.txt", "content")
        seen = []
        rag_index.index_paths(self.settings, self.client, [self.docs],
                              progress=lambda n, total, path: seen.append(n))
        self.assertEqual(seen, [1])


if __name__ == "__main__":
    unittest.main()
