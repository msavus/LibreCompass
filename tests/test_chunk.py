# -*- coding: utf-8 -*-
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at https://www.apache.org/licenses/LICENSE-2.0
import unittest

import context  # noqa: F401

from librecompass.rag import chunk


class ChunkTest(unittest.TestCase):
    def test_empty_text(self):
        self.assertEqual(chunk.split_text(""), [])
        self.assertEqual(chunk.split_text("   \n  "), [])

    def test_short_text_is_one_chunk(self):
        self.assertEqual(chunk.split_text("Short text."), ["Short text."])

    def test_respects_size(self):
        text = "\n\n".join("Paragraph %d. %s" % (number, "x" * 100)
                           for number in range(20))
        chunks = chunk.split_text(text, size=300, overlap=0)
        self.assertGreater(len(chunks), 1)
        for piece in chunks:
            self.assertLessEqual(len(piece), 300)

    def test_overlap_is_added_on_top_of_size(self):
        # Dokumentierte Obergrenze: size + overlap + 1
        text = "word " * 400
        chunks = chunk.split_text(text, size=300, overlap=100)
        for piece in chunks:
            self.assertLessEqual(len(piece), 401)

    def test_overlap_repeats_content(self):
        text = "\n\n".join("Paragraph %d with some words in it." % number
                           for number in range(30))
        with_overlap = chunk.split_text(text, size=300, overlap=120)
        without = chunk.split_text(text, size=300, overlap=0)
        self.assertGreater(sum(len(p) for p in with_overlap),
                           sum(len(p) for p in without))

    def test_very_long_word_is_hard_split(self):
        chunks = chunk.split_text("a" * 3000, size=500, overlap=0)
        self.assertGreater(len(chunks), 1)
        for piece in chunks:
            self.assertLessEqual(len(piece), 500)

    def test_no_empty_chunks(self):
        chunks = chunk.split_text("A.\n\n\n\nB.\n\n   \n\nC.", size=250)
        self.assertTrue(all(piece.strip() for piece in chunks))

    def test_content_is_preserved(self):
        text = "\n\n".join("Sentence number %d." % n for n in range(40))
        joined = " ".join(chunk.split_text(text, size=400, overlap=0))
        for number in (0, 17, 39):
            self.assertIn("Sentence number %d." % number, joined)

    def test_minimum_size_is_enforced(self):
        # size wird auf 200 hochgezogen, overlap auf size // 2 begrenzt
        chunks = chunk.split_text("word " * 200, size=10, overlap=5)
        self.assertTrue(chunks)
        self.assertTrue(all(len(piece) <= 206 for piece in chunks))


if __name__ == "__main__":
    unittest.main()
