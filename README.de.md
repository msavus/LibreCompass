# LibreCompass — 1.5.0

[![CI](https://github.com/msavus/librecompass/actions/workflows/ci.yml/badge.svg)](https://github.com/msavus/librecompass/actions/workflows/ci.yml)
[![Lizenz: Apache 2.0](https://img.shields.io/badge/Lizenz-Apache_2.0-brightgreen.svg)](LICENSE)
[![Release](https://img.shields.io/github/v/release/msavus/librecompass?display_name=tag&sort=semver)](https://github.com/msavus/librecompass/releases/latest)

Lokale generative KI für LibreOffice — alle Module — über einen
OpenAI-kompatiblen lokalen Endpoint (Ollama, llama.cpp/llama-server,
LM Studio, vLLM). Keine Cloud, keine API-Keys.

Der Name ist das Produktversprechen: Die KI gibt die Richtung, **das Steuer
bleibt bei dir**. In Writer können KI-Änderungen als nachverfolgte
Änderungen aufgezeichnet werden — jede Änderung bleibt einzeln prüfbar.

English version: [README.md](README.md)

## Funktionsumfang

- **Schnellbefehle** auf der Auswahl: verbessern, umschreiben,
  zusammenfassen, übersetzen, eigener Prompt — aus der Menüleiste, dem
  **Rechtsklick-Menü** oder per **Tastenkürzel**
  (Strg+Umschalt+Alt+I/R/Z/T/P, Panel auf +C — auf Wunsch eingerichtet)
- **Panel** mit Modellauswahl, Promptbibliothek, Live-Streaming,
  Chat-Modus und drei Übernahme-Modi (ersetzen / einfügen / neues Dokument)
- **Wissensdatenbank (RAG)** über eigene Dateien, vollständig lokal —
  Antworten nennen ihre Quellen
- **Dokumentanalyse** als Bericht in einem neuen Dokument: harte
  Strukturkennzahlen plus Einschätzung des Modells
- **Plug-ins**: eigene Aktionen als einzelne Python-Dateien
- **Diagnose**-Befehl, der meldet, welche Teile der Extension in
  LibreOffice tatsächlich registriert wurden
- **Deutsche und englische** Oberfläche, folgt standardmäßig dem
  LibreOffice-Gebietsschema
- Läuft in **Writer, Calc, Impress und Draw**; Panel und Chat auch
  anderswo

## Dokumentation

| Dokument | Inhalt |
| --- | --- |
| [docs/user-guide.de.md](docs/user-guide.de.md) | Einrichtung, alle Funktionen, Fehlersuche |
| [docs/plugins.de.md](docs/plugins.de.md) | Plug-in-Schnittstelle und Beispiele |
| [docs/development.de.md](docs/development.de.md) | Aufbau, Threading, Bauen, Release |
| [CHANGELOG.md](CHANGELOG.md) | Versionsgeschichte |

## Voraussetzungen und Installation

- LibreOffice ≥ 7.4 (Standardinstallation mit gebündeltem Python)
- Ein lokales Backend, z. B. `ollama pull qwen3` und — für die
  Wissensdatenbank — `ollama pull nomic-embed-text`

1. Die `.oxt` aus dem
   [neuesten Release](https://github.com/msavus/librecompass/releases/latest) laden —
   oder selbst bauen mit `python3 build.py`
2. LibreOffice: **Extras → Extension Manager → Hinzufügen** → .oxt wählen
   (oder `make install`, das `unopkg` nutzt)
3. LibreOffice komplett neu starten (inkl. Schnellstarter)
4. Beliebiges Dokument öffnen → Menü **LibreCompass** erscheint

Optional nach der Installation: **LibreCompass → Tastenkürzel einrichten**
und **Kontextmenü einrichten** — beides bewusst auf Wunsch statt
ungefragt.

**Upgrade von einem Build vor 0.5:** Die Kennung hat sich von
`org.libreaiwriter.*` zu `org.librecompass.*` geändert — LibreOffice
behandelt das als andere Extension, den alten Eintrag vorher entfernen.
Alte Einstellungen werden nicht übernommen.

## Konfiguration

Ablage im LibreOffice-Benutzerprofil unter `user/librecompass/`:
`settings.json`, `prompts.json`, `history.json`, `knowledge.json`,
`plugins/`.

| Backend | Endpoint (`base_url`) |
| --- | --- |
| Ollama | `http://localhost:11434/v1` (Standard) |
| llama.cpp (llama-server) | `http://localhost:8080/v1` |
| LM Studio | `http://localhost:1234/v1` |
| vLLM | `http://localhost:8000/v1` |

Alle sprechen dieselbe `/v1/chat/completions`-API — deshalb gibt es genau
**einen** Client (`ai/client.py`, nur Standardbibliothek, da das in
LibreOffice eingebettete Python kein pip mitbringt).

Wichtige Schalter: `track_changes`, `stream` (`false` erzwingt synchrone
Anfragen), `language`, `max_context_chars`, `rag_top_k`.

## Architektur

```
registration.py                  dünne UNO-Registrierung (XJobExecutor)
Addons.xcu                       Menüeinträge (service:…?befehl)
Jobs.xcu                         registriert den Kontextmenü-Interceptor
pythonpath/librecompass/
├── app.py                       Befehls-Router
├── i18n.py                      englische msgids + deutscher Katalog
├── main_thread.py               AsyncCallback: Worker → Hauptthread
├── plugins.py                   Plug-in-Erkennung + stabile Schnittstelle
├── commands/                    eine Klasse pro Aktion, execute()
├── ai/                          Client (Chat/Streaming/Embeddings), Prompts, Verlauf
├── office/                      alle UNO-Zugriffe, Analyse, Textextraktion
├── rag/                         Chunking, Vektorindex, Indexierung/Retrieval
├── ui/                          Panel, Dialoge, Wissensdatenbank, Plug-ins
└── config/settings.py           settings.json im Benutzerprofil
```

Zwei Regeln: UNO bleibt in `office/`, HTTP bleibt in `ai/client.py`.
**Threading:** HTTP läuft im Worker-Thread; jeder Zugriff auf Controls oder
das Dokument geht über `main_thread.run_on_main()` zurück.

## Entwicklung

```
make check      # XML, Python-Syntax, Versionsgleichstand
make test       # 255 Tests, ohne LibreOffice
make build      # dist/librecompass-1.5.0.oxt
make install    # unopkg add --force
```

## Teststand — vor der Veröffentlichung lesen

- **Von der Suite abgedeckt (255 Tests, echte HTTP-Roundtrips gegen einen
  lokalen Server):** Client synchron/Streaming/Abbruch/Fehlerpfade,
  Embeddings, Prompts, Promptbibliothek, Verlauf, Einstellungen, i18n,
  Chunking, Vektorindex, Textextraktion (ODF/OOXML/Klartext), Indexierung
  und Retrieval, Plug-in-Laden und Plug-in-Schnittstelle, Aufbau des
  Kontextmenüs und Auswertung der Job-Argumente sowie — über
  UNO-Attrappen — die Lese- und Schreibpfade für Writer, Calc, Impress und
  Draw samt Dokumentanalyse.
- **Nicht abgedeckt (in der Build-Umgebung läuft kein LibreOffice):**
  Menü-Registrierung, Aufbau von Dialogen und Panel, `AsyncCallback`, das
  Lesen externer Dateien (PDF/DOC) über LibreOffice und — neu in 1.1 — ob
  der Kontextmenü-Job tatsächlich auslöst und ob die mitgelieferten
  Kürzel irgendwo kollidieren. Dafür ist ein Rauchtest in
  LibreOffice ≥ 7.4 nötig. Wenn das Panel zickt, zuerst
  `"stream": false` in `settings.json` setzen; machen Kontextmenü oder
  Kürzel Ärger, mit `--no-context-menu` bzw. `--no-shortcuts` neu bauen.

## Offene Punkte

- Echte andockbare Sidebar (`XUIElementFactory` + `Sidebar.xcu`) statt des
  nicht-modalen Panels — bewusst zurückgestellt: erfordert einen Umbau auf
  Control-Container und ist ohne LibreOffice nicht überprüfbar.
- Asynchrone Indexierung mit Fortschritt und Abbruch.
- Signierung und die `update.xml`-Quelle sind vorbereitet, aber nicht
  veröffentlicht.

## Mitwirken

Fehlerberichte, Plug-ins und Patches sind willkommen — siehe
[CONTRIBUTING.md](CONTRIBUTING.md). Fehlerberichten bitte die Ausgabe von
**LibreCompass → Diagnose …** beilegen; sie zeigt, welche Teile der
Erweiterung in der jeweiligen LibreOffice-Installation angekommen sind.

## Lizenz

[Apache License 2.0](LICENSE) — permissiv, mit explizitem Patent-Grant.
Kein Copyleft: LibreCompass darf in proprietäre Software eingebunden oder
damit kombiniert werden, ohne Änderungen offenlegen zu müssen.
