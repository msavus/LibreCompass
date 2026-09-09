# -*- coding: utf-8 -*-
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at https://www.apache.org/licenses/LICENSE-2.0
"""Prompt-Bausteine und die Promptbibliothek (prompts.json).

Der Benutzer-Prompt wird automatisch um den Text erweitert (TEXT-Block).
Zwei Regeln sorgen dafür, dass die Antwort sich sauber ins Dokument
einsetzen lässt. Die Instruktionen folgen der aktiven UI-Sprache.
"""
import json
import os

from librecompass.i18n import language

_RULES = {
    "en": (
        "Reply in the language of the source text unless the instruction "
        "says otherwise.",
        "Return the result only - no preamble, no explanations, no quotation "
        "marks and no Markdown unless the source text contains Markdown.",
    ),
    "de": (
        "Antworte in der Sprache des Ausgangstextes, sofern die Anweisung "
        "nichts anderes verlangt.",
        "Gib ausschließlich das Ergebnis zurück - ohne Einleitung, ohne "
        "Erklärungen, ohne Anführungszeichen und ohne Markdown, sofern der "
        "Ausgangstext kein Markdown enthält.",
    ),
}

INSTRUCTIONS = {
    "improve": {
        "en": ("Improve the following text: spelling, grammar, punctuation "
               "and style. Preserve meaning, tone and structure."),
        "de": ("Verbessere den folgenden Text sprachlich: Rechtschreibung, "
               "Grammatik, Zeichensetzung und Stil. Erhalte Bedeutung, Ton "
               "und Gliederung."),
    },
    "summarize": {
        "en": ("Summarize the following text concisely. Keep all essential "
               "statements."),
        "de": ("Fasse den folgenden Text prägnant zusammen. Erhalte alle "
               "wesentlichen Aussagen."),
    },
    "professional": {
        "en": ("Rewrite the following text more professionally without "
               "changing its content."),
        "de": ("Formuliere den folgenden Text professioneller, ohne den "
               "Inhalt zu verändern."),
    },
    "translate": {
        "en": "Translate the following text into: {language}.",
        "de": "Übersetze den folgenden Text nach: {language}.",
    },
    "analysis": {
        "en": ("You are reviewing a document. Below are hard structural "
               "metrics and the document text. Comment on structure, "
               "consistency, readability and gaps. Be specific and brief; "
               "do not repeat the metrics."),
        "de": ("Du prüfst ein Dokument. Unten stehen harte "
               "Strukturkennzahlen und der Dokumenttext. Kommentiere "
               "Struktur, Konsistenz, Lesbarkeit und Lücken. Sei konkret "
               "und knapp; wiederhole die Kennzahlen nicht."),
    },
    "rag_system": {
        "en": ("Answer strictly from the excerpts provided below. If the "
               "answer is not contained in them, say so plainly. Cite the "
               "source names you used."),
        "de": ("Antworte ausschließlich anhand der unten aufgeführten "
               "Auszüge. Steht die Antwort nicht darin, sage das klar. "
               "Nenne die verwendeten Quellennamen."),
    },
    "chat_system": {
        "en": ("You are a helpful assistant inside LibreOffice. Answer in "
               "the language of the question."),
        "de": ("Du bist ein hilfreicher Assistent in LibreOffice. Antworte "
               "in der Sprache der Frage."),
    },
    "document_context": {
        "en": "Current document content (may be truncated):",
        "de": "Aktueller Dokumentinhalt (ggf. gekürzt):",
    },
    "excerpts": {
        "en": "Excerpts from the knowledge base:",
        "de": "Auszüge aus der Wissensdatenbank:",
    },
}

DEFAULT_LIBRARY_KEYS = (
    ("Improve", "Verbessern", "improve"),
    ("Summarize", "Zusammenfassen", "summarize"),
    ("More professional", "Professioneller formulieren", "professional"),
)


def instruction(key, **kwargs):
    """Vorgefertigte Instruktion in der aktiven Sprache."""
    entry = INSTRUCTIONS.get(key, {})
    text = entry.get(language()) or entry.get("en") or ""
    return text.format(**kwargs) if kwargs else text


def build_prompt(user_instruction, text):
    """Vollständiger Prompt: Anweisung + Regeln + TEXT-Block."""
    rules = _RULES.get(language(), _RULES["en"])
    return (
        user_instruction.strip()
        + "\n\n" + rules[0]
        + "\n" + rules[1]
        + "\n\nTEXT:\n\"\"\"\n" + text + "\n\"\"\""
    )


def build_rag_messages(question, context):
    """Nachrichten für eine Frage an die Wissensdatenbank."""
    system = (instruction("rag_system") + "\n\n"
              + instruction("excerpts") + "\n\"\"\"\n" + context + "\n\"\"\"")
    return [{"role": "system", "content": system},
            {"role": "user", "content": question}]


def default_library():
    """Standardbibliothek in der aktiven Sprache."""
    code = language()
    library = []
    for english, german, key in DEFAULT_LIBRARY_KEYS:
        library.append({"name": german if code == "de" else english,
                        "prompt": instruction(key)})
    target = "Englisch" if code == "de" else "English"
    library.append({
        "name": ("Übersetzen (Englisch)" if code == "de"
                 else "Translate (English)"),
        "prompt": instruction("translate", language=target),
    })
    return library


def load_library(settings):
    """Promptbibliothek laden; beim ersten Aufruf mit Standardwerten anlegen."""
    path = settings.prompts_path()
    if not os.path.exists(path):
        library = default_library()
        try:
            with open(path, "w", encoding="utf-8") as handle:
                json.dump(library, handle, ensure_ascii=False, indent=2)
        except Exception:
            pass
        return library
    try:
        with open(path, "r", encoding="utf-8") as handle:
            library = json.load(handle)
        if isinstance(library, list):
            return library
    except Exception:
        pass
    return default_library()


def save_to_library(settings, name, prompt):
    """Prompt unter ``name`` in prompts.json ablegen (ersetzt Gleichnamiges)."""
    library = [entry for entry in load_library(settings)
               if entry.get("name") != name]
    library.append({"name": name, "prompt": prompt})
    try:
        with open(settings.prompts_path(), "w", encoding="utf-8") as handle:
            json.dump(library, handle, ensure_ascii=False, indent=2)
    except Exception:
        pass
    return library
