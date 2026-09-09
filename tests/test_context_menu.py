# -*- coding: utf-8 -*-
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at https://www.apache.org/licenses/LICENSE-2.0
"""Kontextmenü: Menüaufbau und Job-Argumentauswertung."""
import unittest

import context  # noqa: F401
from fakes import (FakeActionTriggerContainer, FakeContextMenuEvent,
                   FakeNamedValue, FakeWriterDocument)

from librecompass import i18n
from librecompass.ui import context_menu


class MenuBuildTest(unittest.TestCase):
    def tearDown(self):
        i18n.set_language("en")

    def test_entries_have_service_urls(self):
        entries = context_menu.menu_entries()
        commands = [command for _label, command in entries if command]
        self.assertIn("service:org.librecompass.Main?improve", commands)
        self.assertIn("service:org.librecompass.Main?panel", commands)

    def test_entries_follow_language(self):
        i18n.set_language("de")
        labels = [label for label, _c in context_menu.menu_entries() if label]
        self.assertIn("Auswahl verbessern", labels)
        i18n.set_language("en")
        labels = [label for label, _c in context_menu.menu_entries() if label]
        self.assertIn("Improve selection", labels)

    def test_entries_contain_a_separator(self):
        self.assertIn((None, None), context_menu.menu_entries())

    def test_build_menu_appends_separator_and_root(self):
        container = FakeActionTriggerContainer(existing=3)
        root = context_menu.build_menu(container,
                                       context_menu.menu_entries())
        self.assertEqual(container.getCount(), 5)
        self.assertTrue(container.getByIndex(3).is_separator)
        self.assertIs(container.getByIndex(4), root)
        self.assertEqual(root.Text, "LibreCompass")

    def test_submenu_holds_all_commands(self):
        container = FakeActionTriggerContainer()
        root = context_menu.build_menu(container,
                                       context_menu.menu_entries())
        submenu = root.SubContainer
        self.assertEqual(submenu.getCount(), len(context_menu.ENTRIES))
        commands = [item.CommandURL for item in submenu.items
                    if not item.is_separator]
        self.assertEqual(len(commands), len(context_menu.ENTRIES) - 1)
        self.assertTrue(all(url.startswith("service:") for url in commands))

    def test_submenu_separator_position_is_kept(self):
        container = FakeActionTriggerContainer()
        root = context_menu.build_menu(container,
                                       context_menu.menu_entries())
        flags = [item.is_separator for item in root.SubContainer.items]
        expected = [key is None for _m, key in context_menu.ENTRIES]
        self.assertEqual(flags, expected)

    def test_menu_is_appended_to_existing_entries(self):
        container = FakeActionTriggerContainer(existing=2)
        before = [container.getByIndex(0), container.getByIndex(1)]
        context_menu.build_menu(container, context_menu.menu_entries())
        self.assertIs(container.getByIndex(0), before[0])
        self.assertIs(container.getByIndex(1), before[1])


class InterceptorTest(unittest.TestCase):
    def test_modifies_menu_and_reports_it(self):
        container = FakeActionTriggerContainer()
        result = context_menu.Interceptor().notifyContextMenuExecute(
            FakeContextMenuEvent(container))
        self.assertEqual(result, context_menu.CONTINUE_MODIFIED)
        self.assertEqual(container.getCount(), 2)

    def test_failure_leaves_menu_alone(self):
        class Broken(object):
            def createInstance(self, service):
                raise RuntimeError("no factory here")

        result = context_menu.Interceptor().notifyContextMenuExecute(
            FakeContextMenuEvent(Broken()))
        self.assertEqual(result, context_menu.IGNORED)


class _Controller(object):
    def __init__(self):
        self.interceptors = []

    def registerContextMenuInterceptor(self, interceptor):
        self.interceptors.append(interceptor)


class _Model(object):
    def __init__(self, controller):
        self._controller = controller

    def getCurrentController(self):
        return self._controller


class RegistrationTest(unittest.TestCase):
    def setUp(self):
        context_menu._REGISTERED.clear()

    def tearDown(self):
        context_menu._REGISTERED.clear()

    def test_registers_once_per_controller(self):
        controller = _Controller()
        model = _Model(controller)
        self.assertTrue(context_menu.register_for_model(model))
        self.assertFalse(context_menu.register_for_model(model))
        self.assertEqual(len(controller.interceptors), 1)

    def test_no_model(self):
        self.assertFalse(context_menu.register_for_model(None))

    def test_model_without_controller(self):
        self.assertFalse(context_menu.register_for_model(_Model(None)))

    def test_failing_controller_is_survived(self):
        class Failing(object):
            def registerContextMenuInterceptor(self, interceptor):
                raise RuntimeError("nope")

        self.assertFalse(context_menu.register_for_model(_Model(Failing())))


class JobArgumentTest(unittest.TestCase):
    def test_model_from_environment(self):
        document = FakeWriterDocument()
        arguments = (FakeNamedValue("Environment",
                                    (FakeNamedValue("EnvType", "DOCUMENTEVENT"),
                                     FakeNamedValue("Model", document))),)
        self.assertIs(context_menu.model_from_job_arguments(arguments),
                      document)

    def test_model_via_frame(self):
        document = FakeWriterDocument()

        class Frame(object):
            def getController(self):
                class Controller(object):
                    def getModel(self):
                        return document
                return Controller()

        arguments = (FakeNamedValue("Environment",
                                    (FakeNamedValue("Frame", Frame()),)),)
        self.assertIs(context_menu.model_from_job_arguments(arguments),
                      document)

    def test_missing_environment(self):
        self.assertIsNone(context_menu.model_from_job_arguments(()))
        self.assertIsNone(context_menu.model_from_job_arguments(None))

    def test_environment_without_model(self):
        arguments = (FakeNamedValue("Environment",
                                    (FakeNamedValue("EnvType", "EXECUTOR"),)),)
        self.assertIsNone(context_menu.model_from_job_arguments(arguments))


if __name__ == "__main__":
    unittest.main()


class OpenDocumentsTest(unittest.TestCase):
    """register_all_open und der Listener für neue Dokumente."""

    def setUp(self):
        context_menu._REGISTERED.clear()
        context_menu._LISTENER[:] = []

    def tearDown(self):
        context_menu._REGISTERED.clear()
        context_menu._LISTENER[:] = []

    class _Enumeration(object):
        def __init__(self, items):
            self.items = list(items)

        def hasMoreElements(self):
            return bool(self.items)

        def nextElement(self):
            return self.items.pop(0)

    class _Components(object):
        def __init__(self, items):
            self.items = items

        def createEnumeration(self):
            return OpenDocumentsTest._Enumeration(self.items)

    class _Desktop(object):
        def __init__(self, items):
            self.items = items

        def getComponents(self):
            return OpenDocumentsTest._Components(self.items)

    def _model(self):
        controller = _Controller()
        return _Model(controller), controller

    def test_registers_all_open_documents(self):
        first, c1 = self._model()
        second, c2 = self._model()
        count = context_menu.register_all_open(self._Desktop([first, second]))
        self.assertEqual(count, 2)
        self.assertEqual(len(c1.interceptors), 1)
        self.assertEqual(len(c2.interceptors), 1)

    def test_second_pass_registers_nothing_new(self):
        model, _c = self._model()
        desktop = self._Desktop([model])
        context_menu.register_all_open(desktop)
        self.assertEqual(context_menu.register_all_open(self._Desktop([model])),
                         0)

    def test_broken_desktop_is_survived(self):
        class Broken(object):
            def getComponents(self):
                raise RuntimeError("nope")

        self.assertEqual(context_menu.register_all_open(Broken()), 0)

    def test_listener_registers_on_relevant_events(self):
        model, controller = self._model()

        class Event(object):
            EventName = "OnViewCreated"
            Source = model

        context_menu.DocumentListener().documentEventOccured(Event())
        self.assertEqual(len(controller.interceptors), 1)

    def test_listener_ignores_other_events(self):
        model, controller = self._model()

        class Event(object):
            EventName = "OnSaveDone"
            Source = model

        context_menu.DocumentListener().documentEventOccured(Event())
        self.assertEqual(controller.interceptors, [])

    def test_is_registered_for(self):
        model, _c = self._model()
        self.assertFalse(context_menu.is_registered_for(model))
        context_menu.register_for_model(model)
        self.assertTrue(context_menu.is_registered_for(model))


class DocumentKeyTest(unittest.TestCase):
    """Der Schlüssel muss über Aufrufgrenzen hinweg stabil sein.

    PyUNO liefert bei jedem getCurrentController() ein neues Proxy-Objekt.
    Mit id() als Schlüssel meldete die Prüfung "nicht registriert", obwohl
    registriert war - genau dieser Fehler wird hier festgehalten.
    """

    class _Doc(object):
        def __init__(self, uid="uid-1", url=""):
            if uid:
                self.RuntimeUID = uid
            if url:
                self.URL = url
            self.controllers = []

        def getCurrentController(self):
            # Jedes Mal ein neues Objekt - wie PyUNO es tut.
            controller = _Controller()
            self.controllers.append(controller)
            return controller

    def setUp(self):
        context_menu._REGISTERED.clear()

    def tearDown(self):
        context_menu._REGISTERED.clear()

    def test_key_is_stable_across_calls(self):
        document = self._Doc()
        first = context_menu.document_key(document)
        second = context_menu.document_key(document)
        self.assertEqual(first, second)
        self.assertIn("uid-1", first)

    def test_registration_survives_new_controller_proxies(self):
        document = self._Doc()
        self.assertTrue(context_menu.register_for_model(document))
        # Zweiter Aufruf holt einen neuen Controller-Proxy
        self.assertTrue(context_menu.is_registered_for(document))
        self.assertFalse(context_menu.register_for_model(document))
        self.assertEqual(len(document.controllers[0].interceptors), 1)

    def test_falls_back_to_url(self):
        document = self._Doc(uid="", url="file:///tmp/a.odt")
        self.assertIn("a.odt", context_menu.document_key(document))

    def test_falls_back_to_identity(self):
        document = self._Doc(uid="", url="")
        self.assertTrue(context_menu.document_key(document).startswith("id:"))

    def test_different_documents_get_different_keys(self):
        self.assertNotEqual(context_menu.document_key(self._Doc("a")),
                            context_menu.document_key(self._Doc("b")))

    def test_error_is_recorded(self):
        class Failing(object):
            RuntimeUID = "uid-x"

            def getCurrentController(self):
                class Controller(object):
                    def registerContextMenuInterceptor(self, interceptor):
                        raise RuntimeError("not supported here")
                return Controller()

        self.assertFalse(context_menu.register_for_model(Failing()))
        self.assertIn("not supported here", context_menu.last_error())


class DuplicateMenuTest(unittest.TestCase):
    """Verkettete Interceptoren bekommen denselben Container."""

    def test_second_build_adds_nothing(self):
        container = FakeActionTriggerContainer()
        context_menu.build_menu(container, context_menu.menu_entries())
        before = container.getCount()
        result = context_menu.build_menu(container,
                                         context_menu.menu_entries())
        self.assertIsNone(result)
        self.assertEqual(container.getCount(), before)

    def test_has_menu_detects_our_root(self):
        container = FakeActionTriggerContainer()
        self.assertFalse(context_menu.has_menu(container))
        context_menu.build_menu(container, context_menu.menu_entries())
        self.assertTrue(context_menu.has_menu(container))

    def test_interceptor_stays_quiet_on_second_pass(self):
        container = FakeActionTriggerContainer()
        interceptor = context_menu.Interceptor()
        interceptor.notifyContextMenuExecute(FakeContextMenuEvent(container))
        count = container.getCount()
        interceptor.notifyContextMenuExecute(FakeContextMenuEvent(container))
        self.assertEqual(container.getCount(), count)
