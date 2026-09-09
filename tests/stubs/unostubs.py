# -*- coding: utf-8 -*-
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at https://www.apache.org/licenses/LICENSE-2.0
"""UNO-Ersatzmodule für Tests ohne LibreOffice.

``install()`` registriert Platzhalter für ``uno``, ``unohelper`` und den
gesamten ``com.sun.star``-Namensraum. Damit lassen sich alle Module der
Extension importieren und die Logik testen – auch die modulspezifischen
Pfade in ``office/document.py``, die sonst nur in LibreOffice laufen.

Die Platzhalter emulieren keine UNO-Semantik; sie machen Importe möglich.
Verhalten wird über die Attrappen in ``tests/fakes.py`` geprüft.
"""
import importlib.abc
import importlib.machinery
import sys
import types


class _AutoModule(types.ModuleType):
    """Modul, das unbekannte Attribute als Platzhalterklassen erzeugt."""

    def __getattr__(self, name):
        if name.startswith("__"):
            raise AttributeError(name)
        placeholder = type(str(name), (object,), {"__module__": self.__name__})
        setattr(self, name, placeholder)
        return placeholder


class _ComStarFinder(importlib.abc.MetaPathFinder, importlib.abc.Loader):
    """Erzeugt ``com``, ``com.sun``, ``com.sun.star`` und alle Unterpakete."""

    PREFIXES = ("com", "com.sun", "com.sun.star")

    def find_spec(self, fullname, path=None, target=None):
        if fullname in self.PREFIXES or fullname.startswith("com.sun.star."):
            return importlib.machinery.ModuleSpec(fullname, self,
                                                  is_package=True)
        return None

    def create_module(self, spec):
        module = _AutoModule(spec.name)
        module.__path__ = []
        return module

    def exec_module(self, module):
        return None


class UnoStruct(object):
    """Ersatz für UNO-Strukturen: beliebige Attribute setzbar."""

    def __init__(self, name=""):
        self._name = name

    def __repr__(self):
        return "<UnoStruct %s>" % self._name


class UnoEnum(object):
    def __init__(self, type_name, value):
        self.typeName = type_name
        self.value = value

    def __eq__(self, other):
        return (isinstance(other, UnoEnum)
                and (self.typeName, self.value) == (other.typeName,
                                                    other.value))

    def __hash__(self):
        return hash((self.typeName, self.value))


def _make_uno_module():
    module = types.ModuleType("uno")

    def create_uno_struct(name, *args, **kwargs):
        return UnoStruct(name)

    def file_url_to_system_path(url):
        return url[7:] if url.startswith("file://") else url

    def system_path_to_file_url(path):
        return "file://" + path

    module.createUnoStruct = create_uno_struct
    module.fileUrlToSystemPath = file_url_to_system_path
    module.systemPathToFileUrl = system_path_to_file_url
    module.Enum = lambda type_name, value: UnoEnum(type_name, value)
    module.getComponentContext = lambda: None
    return module


def _make_unohelper_module():
    module = types.ModuleType("unohelper")

    class Base(object):
        pass

    class ImplementationHelper(object):
        def __init__(self):
            self.implementations = []

        def addImplementation(self, factory, name, services):
            self.implementations.append((factory, name, services))

    module.Base = Base
    module.ImplementationHelper = ImplementationHelper
    return module


def install():
    """Stubs in sys.modules eintragen (idempotent)."""
    if not any(isinstance(finder, _ComStarFinder) for finder in sys.meta_path):
        sys.meta_path.insert(0, _ComStarFinder())
    sys.modules.setdefault("uno", _make_uno_module())
    sys.modules.setdefault("unohelper", _make_unohelper_module())
