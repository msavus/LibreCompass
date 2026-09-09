# -*- coding: utf-8 -*-
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at https://www.apache.org/licenses/LICENSE-2.0
"""Release-Werkzeuge: Versionsgleichstand und Repository-Platzhalter.

Diese Tests fangen genau die Fehler ab, die sonst erst nach einer
Veröffentlichung auffallen: eine Version, die an einer Stelle vergessen
wurde, oder ein Platzhalter, der es in ein Release schafft.
"""
import os
import re
import unittest
from xml.dom import minidom

import context  # noqa: F401

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def read(*parts):
    with open(os.path.join(ROOT, *parts), encoding="utf-8") as handle:
        return handle.read()


def declared_version():
    match = re.search(r'__version__\s*=\s*"([^"]+)"',
                      read("pythonpath", "librecompass", "__init__.py"))
    return match.group(1)


def xml_version(name):
    document = minidom.parse(os.path.join(ROOT, name))
    return document.getElementsByTagName("version")[0].getAttribute("value")


class VersionConsistencyTest(unittest.TestCase):
    def test_description_matches(self):
        self.assertEqual(xml_version("description.xml"), declared_version())

    def test_update_feed_matches(self):
        self.assertEqual(xml_version("update.xml"), declared_version())

    def test_download_url_carries_the_version(self):
        version = declared_version()
        content = read("update.xml")
        self.assertIn("/v%s/librecompass-%s.oxt" % (version, version), content)

    def test_changelog_has_an_entry(self):
        self.assertIn("## %s " % declared_version(), read("CHANGELOG.md"))

    def test_readmes_name_the_version(self):
        version = declared_version()
        for name in ("README.md", "README.de.md"):
            self.assertIn(version, read(name), name)


class LicenseTest(unittest.TestCase):
    def test_license_file_is_apache2(self):
        content = read("LICENSE")
        self.assertIn("Apache License", content)
        self.assertIn("Version 2.0", content)

    def test_python_files_carry_the_header(self):
        missing = []
        for base, dirs, names in os.walk(os.path.join(ROOT, "pythonpath")):
            dirs[:] = [name for name in dirs if name != "__pycache__"]
            for name in names:
                if not name.endswith(".py"):
                    continue
                path = os.path.join(base, name)
                if "www.apache.org/licenses/LICENSE-2.0" not in read(path):
                    missing.append(os.path.relpath(path, ROOT))
        self.assertEqual(missing, [])

    def test_registration_carries_the_header(self):
        self.assertIn("www.apache.org/licenses/LICENSE-2.0", read("registration.py"))


class SetRepoTest(unittest.TestCase):
    """Die Ersetzungslogik von scripts/set_repo.py."""

    def setUp(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "set_repo", os.path.join(ROOT, "scripts", "set_repo.py"))
        self.module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.module)

    def test_replaces_placeholder(self):
        text = "see https://github.com/OWNER/REPO/blob/main/README.md"
        updated, hits = self.module.replace(text, "maxim/librecompass")
        self.assertEqual(hits, 1)
        self.assertIn("github.com/maxim/librecompass/blob", updated)
        self.assertNotIn("OWNER", updated)

    def test_replaces_raw_urls_too(self):
        text = "https://raw.githubusercontent.com/OWNER/REPO/main/update.xml"
        updated, hits = self.module.replace(text, "maxim/librecompass")
        self.assertEqual(hits, 1)
        self.assertIn("raw.githubusercontent.com/maxim/librecompass/main",
                      updated)

    def test_is_repeatable_after_a_move(self):
        text = "https://github.com/old/name/releases"
        once, _h = self.module.replace(text, "new/name")
        twice, hits = self.module.replace(once, "newer/name")
        self.assertEqual(hits, 1)
        self.assertIn("github.com/newer/name/releases", twice)

    def test_placeholder_is_replaced_on_any_host(self):
        # Beabsichtigt: nur so werden die Badge-Adressen von shields.io
        # miterfasst, die nicht auf github.com liegen.
        text = "https://img.shields.io/x/OWNER/REPO"
        updated, hits = self.module.replace(text, "maxim/librecompass")
        self.assertEqual(hits, 1)
        self.assertIn("x/maxim/librecompass", updated)

    def test_set_addresses_on_other_hosts_stay_untouched(self):
        # Ein Umzug biegt nur GitHub-Adressen um, nicht beliebige Pfade.
        text = "https://example.org/old/name/x"
        updated, hits = self.module.replace(text, "new/name")
        self.assertEqual(hits, 0)
        self.assertEqual(updated, text)

    def test_replaces_shields_badge_urls(self):
        text = ("https://img.shields.io/github/v/release/OWNER/REPO"
                "?display_name=tag")
        updated, hits = self.module.replace(text, "maxim/librecompass")
        self.assertEqual(hits, 1)
        self.assertIn("release/maxim/librecompass?", updated)

    def test_target_equal_to_placeholder_changes_nothing(self):
        text = "https://github.com/OWNER/REPO/x"
        updated, _hits = self.module.replace(text, "OWNER/REPO")
        self.assertEqual(updated, text)

    def test_tests_directory_is_skipped(self):
        # Der Platzhalter steht hier als Prüfwert - er darf nicht ersetzt
        # werden, sonst zerstört das Skript die eigenen Tests.
        self.assertIn("tests", self.module.SKIP_DIRS)

    def test_build_script_is_skipped(self):
        # build.py prüft, ob der Platzhalter noch gesetzt ist. Würde die
        # Zeichenkette mitersetzt, meldete die Prüfung danach immer eine
        # Warnung - genau das ist beim Einrichten einmal passiert.
        self.assertIn("build.py", self.module.SKIP_FILES)

    def test_files_generator_skips_them(self):
        names = [os.path.basename(path) for path in self.module.files()]
        self.assertNotIn("build.py", names)
        self.assertNotIn("set_repo.py", names)
        self.assertNotIn("test_release_tooling.py", names)

    def test_counts_every_occurrence(self):
        text = ("https://github.com/OWNER/REPO/a "
                "https://raw.githubusercontent.com/OWNER/REPO/b")
        _updated, hits = self.module.replace(text, "x/y")
        self.assertEqual(hits, 2)


class PackagingTest(unittest.TestCase):
    def test_manifest_lists_only_files_that_exist(self):
        content = read("META-INF", "manifest.xml")
        for name in re.findall(r'manifest:full-path="([^"]+)"', content):
            self.assertTrue(os.path.exists(os.path.join(ROOT, name)),
                            "im Manifest genannt, fehlt aber: %s" % name)

    def test_gitignore_excludes_build_output(self):
        content = read(".gitignore")
        self.assertIn("dist/", content)
        self.assertIn("__pycache__/", content)

    def test_workflows_are_valid_yaml_ish(self):
        # Ohne PyYAML: grobe Struktur prüfen, damit Tippfehler auffallen.
        for name in ("ci.yml", "release.yml"):
            content = read(".github", "workflows", name)
            self.assertIn("runs-on:", content)
            self.assertIn("actions/checkout", content)
            self.assertNotIn("\t", content, "Tabs sind in YAML unzulässig")


if __name__ == "__main__":
    unittest.main()
