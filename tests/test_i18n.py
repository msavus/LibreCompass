# -*- coding: utf-8 -*-
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at https://www.apache.org/licenses/LICENSE-2.0
import unittest

import context  # noqa: F401
from fakes import FakeContext

from librecompass import i18n
from librecompass.i18n import gettext as _


class I18nTest(unittest.TestCase):
    def tearDown(self):
        i18n.set_language("en")

    def test_english_is_identity(self):
        i18n.set_language("en")
        self.assertEqual(_("Send"), "Send")

    def test_german_catalog(self):
        i18n.set_language("de")
        self.assertEqual(_("Send"), "Senden")
        self.assertEqual(_("Knowledge base"), "Wissensdatenbank")

    def test_unknown_message_falls_back(self):
        i18n.set_language("de")
        self.assertEqual(_("not translated at all"), "not translated at all")

    def test_unknown_language_falls_back_to_english(self):
        self.assertEqual(i18n.set_language("fr"), "en")

    def test_region_codes_are_normalized(self):
        self.assertEqual(i18n.set_language("de-DE"), "de")
        self.assertEqual(i18n.set_language("de_AT"), "de")

    def test_office_locale_is_read(self):
        ctx = FakeContext(locale="de-DE")
        self.assertEqual(i18n.office_locale(ctx), "de-DE")

    def test_apply_settings_auto(self):
        ctx = FakeContext(locale="de-DE")

        class S(object):
            language = "auto"

        self.assertEqual(i18n.apply_settings(ctx, S()), "de")

    def test_apply_settings_explicit_overrides_locale(self):
        ctx = FakeContext(locale="de-DE")

        class S(object):
            language = "en"

        self.assertEqual(i18n.apply_settings(ctx, S()), "en")


if __name__ == "__main__":
    unittest.main()
