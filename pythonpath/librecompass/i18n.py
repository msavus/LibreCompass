# -*- coding: utf-8 -*-
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at https://www.apache.org/licenses/LICENSE-2.0
"""Mehrsprachigkeit / internationalization.

Englische Zeichenketten sind die msgids, Deutsch liegt als Katalog vor.
Die Sprache kommt aus ``settings.language`` ("auto", "en", "de"); bei
"auto" wird das UI-Gebietsschema von LibreOffice gelesen.

Nutzung::

    from librecompass.i18n import gettext as _
    _("Send")
    _("Model: {name}").format(name="qwen3")

Neue Sprache ergänzen: Kürzel in ``CATALOGS`` eintragen; fehlende
Einträge fallen automatisch auf Englisch zurück.
"""

DE = {
    # Menü / menu
    "LibreCompass panel": "LibreCompass-Panel",
    "Improve selection": "Auswahl verbessern",
    "Rewrite selection …": "Auswahl umschreiben …",
    "Summarize": "Zusammenfassen",
    "Translate …": "Übersetzen …",
    "Custom prompt …": "Eigener Prompt …",
    "Analyze document": "Dokument analysieren",
    "Knowledge base …": "Wissensdatenbank …",
    "Settings …": "Einstellungen …",
    "Set up context menu": "Kontextmenü einrichten",
    "Remove context menu": "Kontextmenü entfernen",
    "Context menu added to {count} menus.":
        "Kontextmenü in {count} Menüs eingetragen.",
    "{count} context menu entries removed.":
        "{count} Kontextmenü-Einträge entfernt.",
    "Also active in the current document.":
        "Im aktuellen Dokument zusätzlich sofort aktiv.",
    "Interceptor:": "Interceptor:",
    "Right-click in a document to use it. In already open documents it may "
    "take a restart.":
        "Im Dokument rechtsklicken. In bereits geöffneten Dokumenten "
        "eventuell erst nach einem Neustart.",
    "Context menu (persistent):": "Kontextmenü (dauerhaft):",
    "Interceptor active here:": "Interceptor hier aktiv:",
    "Last registration error:": "Letzter Registrierungsfehler:",
    "not installed": "nicht eingerichtet",
    "The context menu is not set up. Use LibreCompass > Set up context "
    "menu.":
        "Das Kontextmenü ist nicht eingerichtet. LibreCompass > "
        "Kontextmenü einrichten wählen.",
    "Diagnostics …": "Diagnose …",
    "Set up shortcuts": "Tastenkürzel einrichten",
    "Remove shortcuts": "Tastenkürzel entfernen",
    "{count} shortcuts assigned.": "{count} Tastenkürzel zugewiesen.",
    "{count} shortcuts removed.": "{count} Tastenkürzel entfernt.",
    "Left untouched because already in use:":
        "Unverändert gelassen, weil bereits belegt:",
    "Errors:": "Fehler:",
    "could not be read": "nicht lesbar",
    "other bindings on these keys:": "andere Belegungen auf diesen Tasten:",
    "Startup job actually ran:": "Startjob tatsächlich gelaufen:",
    "Shortcuts are not assigned. Use LibreCompass > Set up shortcuts.":
        "Es sind keine Kürzel zugewiesen. LibreCompass > Tastenkürzel "
        "einrichten wählen.",
    "The startup job never ran. The context menu is attached on first use "
    "instead - run any LibreCompass command, then right-click.":
        "Der Startjob lief nie. Das Kontextmenü wird stattdessen bei der "
        "ersten Benutzung angehängt - einen beliebigen LibreCompass-Befehl "
        "ausführen, dann rechtsklicken.",
    # Diagnose / diagnostics
    "LibreCompass – Diagnostics": "LibreCompass – Diagnose",
    "Keyboard shortcuts": "Tastenkürzel",
    "Context menu job": "Kontextmenü-Job",
    "registered": "registriert",
    "MISSING": "FEHLT",
    "Bound to events:": "Gebunden an Ereignisse:",
    "Active in this document:": "In diesem Dokument aktiv:",
    "Module:": "Modul:",
    "yes": "ja",
    "no": "nein",
    "What to do:": "Was tun:",
    "Shortcuts did not register. Assign them yourself under Tools > "
    "Customize > Keyboard (category Add-ons).":
        "Die Kürzel wurden nicht registriert. Unter Extras > Anpassen > "
        "Tastatur (Bereich Add-Ons) selbst zuweisen.",
    "The context-menu job is not registered. Reinstall the extension and "
    "restart LibreOffice completely.":
        "Der Kontextmenü-Job ist nicht registriert. Extension neu "
        "installieren und LibreOffice komplett neu starten.",
    # allgemein / general
    "LibreCompass": "LibreCompass",
    "LibreCompass – Error": "LibreCompass – Fehler",
    "OK": "OK",
    "Cancel": "Abbrechen",
    "Close": "Schließen",
    "Please select text or cells first.":
        "Bitte zuerst Text bzw. Zellen markieren.",
    "Please open a document first (Writer, Calc, Impress or Draw).":
        "Bitte zuerst ein Dokument öffnen (Writer, Calc, Impress oder Draw).",
    "The document is empty.": "Das Dokument ist leer.",
    "Unknown command: {name}": "Unbekannter Befehl: {name}",
    "Applying is not supported in this module.":
        "Automatisches Übernehmen wird in diesem Modul nicht unterstützt.",
    "Applying is not supported in this module – please use the "
    "\"New document\" mode.":
        "Übernehmen wird in diesem Modul nicht unterstützt – bitte den "
        "Modus „Neues Dokument\" verwenden.",
    "LibreCompass: waiting for the model ({model}) …":
        "LibreCompass: warte auf Antwort des Modells ({model}) …",
    # Panel
    "Model:": "Modell:",
    "Prompt:": "Prompt:",
    "Context:": "Kontext:",
    "Answer:": "Antwort:",
    "Apply as:": "Übernehmen als:",
    "Insert": "Einfügen",
    "Save": "Speichern",
    "Send": "Senden",
    "Stop": "Stopp",
    "Clear chat": "Chat leeren",
    "Apply": "Übernehmen",
    "History": "Verlauf",
    "Plugins …": "Plug-ins …",
    "Chat mode (keeps history)": "Chat-Modus (Verlauf)",
    "Selection": "Auswahl",
    "Whole document": "Gesamtes Dokument",
    "Knowledge base": "Wissensdatenbank",
    "No context": "Ohne Kontext",
    "Replace selection": "Auswahl ersetzen",
    "Insert at cursor": "Am Cursor einfügen",
    "New document": "Neues Dokument",
    "Please enter a prompt first.": "Bitte zuerst einen Prompt eingeben.",
    "No answer to apply yet.": "Keine Antwort zum Übernehmen vorhanden.",
    "No prompt to save.": "Kein Prompt zum Speichern vorhanden.",
    "Save prompt": "Prompt speichern",
    "Name for the prompt library:": "Name für die Promptbibliothek:",
    "No history yet.": "Noch kein Verlauf vorhanden.",
    "You:": "Du:",
    "Assistant:": "Assistent:",
    # Befehle / commands
    "Rewrite selection": "Auswahl umschreiben",
    "How should the selected text be rewritten?":
        "Wie soll der markierte Text umgeschrieben werden?",
    "Translate": "Übersetzen",
    "Target language:": "Zielsprache:",
    "English": "Englisch",
    "Custom prompt": "Eigener Prompt",
    "Instruction (applied to the selection; without a selection the "
    "answer is inserted):":
        "Anweisung (wird auf die Auswahl angewandt; ohne Auswahl wird die "
        "Antwort eingefügt):",
    "Summary:": "Zusammenfassung:",
    # Einstellungen / settings
    "LibreCompass – Settings": "LibreCompass – Einstellungen",
    "Endpoint (OpenAI-compatible, e.g. Ollama):":
        "Endpoint (OpenAI-kompatibel, z. B. Ollama):",
    "Chat model:": "Chat-Modell:",
    "Embedding model:": "Embedding-Modell:",
    "Temperature:": "Temperatur:",
    "Max. tokens:": "Max. Tokens:",
    "Record replacements as tracked changes":
        "Ersetzungen als nachverfolgte Änderungen einfügen",
    "Streaming in the panel (disable if it misbehaves)":
        "Streaming im Panel (bei Problemen abschalten)",
    "Language:": "Sprache:",
    "Automatic": "Automatisch",
    "Takes effect after reopening the panel.":
        "Wirkt nach dem erneuten Öffnen des Panels.",
    # Wissensdatenbank / knowledge base
    "LibreCompass – Knowledge base": "LibreCompass – Wissensdatenbank",
    "Indexed sources:": "Indexierte Quellen:",
    "Add file …": "Datei hinzufügen …",
    "Add folder …": "Ordner hinzufügen …",
    "Remove": "Entfernen",
    "Rebuild index": "Index neu aufbauen",
    "Clear index": "Index leeren",
    "Path of the file or folder to index:":
        "Pfad der Datei bzw. des Ordners zum Indexieren:",
    "{chunks} chunks from {sources} sources, embedding model {model}":
        "{chunks} Abschnitte aus {sources} Quellen, Embedding-Modell {model}",
    "The index is empty.": "Der Index ist leer.",
    "Indexing …": "Indexierung läuft …",
    "A request is already running. Please wait for it to finish.":
        "Es läuft bereits eine Anfrage. Bitte abwarten.",
    "Indexed {count} chunks.": "{count} Abschnitte indexiert.",
    "Nothing to index – no readable text found.":
        "Nichts zu indexieren – kein lesbarer Text gefunden.",
    "The knowledge base is empty. Please index sources first.":
        "Die Wissensdatenbank ist leer. Bitte zuerst Quellen indexieren.",
    "Sources used:": "Verwendete Quellen:",
    # Plug-ins
    "LibreCompass – Plugins": "LibreCompass – Plug-ins",
    "Installed plugins:": "Installierte Plug-ins:",
    "No plugins installed. Place .py files in:":
        "Keine Plug-ins installiert. .py-Dateien ablegen unter:",
    "Insert prompt": "Prompt einfügen",
    "Run": "Ausführen",
    "Plugin \"{name}\" has no prompt.":
        "Plug-in „{name}\" hat keinen Prompt.",
    "Plugin \"{name}\" is not runnable.":
        "Plug-in „{name}\" ist nicht ausführbar.",
    # Dokumentanalyse / document analysis
    "Document analysis": "Dokumentanalyse",
    "Structure": "Struktur",
    "Observations": "Beobachtungen",
    "Module": "Modul",
    "Paragraphs": "Absätze",
    "Words": "Wörter",
    "Characters": "Zeichen",
    "Headings": "Überschriften",
    "Tables": "Tabellen",
    "Images": "Bilder",
    "Sheets": "Tabellenblätter",
    "Filled cells": "Gefüllte Zellen",
    "Formulas": "Formeln",
    "Slides": "Folien",
    "Pages": "Seiten",
    "Shapes with text": "Formen mit Text",
    "Outline": "Gliederung",
    "Analyzing document …": "Dokument wird analysiert …",
}

CATALOGS = {"de": DE, "en": {}}

_current = {"lang": "en"}


def set_language(code):
    """Aktive Sprache setzen; unbekannte Kürzel fallen auf Englisch zurück."""
    code = (code or "en").split("-")[0].split("_")[0].lower()
    _current["lang"] = code if code in CATALOGS else "en"
    return _current["lang"]


def language():
    return _current["lang"]


def gettext(message):
    return CATALOGS.get(_current["lang"], {}).get(message, message)


def office_locale(ctx):
    """UI-Gebietsschema von LibreOffice lesen (z. B. "de-DE")."""
    try:
        smgr = ctx.ServiceManager
        provider = smgr.createInstanceWithContext(
            "com.sun.star.configuration.ConfigurationProvider", ctx)
        import uno
        argument = uno.createUnoStruct("com.sun.star.beans.PropertyValue")
        argument.Name = "nodepath"
        argument.Value = "/org.openoffice.Setup/L10N"
        access = provider.createInstanceWithArguments(
            "com.sun.star.configuration.ConfigurationAccess", (argument,))
        return str(access.getByName("ooLocale"))
    except Exception:
        return "en"


def apply_settings(ctx, settings):
    """Sprache aus den Einstellungen bzw. dem Gebietsschema übernehmen."""
    configured = str(getattr(settings, "language", "auto") or "auto").lower()
    if configured in ("auto", ""):
        return set_language(office_locale(ctx))
    return set_language(configured)
