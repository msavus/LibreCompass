# -*- coding: utf-8 -*-
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at https://www.apache.org/licenses/LICENSE-2.0
"""Text in überlappende Abschnitte zerlegen.

Es wird bevorzugt an Absatz-, dann an Satz-, zuletzt an Wortgrenzen
getrennt, damit Abschnitte für sich lesbar bleiben. Reine
Standardbibliothek – im eingebetteten LibreOffice-Python gibt es kein pip.
"""
import re

_PARAGRAPH = re.compile(r"\n\s*\n")
_SENTENCE = re.compile(r"(?<=[.!?;:])\s+")


def split_text(text, size=1200, overlap=150):
    """Liste von Abschnitten; ``size``/``overlap`` in Zeichen.

    ``size`` wird nach unten auf 200 Zeichen begrenzt, ``overlap`` auf
    ``size // 2``. Zugesicherte Obergrenze pro Abschnitt ist
    ``size + overlap + 1``: Der Überlappungstext wird dem nächsten
    Abschnitt vorangestellt und zählt zu dessen Länge.
    """
    text = (text or "").strip()
    if not text:
        return []
    size = max(200, int(size))
    overlap = max(0, min(int(overlap), size // 2))

    pieces = _flatten(text, size)
    chunks = []
    current = ""
    for piece in pieces:
        if not current:
            current = piece
        elif len(current) + 1 + len(piece) <= size:
            current += "\n" + piece
        else:
            chunks.append(current)
            current = (_tail(current, overlap) + "\n" + piece
                       if overlap else piece)
    if current.strip():
        chunks.append(current)
    return [chunk.strip() for chunk in chunks if chunk.strip()]


def _flatten(text, size):
    """Text in Teile zerlegen, die einzeln nicht größer als ``size`` sind."""
    result = []
    for paragraph in _PARAGRAPH.split(text):
        paragraph = paragraph.strip()
        if not paragraph:
            continue
        if len(paragraph) <= size:
            result.append(paragraph)
            continue
        for sentence in _SENTENCE.split(paragraph):
            sentence = sentence.strip()
            if not sentence:
                continue
            if len(sentence) <= size:
                result.append(sentence)
            else:
                result.extend(_hard_split(sentence, size))
    return result


def _hard_split(text, size):
    """Sehr langen Text an Wortgrenzen zerteilen (Notfall: hart schneiden)."""
    parts = []
    current = ""
    for word in text.split():
        if not current:
            current = word
        elif len(current) + 1 + len(word) <= size:
            current += " " + word
        else:
            parts.append(current)
            current = word
        while len(current) > size:
            parts.append(current[:size])
            current = current[size:]
    if current:
        parts.append(current)
    return parts


def _tail(text, count):
    """Letzte ``count`` Zeichen, möglichst an einer Wortgrenze beginnend."""
    if count <= 0 or len(text) <= count:
        return text
    tail = text[-count:]
    space = tail.find(" ")
    return tail[space + 1:] if 0 <= space < count // 2 else tail
