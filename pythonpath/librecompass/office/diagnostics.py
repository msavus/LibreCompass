# -*- coding: utf-8 -*-
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at https://www.apache.org/licenses/LICENSE-2.0
"""Diagnose: was ist von der Extension tatsächlich in LibreOffice angekommen?

Menüeinträge, Tastenkürzel und Kontextmenü hängen an drei verschiedenen
Mechanismen (Addons.xcu, Accelerators.xcu, Jobs.xcu + Interceptor). Wenn
einer davon still ausfällt, ist von außen nicht erkennbar, welcher. Dieses
Modul liest die laufende Konfiguration und sagt es.

Die Auswertung (``build_report``) ist von den UNO-Zugriffen (``collect``)
getrennt, damit sie ohne LibreOffice testbar bleibt.
"""
from librecompass import __version__, runtime
from librecompass.i18n import gettext as _
from librecompass.office import context_config, shortcuts
from librecompass.ui import context_menu

ACCELERATOR_MODULES = (
    ("Writer", "com.sun.star.text.TextDocument"),
    ("Calc", "com.sun.star.sheet.SpreadsheetDocument"),
    ("Impress", "com.sun.star.presentation.PresentationDocument"),
    ("Draw", "com.sun.star.drawing.DrawingDocument"),
)

JOB_NAME = "LibreCompassContextMenu"
COMMAND_PREFIX = "service:org.librecompass.Main"


# ---- UNO-Zugriffe -----------------------------------------------------------
def _config(ctx, nodepath):
    """Konfigurationsknoten lesen; None, wenn nicht vorhanden."""
    import uno
    try:
        provider = ctx.ServiceManager.createInstanceWithContext(
            "com.sun.star.configuration.ConfigurationProvider", ctx)
        argument = uno.createUnoStruct("com.sun.star.beans.PropertyValue")
        argument.Name = "nodepath"
        argument.Value = nodepath
        return provider.createInstanceWithArguments(
            "com.sun.star.configuration.ConfigurationAccess", (argument,))
    except Exception:
        return None


def _keys_with_our_commands(node):
    """Namen der Tastenkombinationen, die auf LibreCompass zeigen."""
    if node is None:
        return []
    found = []
    try:
        names = node.getElementNames()
    except Exception:
        return []
    for name in names:
        try:
            command = str(node.getByName(name).getByName("Command"))
        except Exception:
            continue
        if command.startswith(COMMAND_PREFIX):
            found.append(name)
    return sorted(found)


def _office_version(ctx):
    node = _config(ctx, "/org.openoffice.Setup/Product")
    if node is None:
        return "?"
    try:
        return "%s %s" % (node.getByName("ooName"),
                          node.getByName("ooSetupVersionAboutBox"))
    except Exception:
        return "?"


def _bindings(ctx):
    """Belegungen über die Accelerator-API lesen: (gebunden, gesamt) je Ebene.

    Über die API statt über die Konfiguration, weil genau das die Ebene ist,
    auf der LibreOffice die Tastatur tatsächlich auflöst.
    """
    result = {}
    try:
        configurations = shortcuts._configurations(ctx)
    except Exception:
        return result
    for name, configuration in configurations:
        ours = []
        total = 0
        for letter, modifiers, _key, is_global in shortcuts.SHORTCUTS:
            if name == "Global" and not is_global:
                continue
            current = shortcuts._current_binding(configuration, letter,
                                                 modifiers)
            if current:
                total += 1
                if current.startswith(COMMAND_PREFIX):
                    ours.append(shortcuts.describe(letter, modifiers))
        label = name.rsplit(".", 1)[-1] if "." in name else name
        result[label] = (ours, total)
    return result


def collect(ctx, doc=None, settings=None):
    """Rohbefunde einsammeln (alles defensiv, nichts darf werfen)."""
    facts = {
        "version": __version__,
        "office": _office_version(ctx),
        "bindings": _bindings(ctx),
        "job_registered": False,
        "job_events": [],
        "job_ran": None,
        "interceptor_here": False,
        "interceptor_error": context_menu.last_error(),
        "context_modules": [],
        "module": None,
    }
    try:
        facts["context_modules"] = context_config.installed_modules(ctx)
    except Exception:
        pass
    if settings is not None:
        marks = runtime.load(settings)
        facts["job_ran"] = marks.get("startup_job_at")
        facts["listener"] = marks.get("listener_attached")

    jobs = _config(ctx, "/org.openoffice.Office.Jobs/Jobs")
    if jobs is not None:
        try:
            facts["job_registered"] = jobs.hasByName(JOB_NAME)
        except Exception:
            pass
    events = _config(ctx, "/org.openoffice.Office.Jobs/Events")
    if events is not None:
        try:
            for name in events.getElementNames():
                try:
                    joblist = events.getByName(name).getByName("JobList")
                    if joblist.hasByName(JOB_NAME):
                        facts["job_events"].append(name)
                except Exception:
                    continue
        except Exception:
            pass

    if doc is not None:
        facts["module"] = doc.doc_type()
        facts["interceptor_here"] = context_menu.is_registered_for(doc.model)
    return facts


# ---- Auswertung ---------------------------------------------------------------
def build_report(facts):
    """Aus den Rohbefunden einen lesbaren Bericht bauen."""
    lines = ["LibreCompass %s" % facts.get("version", "?"),
             "LibreOffice: %s" % facts.get("office", "?"),
             ""]

    bindings = facts.get("bindings") or {}
    ours_total = sum(len(ours) for ours, _t in bindings.values())
    if not bindings:
        state = _("could not be read")
    elif ours_total:
        state = _("registered")
    else:
        state = _("MISSING")
    lines.append("%s: %s" % (_("Keyboard shortcuts"), state))
    for label in sorted(bindings):
        ours, total = bindings[label]
        lines.append("  %-22s %s (%s %d)"
                     % (label + ":", ", ".join(ours) if ours else "-",
                        _("other bindings on these keys:"), total - len(ours)))

    lines.append("")
    modules = facts.get("context_modules") or []
    lines.append("%s %s" % (_("Context menu (persistent):"),
                            ", ".join(modules) if modules
                            else _("not installed")))
    lines.append("  %s %s" % (_("Interceptor active here:"),
                              _("yes") if facts.get("interceptor_here")
                              else _("no")))
    if facts.get("interceptor_error"):
        lines.append("  %s %s" % (_("Last registration error:"),
                                  facts["interceptor_error"]))
    lines.append("  %s %s" % (_("Context menu job"),
                              _("registered") if facts.get("job_registered")
                              else _("MISSING")))
    events = facts.get("job_events") or []
    lines.append("  %s %s" % (_("Bound to events:"),
                              ", ".join(events) if events else "-"))
    lines.append("  %s %s" % (_("Startup job actually ran:"),
                              facts.get("job_ran") or _("no")))
    if facts.get("module"):
        lines.append("  %s %s" % (_("Module:"), facts["module"]))

    hints = []
    if not ours_total:
        hints.append(_("Shortcuts are not assigned. Use LibreCompass > "
                       "Set up shortcuts."))
    if not modules:
        hints.append(_("The context menu is not set up. Use LibreCompass > "
                       "Set up context menu."))
    if hints:
        lines.append("")
        lines.append(_("What to do:"))
        for hint in hints:
            lines.append("- " + hint)
    return "\n".join(lines)
