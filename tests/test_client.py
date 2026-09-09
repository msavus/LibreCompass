# -*- coding: utf-8 -*-
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at https://www.apache.org/licenses/LICENSE-2.0
"""Client gegen einen echten lokalen HTTP-Server (synchron, Streaming)."""
import json
import threading
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer

import context  # noqa: F401

from librecompass.ai.client import LLMClient, LLMError


class _Handler(BaseHTTPRequestHandler):
    mode = "ok"

    def log_message(self, *args):
        pass

    def _json(self, payload, status=200):
        body = json.dumps(payload).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path.endswith("/models"):
            self._json({"data": [{"id": "qwen3"}, {"id": "mistral"}]})
        else:
            self._json({}, 404)

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        payload = json.loads(self.rfile.read(length) or b"{}")
        if _Handler.mode == "http500":
            self._json({"error": "boom"}, 500)
            return
        if _Handler.mode == "garbage":
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"not json")
            return
        if self.path.endswith("/embeddings"):
            vectors = [{"embedding": [1.0, 2.0, 3.0]}
                       for _ in payload.get("input", [])]
            self._json({"data": vectors})
            return
        if payload.get("stream"):
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.end_headers()
            for token in ("Set ", "the ", "course."):
                chunk = {"choices": [{"delta": {"content": token}}]}
                self.wfile.write(b"data: " + json.dumps(chunk).encode()
                                 + b"\n\n")
            self.wfile.write(b"data: [DONE]\n\n")
            return
        self._json({"choices": [{"message": {"content": "  Answer  "}}]})


class _Settings(object):
    api_key = ""
    model = "qwen3"
    embedding_model = "embed"
    temperature = 0.3
    max_tokens = 64
    timeout_seconds = 10

    def __init__(self, port):
        self.base_url = "http://127.0.0.1:%d/v1" % port


class ClientTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = HTTPServer(("127.0.0.1", 0), _Handler)
        cls.thread = threading.Thread(target=cls.server.serve_forever,
                                      daemon=True)
        cls.thread.start()
        cls.settings = _Settings(cls.server.server_address[1])

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()

    def setUp(self):
        _Handler.mode = "ok"
        self.client = LLMClient(self.settings)

    def test_chat_strips_whitespace(self):
        self.assertEqual(self.client.chat([{"role": "user", "content": "x"}]),
                         "Answer")

    def test_generate_uses_chat(self):
        self.assertEqual(self.client.generate("x"), "Answer")

    def test_models(self):
        self.assertEqual(self.client.models(), ["qwen3", "mistral"])

    def test_embeddings(self):
        vectors = self.client.embeddings(["a", "b"])
        self.assertEqual(vectors, [[1.0, 2.0, 3.0], [1.0, 2.0, 3.0]])

    def test_embeddings_empty_input(self):
        self.assertEqual(self.client.embeddings([]), [])

    def test_streaming_collects_deltas(self):
        deltas = []
        full = self.client.stream_chat([{"role": "user", "content": "x"}],
                                       deltas.append)
        self.assertEqual(full, "Set the course.")
        self.assertEqual("".join(deltas), "Set the course.")

    def test_streaming_stops_on_request(self):
        deltas = []
        full = self.client.stream_chat(
            [{"role": "user", "content": "x"}], deltas.append,
            should_stop=lambda: True)
        self.assertEqual(full, "")

    def test_http_error_becomes_llmerror(self):
        _Handler.mode = "http500"
        with self.assertRaises(LLMError):
            self.client.chat([{"role": "user", "content": "x"}])

    def test_invalid_json_becomes_llmerror(self):
        _Handler.mode = "garbage"
        with self.assertRaises(LLMError):
            self.client.chat([{"role": "user", "content": "x"}])

    def test_unreachable_server_becomes_llmerror(self):
        class Down(_Settings):
            base_url = "http://127.0.0.1:1/v1"
        with self.assertRaises(LLMError):
            LLMClient(Down(1)).chat([{"role": "user", "content": "x"}])


if __name__ == "__main__":
    unittest.main()
