#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at https://www.apache.org/licenses/LICENSE-2.0
"""Platzhalter OWNER/REPO durch die echte GitHub-Adresse ersetzen.

Nach dem Anlegen des Repositorys einmal aufrufen::

    python3 scripts/set_repo.py maxim/librecompass

Danach zeigen Update-Quelle, Badges und Verweise in der Dokumentation auf
das richtige Repository. Der Aufruf ist wiederholbar (etwa nach einem
Umzug), weil er auch eine bereits gesetzte Adresse erkennt.
"""
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PLACEHOLDER = "OWNER/REPO"
SUFFIXES = (".md", ".xml", ".yml", ".yaml", ".xcu", ".py", ".sh")
# Ausgenommen bleibt, was den Platzhalter als *Wert* führt statt als
# Adresse: die Tests (Prüfwerte) und build.py (prüft, ob der Platzhalter
# noch gesetzt ist - würde die Zeichenkette mitersetzt, meldete die Prüfung
# anschließend immer eine Warnung).
SKIP_DIRS = {".git", "__pycache__", "dist", "node_modules", "tests"}
SKIP_FILES = {"set_repo.py", "build.py"}
# github.com/<owner>/<repo> und raw.githubusercontent.com/<owner>/<repo> -
# fängt auch einen späteren Umzug ab.
URL_PATTERN = re.compile(
    r"(github(?:usercontent)?\.com/)([A-Za-z0-9._-]+/[A-Za-z0-9._-]+)")


def files():
    for base, dirs, names in os.walk(ROOT):
        dirs[:] = [name for name in dirs if name not in SKIP_DIRS]
        for name in sorted(names):
            if name.endswith(SUFFIXES) and name not in SKIP_FILES:
                yield os.path.join(base, name)


def replace(content, target):
    """Adressen auf ``target`` umbiegen; liefert (Text, Anzahl der Änderungen).

    Zwei Durchgänge, damit beides abgedeckt ist: der wörtliche Platzhalter
    (er steht auch in Badge-Adressen von shields.io, die nicht auf
    github.com liegen) und bereits gesetzte GitHub-Adressen - so wirkt der
    Aufruf auch nach einem Umzug des Repositorys.

    Gezählt werden nur tatsächliche Änderungen: Nach dem ersten Durchgang
    trifft das Adressmuster dieselben Stellen erneut, sie stehen dann aber
    bereits richtig.
    """
    if target == PLACEHOLDER:
        return content, 0
    changes = content.count(PLACEHOLDER)
    content = content.replace(PLACEHOLDER, target)

    counter = [0]

    def substitute(match):
        if match.group(2) == target:
            return match.group(0)
        counter[0] += 1
        return match.group(1) + target

    content = URL_PATTERN.sub(substitute, content)
    return content, changes + counter[0]


def main(argv):
    if len(argv) != 2 or argv[1].count("/") != 1:
        print(__doc__)
        print("Aufruf: python3 scripts/set_repo.py <owner>/<repo>")
        return 2
    target = argv[1].strip().strip("/")
    if target == PLACEHOLDER:
        print("Das ist der Platzhalter selbst.")
        return 2

    total_files = 0
    total_hits = 0
    for path in files():
        with open(path, encoding="utf-8") as handle:
            content = handle.read()
        updated, hits = replace(content, target)
        if hits:
            with open(path, "w", encoding="utf-8") as handle:
                handle.write(updated)
            total_files += 1
            total_hits += hits
            print("  %s (%d)" % (os.path.relpath(path, ROOT), hits))
    print("%d Verweise in %d Dateien auf %s gesetzt."
          % (total_hits, total_files, target))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
