# Contributing to LibreCompass

Thanks for taking a look. Bug reports, plugins and patches are all welcome.

## Reporting bugs

Run **LibreCompass → Diagnostics …** and paste its output into the issue.
It reports which parts of the extension actually registered in your
LibreOffice, which is usually the fastest route to the cause. The bug
report template asks for it.

## Development setup

No LibreOffice needed for the test suite — UNO is stubbed:

```
git clone https://github.com/msavus/librecompass
cd REPO
make test      # 255 tests
make check     # XML well-formedness, Python syntax, version consistency
make build     # dist/librecompass-<version>.oxt
make install   # unopkg add --force, then restart LibreOffice completely
```

`make install` needs `unopkg` from your LibreOffice installation; set
`UNOPKG=<path>` if it is not on `PATH`.

## Ground rules in the code

Two rules keep the codebase workable — please keep to them:

1. **UNO stays in `office/`.** No other module imports UNO document APIs.
   That is what makes the rest of the code testable.
2. **Every HTTP call runs in a worker thread**, and every touch of a control
   or the document goes back to the main thread via
   `main_thread.run_on_main()`. Breaking this freezes or crashes
   LibreOffice — it is the single most common cause of both.

Beyond that: standard library only in `pythonpath/` (the Python embedded in
LibreOffice has no pip), English msgids with a German entry in `i18n.py` for
user-visible strings, and a test for anything that can be tested without
LibreOffice.

Style: PEP 8, four spaces, lines under 80 characters, comments explaining
*why* rather than *what*.

## Adding things

- **A command:** class in `commands/` deriving from `Command`, register it
  in `COMMANDS` in `app.py`, add a menu node in `Addons.xcu`, optionally add
  it to `ENTRIES` in `ui/context_menu.py` and `SHORTCUTS` in
  `office/shortcuts.py`.
- **A language:** add a catalog to `CATALOGS` in `i18n.py` and extend
  `LANGUAGE_CODES` in `ui/dialogs.py`. Missing entries fall back to English.
- **A plugin:** see [docs/plugins.en.md](docs/plugins.en.md). Plugins live in
  your profile and need no changes to this repository — but good examples
  are welcome in `examples/plugins/`.

Details on layout, threading and the release process:
[docs/development.en.md](docs/development.en.md).

## Pull requests

Run `make check test` before opening one. CI runs the same on Python 3.9,
3.11 and 3.13. Please describe what you tested in a real LibreOffice — the
suite cannot cover menu registration, dialogs, `AsyncCallback` or reading
files through LibreOffice.

## Licensing

By contributing you agree that your contribution is licensed under the
Apache License 2.0, like the rest of the project. New source files should
carry the standard Apache header (see any existing file).
