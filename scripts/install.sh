#!/bin/sh
# LibreCompass installieren (Linux/macOS). Benötigt unopkg aus LibreOffice.
set -e
cd "$(dirname "$0")/.."

VERSION=$(python3 -c "import re;print(re.search(r'__version__\s*=\s*\"([^\"]+)\"',open('pythonpath/librecompass/__init__.py').read()).group(1))")
OXT="dist/librecompass-$VERSION.oxt"

UNOPKG=${UNOPKG:-unopkg}
if ! command -v "$UNOPKG" >/dev/null 2>&1; then
    for candidate in \
        /usr/lib/libreoffice/program/unopkg \
        /opt/libreoffice*/program/unopkg \
        "/Applications/LibreOffice.app/Contents/MacOS/unopkg"; do
        if [ -x "$candidate" ]; then UNOPKG="$candidate"; break; fi
    done
fi
if ! command -v "$UNOPKG" >/dev/null 2>&1 && [ ! -x "$UNOPKG" ]; then
    echo "unopkg nicht gefunden. Bitte UNOPKG=<pfad> setzen oder die .oxt"
    echo "über Extras > Extension Manager installieren."
    exit 1
fi

python3 build.py
"$UNOPKG" add --force "$OXT"
echo "Installiert. LibreOffice komplett neu starten (inkl. Schnellstarter)."
