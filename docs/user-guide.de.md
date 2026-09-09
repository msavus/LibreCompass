# LibreCompass — Benutzerhandbuch

English: [user-guide.en.md](user-guide.en.md)

LibreCompass bringt lokale generative KI in alle LibreOffice-Module. Nichts
verlässt den Rechner: Die Erweiterung spricht einen lokalen Modellserver
über einen OpenAI-kompatiblen HTTP-Endpoint an.

## 1. Modellserver einrichten

Alle Varianten funktionieren; es unterscheidet sich nur der Endpoint.

| Backend | Start | Endpoint |
| --- | --- | --- |
| Ollama | `ollama serve` (läuft oft schon) | `http://localhost:11434/v1` |
| llama.cpp | `llama-server -m modell.gguf` | `http://localhost:8080/v1` |
| LM Studio | lokalen Server in der App starten | `http://localhost:1234/v1` |
| vLLM | `vllm serve <modell>` | `http://localhost:8000/v1` |

Chat-Modell laden und — für die Wissensdatenbank — ein Embedding-Modell:

```
ollama pull qwen3
ollama pull nomic-embed-text
```

Danach unter **LibreCompass → Einstellungen …** Endpoint, Chat-Modell und
Embedding-Modell prüfen.

## 2. Schnellbefehle

Text (oder Zellen oder eine Form) markieren und wählen:

| Befehl | Wirkung |
| --- | --- |
| Auswahl verbessern | Rechtschreibung, Grammatik, Zeichensetzung, Stil |
| Auswahl umschreiben … | fragt nach einer Anweisung und schreibt um |
| Zusammenfassen | fasst die Auswahl zusammen; ohne Auswahl das ganze Dokument |
| Übersetzen … | fragt nach der Zielsprache |
| Eigener Prompt … | freie Anweisung auf die Auswahl |

Diese Befehle laufen im Hintergrund: Die Statusleiste zeigt die offene
Anfrage, und es lässt sich weiterarbeiten, während das Modell rechnet.
Das Ergebnis ersetzt den Text, der beim Absenden markiert war — auch
wenn inzwischen etwas anderes markiert ist. Es läuft immer nur eine
Anfrage.

## 3. Kontextmenü und Tastenkürzel

Einmal **LibreCompass → Kontextmenü einrichten** aufrufen. Danach bietet
ein Rechtsklick in Writer, Calc, Impress oder Draw ein Untermenü
**LibreCompass** mit denselben Befehlen wie die Menüleiste. Die Einträge
landen in der Kontextmenü-Konfiguration von LibreOffice und überstehen
einen Neustart; **Kontextmenü entfernen** nimmt sie zurück, und unter
Extras → Anpassen → Kontextmenüs lassen sie sich ebenfalls bearbeiten.

Die Kürzel werden **nicht** automatisch installiert. Einmal
**LibreCompass → Tastenkürzel einrichten** aufrufen;
**Tastenkürzel entfernen** nimmt sie wieder zurück. Eine bereits
belegte Kombination wird nie überschrieben, sondern gemeldet.

Vorgabe:

| Kürzel | Befehl |
| --- | --- |
| Strg+Umschalt+Alt+C | Panel öffnen (überall verfügbar) |
| Strg+Umschalt+Alt+I | Auswahl verbessern |
| Strg+Umschalt+Alt+R | Auswahl umschreiben |
| Strg+Umschalt+Alt+Z | Zusammenfassen |
| Strg+Umschalt+Alt+T | Übersetzen |
| Strg+Umschalt+Alt+P | Eigener Prompt |

Warum drei Modifikatoren: Strg+Umschalt ist von LibreOffice selbst stark
belegt (Hoch-/Tiefstellen, Speichern unter, Druckvorschau, Inhalte
einfügen), und Strg+Alt ist auf deutschen Tastaturen AltGr — dort
entstehen Zeichen wie @ und €. Strg+Umschalt+Alt lässt beides in Ruhe.

Ändern unter **Extras → Anpassen → Tastatur**; die
LibreCompass-Befehle stehen dort im Bereich *Add-Ons*. Kollidiert eine
Kombination mit dem Desktop-System, dort neu belegen — das System gewinnt
gegen LibreOffice.

**Wenn beides nicht erscheint:** **LibreCompass → Diagnose …** aufrufen.
Sie liest die laufende Konfiguration und meldet, welcher der drei
Mechanismen (Menü, Kürzel, Kontextmenü-Job) tatsächlich registriert wurde
und was bei den übrigen zu tun ist. Kürzel, die nicht ankommen, lassen
sich immer von Hand unter Extras → Anpassen → Tastatur zuweisen; ein
registriertes, aber inaktives Kontextmenü schaltet
**LibreCompass → Kontextmenü aktivieren** ein.

## 4. Das Panel

**LibreCompass → LibreCompass-Panel** öffnet die Hauptoberfläche. Sie bleibt
offen, während im Dokument weitergearbeitet wird.

- **Modell** — vom Server geladen; ↻ lädt neu. Die Wahl wird gespeichert.
- **Promptbibliothek** — Eintrag wählen, *Einfügen* übernimmt ihn ins
  Prompt-Feld, *Speichern* legt den aktuellen Prompt unter einem Namen ab.
- **Prompt** — freier, mehrzeiliger Text.
- **Kontext** — was das Modell außer dem Prompt sieht:
  *Auswahl*, *Gesamtes Dokument* (gekürzt auf `max_context_chars`),
  *Wissensdatenbank* (siehe unten) oder *Ohne Kontext*.
- **Chat-Modus** — hält den Verlauf. Der Kontext wird beim ersten Senden in
  die System-Nachricht eingefroren; *Chat leeren* beginnt neu.
- **Senden** streamt die Antwort live; **Stopp** bricht ab und behält das
  bereits Empfangene.
- **Übernehmen als** — *Auswahl ersetzen*, *Am Cursor einfügen* oder
  *Neues Dokument*, dann **Übernehmen**. Übernommen wird stets die letzte
  Antwort.
- **Verlauf** — die letzten 200 Prompt/Antwort-Paare; ein Eintrag lädt
  beides zurück.

## 5. Kontrolle behalten

In den Einstellungen **Ersetzungen als nachverfolgte Änderungen einfügen**
aktivieren. Jede KI-Änderung in Writer erscheint dann unter
*Bearbeiten → Änderungen* und lässt sich einzeln annehmen oder verwerfen.
Für Dokumente, auf die es ankommt, ist das die empfohlene Einstellung.

In Calc wird ausschließlich die Zielzelle geschrieben — keine andere Zelle
wird angetastet.

## 6. Verhalten je Modul

| Modul | Auswahl lesen | Ersetzen | Einfügen |
| --- | --- | --- | --- |
| Writer | markierter Text | ersetzt die Auswahl | an der Cursorposition |
| Calc | markierte Zellen (Tab/Zeilenumbruch) | oberste linke Zelle der Auswahl | Zelle unterhalb der Auswahl |
| Impress / Draw | Text der markierten Formen | erste markierte Form | hängt an die Form an; ohne Markierung neue Textbox |
| Math, Base u. a. | – | – | – (Panel und Chat funktionieren; Übernahme über *Neues Dokument*) |

## 7. Wissensdatenbank (RAG)

**LibreCompass → Wissensdatenbank …** indexiert eigene Dateien, sodass
Fragen über mehrere Dokumente hinweg möglich sind.

1. *Datei hinzufügen …* oder *Ordner hinzufügen …* und Pfad eingeben.
2. Der Text wird extrahiert, in Abschnitte zerlegt und mit dem
   Embedding-Modell eingebettet; der Index liegt als `knowledge.json` im
   Benutzerprofil.
3. Im Panel **Kontext** auf *Wissensdatenbank* stellen und fragen. Die
   Antwort nennt die verwendeten Quellen.

Ohne Zusatzsoftware lesbar: `txt`, `md`, `csv`, `json`, `xml`, `html`,
`odt`, `ods`, `odp`, `docx`, `xlsx`, `pptx`. Formate wie `pdf`, `doc`,
`rtf` und `epub` werden gelesen, indem LibreOffice sie unsichtbar lädt.

Hinweise: Ein Wechsel des Embedding-Modells macht den Index ungültig
(Vektoren verschiedener Modelle sind nicht vergleichbar) — LibreCompass
leert ihn, der Neuaufbau erfolgt manuell. Die Indexierung läuft im
Hintergrund mit Fortschrittsanzeige im Dialog. Die Suche
ist eine lineare Prüfung in Python und trägt bis in den Bereich einiger
tausend Abschnitte.

## 8. Dokumentanalyse

**LibreCompass → Dokument analysieren** erzeugt einen Bericht in einem
*neuen* Dokument — das analysierte Dokument bleibt unverändert. Der Bericht
hat zwei Teile:

- **Struktur** — harte Zahlen, direkt aus dem Dokument gelesen (Absätze,
  Wörter, Überschriften samt Gliederung, Tabellen, Bilder;
  Tabellenblätter, gefüllte Zellen, Formeln; Folien, Formen mit Text).
  Diese Zahlen kommen aus LibreOffice, nicht aus dem Modell.
- **Beobachtungen** — die Einschätzung des Modells zu Struktur, Konsistenz,
  Lesbarkeit und Lücken.

## 9. Plug-ins

**LibreCompass → Plug-ins …** listet eigene Aktionen. Schnittstelle und
Beispiele: [plugins.de.md](plugins.de.md).

## 10. Dateien und Einstellungen

Alles liegt im LibreOffice-Benutzerprofil unter `user/librecompass/`:

| Datei | Inhalt |
| --- | --- |
| `settings.json` | alle Einstellungen |
| `prompts.json` | Promptbibliothek (von Hand editierbar) |
| `history.json` | Verlauf |
| `knowledge.json` | Index der Wissensdatenbank |
| `plugins/` | eigene Plug-in-Dateien |

Nützliche Schlüssel in `settings.json`: `language` (`auto`/`en`/`de`),
`track_changes`, `stream` (auf `false` für synchrone Anfragen),
`max_context_chars`, `chunk_size`, `chunk_overlap`, `rag_top_k`,
`temperature`, `max_tokens`, `timeout_seconds`.

## 11. Fehlersuche

| Symptom | Ursache / Abhilfe |
| --- | --- |
| „Server nicht erreichbar" | Modellserver läuft nicht oder falscher Endpoint |
| HTTP 404 mit Modellnamen | Modell auf dem Server nicht vorhanden; `ollama pull <name>` |
| Panel hängt oder Streaming wirkt seltsam | `"stream": false` in `settings.json`, Panel neu öffnen |
| Schnellbefehl tut nichts | es war nichts markiert — die Statusleiste zeigt Anfragen |
| Wissensdatenbank findet nichts | Index leer oder Embedding-Modell nicht geladen |
| Menü fehlt nach der Installation | LibreOffice war nicht komplett neu gestartet (inkl. Schnellstarter) |
| Kein LibreCompass-Eintrag beim Rechtsklick | der Kontextmenü-Job lief nicht; mit `--no-context-menu` bauen und die Menüleiste nutzen oder melden |
| Ein Kürzel tut nichts | die Kombination ist vom Desktop-System belegt; unter Extras → Anpassen → Tastatur neu belegen |
| Ein Kürzel hat eines überschrieben, das gebraucht wird | unter Extras → Anpassen → Tastatur ändern oder mit `--no-shortcuts` bauen |
