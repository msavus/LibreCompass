# -*- coding: utf-8 -*-
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at https://www.apache.org/licenses/LICENSE-2.0
"""Kommunikation mit dem Sprachmodell über eine OpenAI-kompatible API.

Ein einziger Client deckt alle im Projektplan genannten Backends ab, weil
Ollama, llama.cpp (llama-server), LM Studio, vLLM und KoboldCpp dieselbe
``/v1/chat/completions``-Schnittstelle sprechen. Es ändert sich nur die
``base_url`` in den Einstellungen.

Bewusst nur Standardbibliothek (urllib): Das in LibreOffice eingebettete
Python bringt kein pip mit.
"""
import json
import urllib.error
import urllib.request


class LLMError(Exception):
    """Fehler bei der Kommunikation mit dem Modell (für Dialoganzeige)."""


class LLMClient(object):
    def __init__(self, settings):
        self.settings = settings

    # ---- öffentliche API --------------------------------------------------
    def generate(self, prompt):
        return self.chat([{"role": "user", "content": prompt}])

    def chat(self, messages):
        payload = {
            "model": self.settings.model,
            "messages": messages,
            "temperature": float(self.settings.temperature),
            "max_tokens": int(self.settings.max_tokens),
            "stream": False,
        }
        data = self._post("/chat/completions", payload)
        try:
            content = data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError):
            raise LLMError("Unerwartetes Antwortformat:\n%s"
                           % json.dumps(data, ensure_ascii=False)[:800])
        if not content:
            raise LLMError("Das Modell hat eine leere Antwort geliefert.")
        return content.strip()

    def stream_chat(self, messages, on_delta, should_stop=None):
        """Wie chat(), aber mit Streaming (SSE, ``data:``-Zeilen).

        ``on_delta(text)`` wird pro Teilstück aufgerufen (im aufrufenden
        Thread!); ``should_stop()`` erlaubt den Abbruch zwischen Zeilen.
        Rückgabe ist die vollständige (ggf. abgebrochene) Antwort.
        """
        payload = {
            "model": self.settings.model,
            "messages": messages,
            "temperature": float(self.settings.temperature),
            "max_tokens": int(self.settings.max_tokens),
            "stream": True,
        }
        request = urllib.request.Request(
            self._url("/chat/completions"),
            data=json.dumps(payload).encode("utf-8"),
            headers=self._headers(),
            method="POST",
        )
        timeout = int(self.settings.timeout_seconds)
        try:
            response = urllib.request.urlopen(request, timeout=timeout)
        except urllib.error.HTTPError as exc:
            body = ""
            try:
                body = exc.read().decode("utf-8", "replace")[:500]
            except Exception:
                pass
            raise LLMError("HTTP %s vom Server\n%s\n%s"
                           % (exc.code, request.full_url, body))
        except urllib.error.URLError as exc:
            raise LLMError(
                "Server nicht erreichbar:\n%s\n\nDetails: %s"
                % (request.full_url, exc.reason))
        parts = []
        try:
            for raw_line in response:
                if should_stop is not None and should_stop():
                    break
                line = raw_line.decode("utf-8", "replace").strip()
                if not line.startswith("data:"):
                    continue
                data = line[5:].strip()
                if data == "[DONE]":
                    break
                try:
                    payload = json.loads(data)
                except ValueError:
                    continue
                try:
                    delta = payload["choices"][0]["delta"].get("content") or ""
                except (KeyError, IndexError, TypeError, AttributeError):
                    delta = ""
                if delta:
                    parts.append(delta)
                    on_delta(delta)
        except Exception as exc:
            if parts:
                return "".join(parts).strip()
            raise LLMError("Streaming abgebrochen: %s" % exc)
        finally:
            try:
                response.close()
            except Exception:
                pass
        return "".join(parts).strip()

    def embeddings(self, inputs, model=None):
        """Embeddings für eine Liste von Texten (für die Wissensdatenbank).

        Nutzt ``/v1/embeddings``; Ollama, llama-server, LM Studio und vLLM
        bieten den Endpoint OpenAI-kompatibel an.
        """
        if not inputs:
            return []
        payload = {
            "model": model or getattr(self.settings, "embedding_model",
                                      self.settings.model),
            "input": list(inputs),
        }
        data = self._post("/embeddings", payload)
        try:
            entries = data["data"]
        except (KeyError, TypeError):
            raise LLMError("Unerwartete Embedding-Antwort:\n%s"
                           % json.dumps(data, ensure_ascii=False)[:500])
        vectors = []
        for entry in entries:
            vector = entry.get("embedding") if isinstance(entry, dict) else None
            if not vector:
                raise LLMError("Embedding ohne Vektor erhalten.")
            vectors.append([float(value) for value in vector])
        if len(vectors) != len(inputs):
            raise LLMError("Embedding-Anzahl passt nicht zur Eingabe "
                           "(%d statt %d)." % (len(vectors), len(inputs)))
        return vectors

    def models(self):
        """Verfügbare Modelle (für die Modellauswahl ab Version 0.2)."""
        data = self._get("/models")
        try:
            return [entry["id"] for entry in data.get("data", [])]
        except (TypeError, KeyError):
            return []

    # ---- intern -------------------------------------------------------------
    def _url(self, path):
        return str(self.settings.base_url).rstrip("/") + path

    def _headers(self):
        headers = {"Content-Type": "application/json"}
        api_key = getattr(self.settings, "api_key", "")
        if api_key:
            headers["Authorization"] = "Bearer " + api_key
        return headers

    def _post(self, path, payload):
        request = urllib.request.Request(
            self._url(path),
            data=json.dumps(payload).encode("utf-8"),
            headers=self._headers(),
            method="POST",
        )
        return self._send(request)

    def _get(self, path):
        request = urllib.request.Request(self._url(path), headers=self._headers())
        return self._send(request)

    def _send(self, request):
        timeout = int(self.settings.timeout_seconds)
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                raw = response.read().decode("utf-8", "replace")
        except urllib.error.HTTPError as exc:
            body = ""
            try:
                body = exc.read().decode("utf-8", "replace")[:500]
            except Exception:
                pass
            raise LLMError(
                "HTTP %s vom Server\n%s\n%s\n\n"
                "Stimmen Modellname (%r) und Endpoint?"
                % (exc.code, request.full_url, body, self.settings.model))
        except urllib.error.URLError as exc:
            raise LLMError(
                "Server nicht erreichbar:\n%s\n\n"
                "Läuft das Backend? Beispiele:\n"
                "  Ollama:       ollama serve   →  http://localhost:11434/v1\n"
                "  llama-server: llama-server … →  http://localhost:8080/v1\n\n"
                "Details: %s" % (request.full_url, exc.reason))
        except Exception as exc:  # z. B. Timeout als OSError
            raise LLMError("Anfrage fehlgeschlagen: %s" % exc)
        try:
            return json.loads(raw)
        except ValueError:
            raise LLMError("Antwort ist kein gültiges JSON:\n%s" % raw[:500])
