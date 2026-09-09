# -*- coding: utf-8 -*-
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at https://www.apache.org/licenses/LICENSE-2.0
"""Hilfen für Tests: temporäre Einstellungen ohne LibreOffice-Profil."""
import os
import shutil
import tempfile

import context  # noqa: F401

from librecompass.config.settings import DEFAULTS, Settings


class TempSettings(Settings):
    """Einstellungen in einem Wegwerf-Verzeichnis."""

    def __init__(self, **overrides):
        directory = tempfile.mkdtemp(prefix="librecompass-test-")
        data = dict(DEFAULTS)
        data.update(overrides)
        Settings.__init__(self, data, directory)

    def cleanup(self):
        shutil.rmtree(self.directory, ignore_errors=True)


def write_file(directory, name, content, encoding="utf-8"):
    path = os.path.join(directory, name)
    with open(path, "w", encoding=encoding) as handle:
        handle.write(content)
    return path
