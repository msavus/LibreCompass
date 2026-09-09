#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at https://www.apache.org/licenses/LICENSE-2.0
"""Packt die Erweiterung als dist/librecompass-<version>.oxt (ein ZIP).

Aufrufe::

    python3 build.py            # prüfen und packen
    python3 build.py --check    # nur prüfen (XML, Python-Syntax, Version)

Die Version steht an einer Stelle (pythonpath/librecompass/__init__.py) und
wird gegen description.xml geprüft, damit beides nicht auseinanderläuft.
"""
import argparse
import os
import py_compile
import re
import sys
import tempfile
import zipfile
from xml.dom import minidom

NAME = "librecompass"
ROOT = os.path.dirname(os.path.abspath(__file__))

STATIC_FILES = [
    "description.xml",
    "pkg-description.en.txt",
    "pkg-description.de.txt",
    "Addons.xcu",
    "registration.py",
]
# Abschaltbare Bestandteile: Wird eine dieser Dateien weggelassen, muss auch
# ihr Eintrag aus META-INF/manifest.xml verschwinden - eine im Manifest
# genannte, aber fehlende Datei lässt die Installation scheitern.
OPTIONAL_FILES = {
    "context-menu": "Jobs.xcu",
}
DOC_FILES = ["README.md", "README.de.md", "CHANGELOG.md", "LICENSE"]
XML_FILES = ["description.xml", "Addons.xcu", "Jobs.xcu",
             "META-INF/manifest.xml"]


def version():
    path = os.path.join(ROOT, "pythonpath", NAME, "__init__.py")
    with open(path, encoding="utf-8") as handle:
        match = re.search(r'__version__\s*=\s*"([^"]+)"', handle.read())
    if not match:
        raise SystemExit("Version nicht gefunden in %s" % path)
    return match.group(1)


def python_files():
    for base, _dirs, files in os.walk(os.path.join(ROOT, "pythonpath")):
        if "__pycache__" in base:
            continue
        for name in sorted(files):
            if name.endswith(".py"):
                yield os.path.relpath(os.path.join(base, name), ROOT)


def example_files():
    directory = os.path.join(ROOT, "examples")
    if not os.path.isdir(directory):
        return
    for base, _dirs, files in os.walk(directory):
        for name in sorted(files):
            if name.endswith(".py") or name.endswith(".md"):
                yield os.path.relpath(os.path.join(base, name), ROOT)


def check():
    """XML-Wohlgeformtheit, Python-Syntax und Versionsgleichstand prüfen."""
    problems = []
    for relative in XML_FILES:
        try:
            minidom.parse(os.path.join(ROOT, relative))
        except Exception as exc:
            problems.append("%s: %s" % (relative, exc))

    declared = version()
    for relative in ("description.xml", "update.xml"):
        try:
            document = minidom.parse(os.path.join(ROOT, relative))
            in_xml = document.getElementsByTagName(
                "version")[0].getAttribute("value")
            if in_xml != declared:
                problems.append("Version: __init__.py=%s, %s=%s"
                                % (declared, relative, in_xml))
        except Exception as exc:
            problems.append("%s: %s" % (relative, exc))

    # Kein Fehler, aber eine Warnung wert: Die Update-Quelle zeigt noch auf
    # den Platzhalter und damit ins Leere.
    warnings = []
    try:
        with open(os.path.join(ROOT, "description.xml"),
                  encoding="utf-8") as handle:
            if "OWNER/REPO" in handle.read():
                warnings.append(
                    "Repository-Platzhalter noch gesetzt - vor der "
                    "Veröffentlichung `python3 scripts/set_repo.py "
                    "<owner>/<repo>` ausführen.")
    except Exception:
        pass

    with tempfile.TemporaryDirectory() as scratch:
        for number, relative in enumerate(
                ["registration.py"] + list(python_files())):
            path = os.path.join(ROOT, relative)
            cache = os.path.join(scratch, "check%d.pyc" % number)
            try:
                py_compile.compile(path, cfile=cache, doraise=True)
            except py_compile.PyCompileError as exc:
                problems.append("%s: %s" % (relative, exc.msg.strip()))

    for problem in problems:
        print("FEHLER:", problem)
    if problems:
        return False
    for warning in warnings:
        print("WARNUNG:", warning)
    print("Prüfung bestanden (Version %s)" % declared)
    return True


def manifest_without(excluded):
    """manifest.xml ohne die Einträge der ausgelassenen Dateien."""
    with open(os.path.join(ROOT, "META-INF", "manifest.xml"),
              encoding="utf-8") as handle:
        content = handle.read()
    for name in excluded:
        pattern = (r"\s*<manifest:file-entry[^>]*?manifest:full-path=\""
                   + re.escape(name) + r"\"\s*/>")
        content = re.sub(pattern, "", content)
    return content


def package(excluded=()):
    release = version()
    dist = os.path.join(ROOT, "dist")
    os.makedirs(dist, exist_ok=True)
    target = os.path.join(dist, "%s-%s.oxt" % (NAME, release))
    members = list(STATIC_FILES)
    members += [name for name in OPTIONAL_FILES.values()
                if name not in excluded]
    members += [name for name in DOC_FILES
                if os.path.exists(os.path.join(ROOT, name))]
    members += sorted(python_files())
    members += sorted(example_files())
    with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as archive:
        for relative in members:
            archive.write(os.path.join(ROOT, relative),
                          relative.replace(os.sep, "/"))
        archive.writestr("META-INF/manifest.xml",
                         manifest_without(excluded))
    if excluded:
        print("ausgelassen: %s" % ", ".join(sorted(excluded)))
    print("geschrieben: %s (%d Dateien)" % (target, len(members) + 1))
    return target


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true",
                        help="nur prüfen, nicht packen")
    parser.add_argument("--no-context-menu", action="store_true",
                        help="ohne Kontextmenü (Jobs.xcu) packen")
    arguments = parser.parse_args()
    if not check():
        return 1
    if arguments.check:
        return 0
    excluded = set()
    if arguments.no_context_menu:
        excluded.add(OPTIONAL_FILES["context-menu"])
    package(excluded)
    return 0


if __name__ == "__main__":
    sys.exit(main())
