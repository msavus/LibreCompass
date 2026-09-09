#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at https://www.apache.org/licenses/LICENSE-2.0
"""Versionsnummer an allen Stellen gleichzeitig setzen.

    python3 scripts/bump_version.py 1.5.0

Betrifft ``pythonpath/librecompass/__init__.py`` (die Quelle der Wahrheit),
``description.xml`` und ``update.xml`` samt Download-Adresse. ``build.py
--check`` vergleicht die drei anschließend - Auseinanderlaufen fällt damit
im Test auf, nicht erst beim Benutzer.
"""
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VERSION_PATTERN = re.compile(r"^\d+\.\d+\.\d+$")


def _edit(relative, pattern, replacement):
    path = os.path.join(ROOT, relative)
    with open(path, encoding="utf-8") as handle:
        content = handle.read()
    updated, count = re.subn(pattern, replacement, content)
    if not count:
        raise SystemExit("Muster nicht gefunden in %s" % relative)
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(updated)
    return count


def bump(version):
    _edit("pythonpath/librecompass/__init__.py",
          r'__version__\s*=\s*"[^"]+"',
          '__version__ = "%s"' % version)
    _edit("description.xml",
          r'<version value="[^"]+"/>',
          '<version value="%s"/>' % version)
    _edit("update.xml",
          r'<version value="[^"]+"/>',
          '<version value="%s"/>' % version)
    _edit("update.xml",
          r'/releases/download/v[^/]+/librecompass-[^"]+\.oxt',
          '/releases/download/v%s/librecompass-%s.oxt' % (version, version))
    return version


def main(argv):
    if len(argv) != 2 or not VERSION_PATTERN.match(argv[1]):
        print(__doc__)
        return 2
    version = bump(argv[1])
    print("Version %s gesetzt. Jetzt: CHANGELOG.md ergänzen, "
          "`make check test build`, committen, taggen." % version)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
