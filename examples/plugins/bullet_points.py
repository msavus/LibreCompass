# -*- coding: utf-8 -*-
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at https://www.apache.org/licenses/LICENSE-2.0
"""Beispiel-Plug-in: Prompt-Aktion.

Kopieren nach <Profil>/user/librecompass/plugins/ - danach erscheint es im
Plug-in-Dialog und der Prompt lässt sich ins Panel übernehmen.
"""
NAME = "Bullet points"
DESCRIPTION = "Turns the selection into a concise bullet list"
PROMPT = ("Rewrite the following text as a concise bullet list. "
          "One idea per bullet, no sub-bullets.")
