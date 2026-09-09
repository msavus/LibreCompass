# -*- coding: utf-8 -*-
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at https://www.apache.org/licenses/LICENSE-2.0
"""Tastenkürzel über die Accelerator-API setzen.

``Accelerators.xcu`` als Konfigurationsfragment einer Extension wird von
LibreOffice offenbar nicht in die Tastaturkonfiguration übernommen (in
26.2 kam nichts an). Der verlässliche Weg ist die dokumentierte
Schnittstelle ``XAcceleratorConfiguration``:

* global   ``com.sun.star.ui.GlobalAcceleratorConfiguration``
* je Modul ``ModuleUIConfigurationManagerSupplier`` ->
  ``getUIConfigurationManager(<Modul>)`` -> ``getShortCutManager()``

Belegungen werden nur gesetzt, wenn die Kombination frei ist oder bereits
LibreCompass gehört - ein fremdes Kürzel wird nie überschrieben.

Aufteilung wie überall: reine Logik (``key_code``, ``modifier_mask``,
``plan``) getrennt von den UNO-Aufrufen (``apply``, ``remove``).
"""
from librecompass.i18n import gettext as _

# com.sun.star.awt.Key.A; Buchstaben liegen fortlaufend dahinter.
KEY_A = 512
# com.sun.star.awt.KeyModifier
SHIFT, MOD1, MOD2 = 1, 2, 4

COMMAND_PREFIX = "service:org.librecompass.Main"
GLOBAL_SERVICE = "com.sun.star.ui.GlobalAcceleratorConfiguration"

MODULES = (
    "com.sun.star.text.TextDocument",
    "com.sun.star.sheet.SpreadsheetDocument",
    "com.sun.star.presentation.PresentationDocument",
    "com.sun.star.drawing.DrawingDocument",
)

# (Buchstabe, Modifikatoren, Befehl, nur global?)
# Strg+Umschalt+Alt: Strg+Umschalt ist von LibreOffice stark belegt,
# Strg+Alt ist auf deutschen Tastaturen AltGr.
SHORTCUTS = (
    ("C", SHIFT | MOD1 | MOD2, "panel", True),
    ("I", SHIFT | MOD1 | MOD2, "improve", False),
    ("R", SHIFT | MOD1 | MOD2, "rewrite", False),
    ("Z", SHIFT | MOD1 | MOD2, "summarize", False),
    ("T", SHIFT | MOD1 | MOD2, "translate", False),
    ("P", SHIFT | MOD1 | MOD2, "custom", False),
)


def key_code(letter):
    """Tastencode für einen Buchstaben (com.sun.star.awt.Key)."""
    letter = (letter or "").upper()
    if len(letter) != 1 or not ("A" <= letter <= "Z"):
        raise ValueError("nur Buchstaben A-Z: %r" % letter)
    return KEY_A + (ord(letter) - ord("A"))


def modifier_mask(*names):
    """Maske aus den Namen shift/mod1/mod2 bauen (für Tests und Lesbarkeit)."""
    values = {"shift": SHIFT, "mod1": MOD1, "mod2": MOD2}
    mask = 0
    for name in names:
        mask |= values[name.lower()]
    return mask


def describe(letter, modifiers):
    """Menschenlesbare Bezeichnung, z. B. Ctrl+Shift+Alt+I."""
    parts = []
    if modifiers & MOD1:
        parts.append("Ctrl")
    if modifiers & SHIFT:
        parts.append("Shift")
    if modifiers & MOD2:
        parts.append("Alt")
    parts.append(letter.upper())
    return "+".join(parts)


def command_url(key):
    return "%s?%s" % (COMMAND_PREFIX, key)


def plan(existing, only_global=False):
    """Was soll gesetzt werden, was ist belegt?

    ``existing`` bildet (Buchstabe, Modifikatoren) auf den bereits
    gebundenen Befehl ab (None = frei). Liefert (zu_setzen, konflikte).
    """
    to_set = []
    conflicts = []
    for letter, modifiers, key, is_global in SHORTCUTS:
        if only_global and not is_global:
            continue
        current = existing.get((letter, modifiers))
        if current and not current.startswith(COMMAND_PREFIX):
            conflicts.append((describe(letter, modifiers), current))
            continue
        to_set.append((letter, modifiers, command_url(key), is_global))
    return to_set, conflicts


# ---- UNO-Anbindung ---------------------------------------------------------
def _key_event(letter, modifiers):
    import uno
    event = uno.createUnoStruct("com.sun.star.awt.KeyEvent")
    event.KeyCode = key_code(letter)
    event.Modifiers = modifiers
    return event


def _configurations(ctx):
    """(Name, XAcceleratorConfiguration)-Paare: global und je Modul."""
    smgr = ctx.ServiceManager
    result = []
    try:
        result.append(("Global",
                       smgr.createInstanceWithContext(GLOBAL_SERVICE, ctx)))
    except Exception:
        pass
    try:
        supplier = smgr.createInstanceWithContext(
            "com.sun.star.ui.ModuleUIConfigurationManagerSupplier", ctx)
    except Exception:
        return result
    for module in MODULES:
        try:
            manager = supplier.getUIConfigurationManager(module)
            result.append((module, manager.getShortCutManager()))
        except Exception:
            continue
    return result


def _current_binding(configuration, letter, modifiers):
    try:
        return str(configuration.getCommandByKeyEvent(
            _key_event(letter, modifiers)))
    except Exception:
        return None  # nicht belegt


def read_existing(configuration, only_global=False):
    existing = {}
    for letter, modifiers, _key, is_global in SHORTCUTS:
        if only_global and not is_global:
            continue
        existing[(letter, modifiers)] = _current_binding(
            configuration, letter, modifiers)
    return existing


def apply(ctx):
    """Kürzel setzen; liefert (gesetzt, konflikte, fehler)."""
    applied = 0
    conflicts = []
    errors = []
    for name, configuration in _configurations(ctx):
        only_global = (name == "Global")
        existing = read_existing(configuration, only_global=only_global)
        to_set, found = plan(existing, only_global=only_global)
        conflicts.extend(found)
        changed = False
        for letter, modifiers, command, _is_global in to_set:
            try:
                configuration.setKeyEvent(_key_event(letter, modifiers),
                                          command)
                applied += 1
                changed = True
            except Exception as exc:
                errors.append("%s %s: %s"
                              % (name, describe(letter, modifiers), exc))
        if changed:
            try:
                configuration.store()
            except Exception as exc:
                errors.append("%s: %s" % (name, exc))
    # Doppelte Konfliktmeldungen (global + Module) zusammenfassen
    unique = []
    for entry in conflicts:
        if entry not in unique:
            unique.append(entry)
    return applied, unique, errors


def remove(ctx):
    """Alle LibreCompass-Kürzel wieder entfernen; liefert die Anzahl."""
    removed = 0
    for name, configuration in _configurations(ctx):
        changed = False
        for letter, modifiers, _key, _is_global in SHORTCUTS:
            current = _current_binding(configuration, letter, modifiers)
            if not current or not current.startswith(COMMAND_PREFIX):
                continue
            try:
                configuration.removeKeyEvent(_key_event(letter, modifiers))
                removed += 1
                changed = True
            except Exception:
                continue
        if changed:
            try:
                configuration.store()
            except Exception:
                pass
    return removed


def installed_count(ctx):
    """Wie viele LibreCompass-Kürzel sind aktuell gebunden?"""
    count = 0
    for _name, configuration in _configurations(ctx):
        for letter, modifiers, _key, _is_global in SHORTCUTS:
            current = _current_binding(configuration, letter, modifiers)
            if current and current.startswith(COMMAND_PREFIX):
                count += 1
    return count


def summary(applied, conflicts, errors):
    """Ergebnismeldung für den Benutzer."""
    lines = [_("{count} shortcuts assigned.").format(count=applied)]
    if conflicts:
        lines.append("")
        lines.append(_("Left untouched because already in use:"))
        for combination, command in conflicts:
            lines.append("  %s -> %s" % (combination, command))
    if errors:
        lines.append("")
        lines.append(_("Errors:"))
        lines.extend("  " + entry for entry in errors[:8])
    return "\n".join(lines)
