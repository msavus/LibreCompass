# LibreCompass - Entwicklungsaufgaben
#
#   make test       Tests ohne LibreOffice
#   make check      XML, Python-Syntax und Versionsgleichstand prüfen
#   make build      dist/librecompass-<version>.oxt erzeugen
#   make install    Extension im lokalen LibreOffice installieren
#   make uninstall  Extension entfernen
#   make dist       Quellarchiv erzeugen
#   make clean      Build-Reste entfernen
#   make repo REPO=owner/name    GitHub-Adresse überall eintragen
#   make bump V=1.5.0            Version an allen Stellen setzen

PYTHON ?= python3
UNOPKG ?= unopkg
VERSION := $(shell $(PYTHON) -c "import re;print(re.search(r'__version__\s*=\s*\"([^\"]+)\"',open('pythonpath/librecompass/__init__.py').read()).group(1))")
OXT := dist/librecompass-$(VERSION).oxt

.PHONY: all test check build install uninstall reinstall dist clean repo bump

all: check test build

test:
	$(PYTHON) tests/run_tests.py

check:
	$(PYTHON) build.py --check

build: $(OXT)

$(OXT): $(shell find pythonpath -name '*.py') description.xml Addons.xcu registration.py META-INF/manifest.xml
	$(PYTHON) build.py

install: build
	$(UNOPKG) add --force $(OXT)
	@echo "LibreOffice komplett neu starten (inkl. Schnellstarter)."

uninstall:
	-$(UNOPKG) remove org.librecompass.extension

reinstall: uninstall install

dist: build
	@mkdir -p dist
	@tar --exclude='./dist' --exclude='__pycache__' --exclude='./.git' \
	    -czf dist/librecompass-$(VERSION)-src.tar.gz .
	@echo "geschrieben: dist/librecompass-$(VERSION)-src.tar.gz"

clean:
	rm -rf dist
	find . -name '__pycache__' -type d -prune -exec rm -rf {} +

repo:
	@test -n "$(REPO)" || (echo "Aufruf: make repo REPO=owner/name"; exit 1)
	$(PYTHON) scripts/set_repo.py $(REPO)

bump:
	@test -n "$(V)" || (echo "Aufruf: make bump V=1.5.0"; exit 1)
	$(PYTHON) scripts/bump_version.py $(V)
