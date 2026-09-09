# LibreCompass — Entwicklung

English: [development.en.md](development.en.md)

## Aufbau

```
description.xml            Extension-Manifest (Kennung, Version, Texte)
Addons.xcu                 Menüeinträge, je einer pro service:…?befehl
Jobs.xcu                   bindet den Kontextmenü-Job an Dokumentereignisse
registration.py            dünne UNO-Komponente (XJobExecutor)
META-INF/manifest.xml       sagt LibreOffice, was in der .oxt steckt
build.py                   prüfen und nach dist/*.oxt packen
Makefile                   test / check / build / install / dist / clean
update.xml                 Vorlage für die Aktualisierungsquelle
pythonpath/librecompass/    der eigentliche Code (von LO in sys.path gelegt)
tests/                     läuft ohne LibreOffice (UNO-Stubs + Attrappen)
examples/plugins/          fertige Plug-in-Beispiele
docs/                      Handbuch, Plug-in-Schnittstelle, diese Datei
```

Innerhalb von `pythonpath/librecompass/`:

| Modul | Zuständigkeit |
| --- | --- |
| `app.py` | Befehls-Router (`service:…?befehl` → Befehlsklasse) |
| `i18n.py` | Übersetzung, englische msgids + deutscher Katalog |
| `main_thread.py` | `AsyncCallback`: Worker-Thread → Hauptthread |
| `commands/` | eine Klasse pro Aktion, jeweils mit `execute()` |
| `ai/client.py` | OpenAI-kompatibler Client: Chat, Streaming, Modelle, Embeddings |
| `ai/prompts.py` | Prompt-Bausteine, Promptbibliothek |
| `ai/history.py` | Verlaufsdatei |
| `office/document.py` | **alle** UNO-Dokumentzugriffe, je Modul |
| `office/analysis.py` | Strukturkennzahlen für die Analyse |
| `office/extract.py` | Textextraktion aus externen Dateien |
| `rag/` | Chunking, Vektorindex, Indexierung/Retrieval |
| `plugins.py` | Plug-in-Erkennung und die stabile Plug-in-Schnittstelle |
| `ui/` | Panel, Dialoge, Wissensdatenbank- und Plug-in-Dialog |

Zwei Regeln halten das wartbar:

1. **UNO bleibt in `office/`.** Kein anderes Modul importiert
   UNO-Dokument-APIs.
2. **HTTP bleibt in `ai/client.py`.** Ein Client deckt alle Backends ab,
   weil sie alle `/v1/chat/completions` sprechen.

## Grenzen des eingebetteten Python

Das mit LibreOffice gelieferte Python hat **kein pip**, deshalb nutzt die
Erweiterung ausschließlich die Standardbibliothek (`urllib`, `json`,
`zipfile`, `xml.etree`, `math`). Daher ist der Vektorindex reines Python
statt ChromaDB/FAISS, und PDFs werden von LibreOffice selbst gelesen.

## Threading

**Jeder** HTTP-Aufruf läuft im Worker-Thread — `async_task.run()` für die
Befehle, ein eigener Thread im Panel und im Wissensdialog. Jeder Zugriff
auf Controls oder das Dokument geht über `main_thread.run_on_main()` (`com.sun.star.awt.AsyncCallback`)
zurück. Streaming-Aktualisierungen sind auf etwa fünf pro Sekunde
gedrosselt. Ein Verstoß gegen diese Regel ist die wahrscheinlichste
Ursache für Hänger oder Abstürze.

## Bauen und testen

```
make check      # XML-Wohlgeformtheit, Python-Syntax, Versionsgleichstand
make test       # 145 Tests, ohne LibreOffice
make build      # dist/librecompass-<version>.oxt
make install    # unopkg add --force  (danach LibreOffice komplett neu starten)
make uninstall
```

`tests/stubs/unostubs.py` legt Platzhalter für `uno`, `unohelper` und den
gesamten `com.sun.star`-Namensraum an, sodass sich jedes Modul außerhalb
von LibreOffice importieren lässt. `tests/fakes.py` bildet den genutzten
Teil der UNO-API nach — dadurch sind die Calc-/Impress-/Draw-Pfade
prüfbar. `tests/test_client.py` führt echte HTTP-Roundtrips gegen einen
lokalen Wegwerf-Server aus.

Nicht abgedeckt: Menü-Registrierung, Aufbau von Dialogen und Panel,
`AsyncCallback` sowie das Laden externer Dateien über LibreOffice. Dafür
ist ein Rauchtest in echtem LibreOffice nötig.

## Kontextmenü und Tastenkürzel

Beide hängen an denselben `service:`-URLs wie die Menüleiste; ein neuer
Befehl braucht daher keine zusätzliche Verdrahtung, nur Einträge an den
richtigen Stellen.

**Kürzel** setzt `office/shortcuts.py` über
`com.sun.star.ui.GlobalAcceleratorConfiguration` und je Modul über
`ModuleUIConfigurationManagerSupplier` → `getShortCutManager()`.

> 1.1/1.2 lieferten stattdessen eine `Accelerators.xcu` mit. Die Diagnose
> auf LibreOffice 26.2 zeigte, dass davon nichts ankommt: Ein von einer
> Extension geliefertes Accelerator-Fragment wird nicht in die
> Tastaturkonfiguration übernommen. Also die API nutzen, nicht die
> Konfiguration.

**Kontextmenü** lässt sich nicht rein über Konfiguration lösen. `Jobs.xcu`
bindet `org.librecompass.ContextMenuJob` an `onFirstVisibleTask` — das
dokumentierte Startereignis des Job-Frameworks. Der Job (in
`registration.py`) registriert einen `XContextMenuInterceptor` an allen
offenen Dokumenten und meldet sich anschließend am
`com.sun.star.frame.GlobalEventBroadcaster` an, damit auch später
geöffnete Dokumente erfasst werden.

Seit 1.5 hängt das Kontextmenü an **keinem** dieser Teile mehr.
`office/context_config.py` schreibt die Einträge über
`ModuleUIConfigurationManagerSupplier` →
`getSettings("private:resource/popupmenu/…")` → `replaceSettings` →
`store()` in die Kontextmenüs der Module. Das ist dieselbe API-Ebene wie
bei den Kürzeln, überlebt Neustarts und ist unter Extras → Anpassen →
Kontextmenüs bearbeitbar. Der Interceptor bleibt als Laufzeit-Ergänzung.

> Zwei Fallen, in die das Projekt gelaufen ist — beide erinnerungswert:
>
> 1. Jobs an `OnViewCreated`/`OnLoad`/`OnNew` laufen nie an: Das sind
>    Dokumentereignis-Namen, keine Job-Ereignisse. Richtig ist
>    `onFirstVisibleTask`.
> 2. **Niemals `id()` eines UNO-Objekts als Schlüssel verwenden.** PyUNO
>    liefert pro Aufruf ein neues Python-Proxy; `id(getCurrentController())`
>    unterscheidet sich zwischen zwei Aufrufen am selben Dokument.
>    Stattdessen `RuntimeUID`. `ui/context_menu.py` trennt
das in reine Logik (`menu_entries`, `build_menu`,
`model_from_job_arguments` — alle mit Tests) und die UNO-Anbindung. Da der
Job pro Dokument mehrfach auslöst, führt `register_for_model` ein Register
nach Controller-Kennung, damit das Untermenü nicht doppelt erscheint.

Beide Teile sind beim Bauen abschaltbar, weil sie die beiden Bestandteile
mit dem höchsten Risiko auf einer ungetesteten LibreOffice-Version sind:

```
python3 build.py --no-context-menu    # ohne Jobs.xcu
```

`build.py` entfernt die zugehörigen Einträge beim Packen aus
`META-INF/manifest.xml` — eine im Manifest genannte, aber im Archiv
fehlende Datei lässt die Installation scheitern.

## Befehl hinzufügen

1. Neue Klasse in `commands/`, abgeleitet von `Command`, mit `execute()`;
   `needs_document = False` setzen, wenn kein Dokument nötig ist.
2. In `COMMANDS` in `app.py` registrieren.
3. Menüknoten in `Addons.xcu` mit
   `service:org.librecompass.Main?<schlüssel>` und beiden Sprachtiteln.
   Optional in `ENTRIES` in `ui/context_menu.py` und in
   `Accelerators.xcu` ergänzen.
4. UI-Texte als englische msgids plus deutschen Eintrag in `i18n.py`.

## Sprache hinzufügen

Katalog-Dictionary in `CATALOGS` in `i18n.py` ergänzen sowie
`LANGUAGE_CODES` in `ui/dialogs.py` und das zugehörige Bezeichner-Tupel
erweitern. Fehlende Einträge fallen automatisch auf Englisch zurück. Die
Menütitel in `Addons.xcu` tragen eigene `xml:lang`-Werte.

## Release-Checkliste

1. `python3 scripts/bump_version.py X.Y.Z` — setzt `__init__.py`,
   `description.xml` und `update.xml` samt Download-Adresse.
   `make check` vergleicht alle drei.
2. `CHANGELOG.md` fortschreiben (ein Test prüft, dass ein Eintrag zur
   Version existiert).
3. `make check test build`
4. Rauchtest in LibreOffice: Menü in Writer, Calc und Impress vorhanden;
   Panel öffnet; Streaming läuft; Übernehmen je Modul; Rechtsklick-Menü;
   `Tastenkürzel einrichten`.
5. Committen, dann `git tag vX.Y.Z && git push origin vX.Y.Z`. Der
   Release-Workflow prüft, ob der Tag zur Version passt, baut die .oxt und
   hängt sie an ein GitHub-Release.
6. Wer eine ältere Version installiert hat, bekommt die Aktualisierung über
   `update.xml` angeboten, sobald das Release veröffentlicht ist.

Optional: die .oxt vor der Veröffentlichung mit einem Zertifikat signieren —
LibreOffice zeigt unsignierte Erweiterungen mit einer Warnung.
