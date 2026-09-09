# -*- coding: utf-8 -*-
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at https://www.apache.org/licenses/LICENSE-2.0
"""Gemeinsame Testvorbereitung: Stubs installieren, Paketpfad setzen."""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

for path in (os.path.join(HERE, "stubs"), HERE,
             os.path.join(ROOT, "pythonpath")):
    if path not in sys.path:
        sys.path.insert(0, path)

import unostubs  # noqa: E402

unostubs.install()
