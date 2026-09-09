# LibreCompass — Development

Deutsch: [development.de.md](development.de.md)

## Layout

```
description.xml            extension manifest (identifier, version, i18n text)
Addons.xcu                 menu entries, one per service:…?command
Jobs.xcu                   binds the context-menu job to document events
registration.py            thin UNO component (XJobExecutor)
META-INF/manifest.xml       tells LibreOffice what is inside the .oxt
build.py                   check + package into dist/*.oxt
Makefile                   test / check / build / install / dist / clean
update.xml                 template for the auto-update feed
pythonpath/librecompass/    the actual code (auto-added to sys.path by LO)
tests/                     runs without LibreOffice (UNO stubs + fakes)
examples/plugins/          copy-ready plugin examples
docs/                      user guide, plugin API, this file (en + de)
```

Inside `pythonpath/librecompass/`:

| Module | Responsibility |
| --- | --- |
| `app.py` | command router (`service:…?command` → command class) |
| `i18n.py` | translation, English msgids + German catalog |
| `main_thread.py` | `AsyncCallback`: worker thread → main thread |
| `commands/` | one class per action, each with `execute()` |
| `ai/client.py` | OpenAI-compatible client: chat, streaming, models, embeddings |
| `ai/prompts.py` | prompt building blocks, prompt library |
| `ai/history.py` | history file |
| `office/document.py` | **all** UNO document access, per module |
| `office/analysis.py` | structural metrics for the analysis command |
| `office/extract.py` | text extraction from external files |
| `rag/` | chunking, vector store, indexing/retrieval |
| `plugins.py` | plugin discovery and the stable plugin API |
| `ui/` | panel, dialogs, knowledge base and plugin dialogs |

Two rules keep this maintainable:

1. **UNO stays in `office/`.** No other module imports UNO document APIs.
2. **HTTP stays in `ai/client.py`.** One client covers every backend,
   because they all speak `/v1/chat/completions`.

## Constraints of the embedded Python

The Python bundled with LibreOffice has **no pip**, so the extension uses
the standard library only (`urllib`, `json`, `zipfile`, `xml.etree`,
`math`). That is why the vector store is plain Python instead of
ChromaDB/FAISS, and why PDFs are read by LibreOffice itself.

## Threading

**Every** HTTP call runs in a worker thread — `async_task.run()` for the
commands, an explicit thread in the panel and the knowledge dialog. Every
touch of a control or the document goes back through
`main_thread.run_on_main()`
(`com.sun.star.awt.AsyncCallback`). Streaming updates are throttled to
about five per second. Violating this rule is the most likely cause of
freezes or crashes.

## Build and test

```
make check      # XML well-formedness, Python syntax, version consistency
make test       # 145 tests, no LibreOffice needed
make build      # dist/librecompass-<version>.oxt
make install    # unopkg add --force  (then restart LibreOffice fully)
make uninstall
```

`tests/stubs/unostubs.py` installs placeholders for `uno`, `unohelper` and
the whole `com.sun.star` namespace, so every module imports outside
LibreOffice. `tests/fakes.py` emulates the slice of the UNO API the
extension uses — that is what makes the Calc/Impress/Draw code paths
testable. `tests/test_client.py` runs real HTTP round trips against a local
throwaway server.

What the suite does **not** cover: menu registration, dialog and panel
construction, `AsyncCallback`, and loading external files through
LibreOffice. Those need a smoke test in a real LibreOffice.

## Context menu and shortcuts

Both hang off the same `service:` URLs as the menu bar, so a new command
needs no extra plumbing — just add it in the right places.

**Shortcuts** are set through `office/shortcuts.py` using
`com.sun.star.ui.GlobalAcceleratorConfiguration` and, per module,
`ModuleUIConfigurationManagerSupplier` → `getShortCutManager()`.

> Versions 1.1/1.2 shipped an `Accelerators.xcu` instead. Diagnostics on
> LibreOffice 26.2 showed no binding arrived: an extension-supplied
> accelerator fragment is not merged into the keyboard configuration.
> Use the API, not the configuration.

**Context menu** cannot be done with configuration alone. `Jobs.xcu` binds
`org.librecompass.ContextMenuJob` to `onFirstVisibleTask` — the documented
startup event of the job framework. The job (in `registration.py`)
registers a `XContextMenuInterceptor` on every open document and then
attaches a listener to `com.sun.star.frame.GlobalEventBroadcaster` so
later documents are covered too.

Since 1.5 the context menu does **not** depend on any of that.
`office/context_config.py` writes the entries into the module context
menus through `ModuleUIConfigurationManagerSupplier` →
`getSettings("private:resource/popupmenu/…")` → `replaceSettings` →
`store()`. That is the same API layer the shortcuts use, it persists
across restarts, and the user can edit it under Tools → Customize →
Context Menus. The interceptor remains as a runtime addition.

> Two traps this walked into, both worth remembering:
>
> 1. Jobs bound to `OnViewCreated`/`OnLoad`/`OnNew` never run — those are
>    document event names, not job event names. Use `onFirstVisibleTask`.
> 2. **Never key anything on `id()` of a UNO object.** PyUNO returns a new
>    Python proxy per call, so `id(model.getCurrentController())` differs
>    between two calls on the same document. Use `RuntimeUID`. `ui/context_menu.py` splits this into pure logic
(`menu_entries`, `build_menu`, `model_from_job_arguments` — all unit
tested) and the UNO glue. Because the job fires more than once per
document, `register_for_model` keeps a registry keyed by controller id so
the submenu is not inserted twice.

Both parts are optional at build time, because they are the two pieces most
likely to misbehave on an untested LibreOffice version:

```
python3 build.py --no-context-menu    # without Jobs.xcu
```

`build.py` strips the matching entries from `META-INF/manifest.xml` when
packaging — a file named in the manifest but missing from the archive makes
the installation fail.

## Adding a command

1. New class in `commands/`, deriving from `Command`, implementing
   `execute()`; set `needs_document = False` if it works without a document.
2. Register it in `COMMANDS` in `app.py`.
3. Add a menu node in `Addons.xcu` with `service:org.librecompass.Main?<key>`
   and both language titles. Optionally add it to `ENTRIES` in
   `ui/context_menu.py` and to `Accelerators.xcu`.
4. Add UI strings as English msgids plus a German entry in `i18n.py`.

## Adding a language

Add a catalog dict to `CATALOGS` in `i18n.py` and extend `LANGUAGE_CODES`
in `ui/dialogs.py` plus the label tuple next to it. Missing entries fall
back to English automatically. The menu titles in `Addons.xcu` take their
own `xml:lang` values.

## Release checklist

1. `python3 scripts/bump_version.py X.Y.Z` — updates `__init__.py`,
   `description.xml` and `update.xml` including the download URL.
   `make check` verifies all three agree.
2. Update `CHANGELOG.md` (a test checks that an entry for the version
   exists).
3. `make check test build`
4. Smoke test in LibreOffice: menu present in Writer, Calc and Impress;
   panel opens; streaming works; apply works per module; right-click menu;
   `Set up shortcuts`.
5. Commit, then `git tag vX.Y.Z && git push origin vX.Y.Z`. The release
   workflow verifies the tag matches the version, builds the .oxt and
   attaches it to a GitHub release.
6. Users on an older version get the update offered through `update.xml`
   once the release is published.

Optional: sign the .oxt with a certificate before publishing — LibreOffice
shows unsigned extensions with a warning.
