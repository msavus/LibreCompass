# LibreCompass — Plug-ins schreiben

English: [plugins.en.md](plugins.en.md)

Ein Plug-in ist eine einzelne Python-Datei im Benutzerprofil:
`<Profil>/user/librecompass/plugins/`. Dateien, die mit `_` beginnen, werden
ignoriert. Ein defektes Plug-in wird übersprungen — es kann die Erweiterung
nicht lahmlegen.

> **Sicherheit:** Plug-ins sind gewöhnlicher Python-Code mit allen Rechten
> des LibreOffice-Prozesses. Nur selbst geschriebene oder geprüfte Dateien
> ablegen.

## Prompt-Plug-ins

Die einfachste Form liefert einen wiederverwendbaren Prompt:

```python
NAME = "Bullet points"
DESCRIPTION = "Turns the selection into a concise bullet list"
PROMPT = ("Rewrite the following text as a concise bullet list. "
          "One idea per bullet, no sub-bullets.")
```

Es erscheint unter **LibreCompass → Plug-ins …**; *Prompt einfügen*
übernimmt es in das Prompt-Feld des Panels, wo Kontext und
Übernahme-Modus wie gewohnt gewählt werden.

## Aktions-Plug-ins

Für volle Kontrolle statt (oder zusätzlich zu) `PROMPT` eine Funktion
`run(api)` definieren:

```python
NAME = "Word count"
DESCRIPTION = "Counts words and characters"


def run(api):
    text = api.selection() or api.document_text()
    api.message("%d Wörter, %d Zeichen" % (len(text.split()), len(text)))
```

## Das `api`-Objekt

Dies ist die einzige Schnittstelle, deren Stabilität LibreCompass zusagt;
alles andere im Code kann sich ändern.

| Methode | Liefert / bewirkt |
| --- | --- |
| `api.selection()` | markierter Text (`""` ohne Auswahl) |
| `api.document_text()` | gesamtes Dokument als Text |
| `api.module()` | `"writer"`, `"calc"`, `"impress"`, `"draw"` oder `None` |
| `api.setting(name, default)` | Wert aus `settings.json` |
| `api.ask(prompt)` | eine Modellanfrage, liefert die Antwort |
| `api.chat(messages)` | Modellanfrage mit Nachrichtenliste |
| `api.replace_selection(text)` | ersetzt die Auswahl, `True` bei Erfolg |
| `api.insert(text)` | fügt an der Cursorposition ein, `True` bei Erfolg |
| `api.new_document(text)` | öffnet ein neues Writer-Dokument mit `text` |
| `api.message(text)` | zeigt einen Hinweisdialog |

`replace_selection` und `insert` beachten die Einstellung `track_changes`
automatisch. In Modulen ohne Übernahme-Unterstützung (Math, Base) liefern
sie `False` — Rückgabewert prüfen oder `new_document` verwenden.

Modellaufrufe sind synchron: Die Oberfläche wartet. Prompts klein halten
oder in ein neues Dokument schreiben, statt über einen großen Text zu
iterieren.

## Empfohlenes Muster

Lesen → fragen → in ein *neues* Dokument schreiben, damit das Original
unangetastet bleibt:

```python
NAME = "Terminology check"

INSTRUCTION = ("List terms used inconsistently in the text below and "
               "suggest one variant each.\n\nTEXT:\n\"\"\"\n%s\n\"\"\"")


def run(api):
    text = api.selection() or api.document_text()
    if not text.strip():
        api.message("Nichts zu prüfen.")
        return
    limit = int(api.setting("max_context_chars", 24000))
    api.new_document("Terminology check\n\n" + api.ask(INSTRUCTION % text[:limit]))
```

## Plug-in testen

Fehler innerhalb von `run()` werden abgefangen und mit Traceback angezeigt.
Die schnellste Schleife ist daher: Datei bearbeiten, Plug-in-Dialog erneut
öffnen, erneut ausführen. Plug-in-Dateien werden zwischen zwei Dialogaufrufen
nicht zwischengespeichert.

Fertige Beispiele liegen in `examples/plugins/`:
`bullet_points.py`, `word_count.py`, `terminology_check.py`.
