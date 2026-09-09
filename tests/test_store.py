# -*- coding: utf-8 -*-
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at https://www.apache.org/licenses/LICENSE-2.0
import os
import shutil
import tempfile
import unittest

import context  # noqa: F401

from librecompass.rag.store import KnowledgeStore


class StoreTest(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.mkdtemp(prefix="librecompass-store-")
        self.path = os.path.join(self.directory, "knowledge.json")
        self.store = KnowledgeStore(self.path)

    def tearDown(self):
        shutil.rmtree(self.directory, ignore_errors=True)

    def _fill(self):
        self.store.add("/docs/a.txt", "a.txt", ["alpha", "beta"],
                       [[1.0, 0.0], [0.0, 1.0]], "embed")

    def test_empty_store(self):
        self.assertEqual(self.store.chunks, [])
        self.assertEqual(self.store.search([1.0, 0.0]), [])
        self.assertEqual(self.store.stats()["chunks"], 0)

    def test_add_and_stats(self):
        self.assertEqual(
            self.store.add("/docs/a.txt", "a.txt", ["x"], [[1.0, 0.0]],
                           "embed"), 1)
        stats = self.store.stats()
        self.assertEqual(stats["chunks"], 1)
        self.assertEqual(stats["sources"], 1)
        self.assertEqual(stats["model"], "embed")
        self.assertEqual(stats["dimension"], 2)

    def test_search_orders_by_similarity(self):
        self._fill()
        results = self.store.search([1.0, 0.0], top_k=2)
        self.assertEqual(results[0][1]["text"], "alpha")
        self.assertGreater(results[0][0], results[1][0])

    def test_search_respects_top_k(self):
        self._fill()
        self.assertEqual(len(self.store.search([1.0, 1.0], top_k=1)), 1)

    def test_zero_query_vector(self):
        self._fill()
        self.assertEqual(self.store.search([0.0, 0.0]), [])

    def test_dimension_mismatch_is_rejected(self):
        self._fill()
        with self.assertRaises(ValueError):
            self.store.add("/docs/b.txt", "b.txt", ["y"], [[1.0, 0.0, 0.0]],
                           "embed")

    def test_adding_same_source_replaces(self):
        self._fill()
        self.store.add("/docs/a.txt", "a.txt", ["gamma"], [[1.0, 1.0]],
                       "embed")
        self.assertEqual(len(self.store.chunks), 1)
        self.assertEqual(self.store.chunks[0]["text"], "gamma")

    def test_remove_source(self):
        self._fill()
        self.store.add("/docs/b.txt", "b.txt", ["delta"], [[1.0, 1.0]],
                       "embed")
        self.store.remove_source("/docs/a.txt")
        self.assertEqual(self.store.sources(), ["/docs/b.txt"])

    def test_persistence(self):
        self._fill()
        self.store.save()
        again = KnowledgeStore.load(self.path)
        self.assertEqual(len(again.chunks), 2)
        self.assertEqual(again.model, "embed")
        self.assertEqual(again.dimension, 2)

    def test_load_missing_file(self):
        again = KnowledgeStore.load(os.path.join(self.directory, "nope.json"))
        self.assertEqual(again.chunks, [])

    def test_load_corrupt_file(self):
        with open(self.path, "w", encoding="utf-8") as handle:
            handle.write("broken")
        again = KnowledgeStore.load(self.path)
        self.assertEqual(again.chunks, [])

    def test_clear(self):
        self._fill()
        self.store.clear()
        self.assertEqual(self.store.chunks, [])

    def test_mismatched_lengths_are_rejected(self):
        with self.assertRaises(ValueError):
            self.store.add("/x", "x", ["a", "b"], [[1.0, 0.0]], "embed")


if __name__ == "__main__":
    unittest.main()
