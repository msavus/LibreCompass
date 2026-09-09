# Changelog

All notable changes to LibreCompass. Versions follow the project's phase
plan. Dates are the build dates of this working series.

## 1.5.0 — 2026-08-02

Diagnostics on LibreOffice 26.2 showed the context menu was still inactive.
Two separate causes.

**The diagnostics were lying — `id()` is not a stable key**
- Registration was tracked by `id(controller)`. PyUNO hands out a *new*
  Python proxy for every `getCurrentController()` call, so the id never
  matched on lookup: the check reported "not active" even when registration
  had succeeded, and the interceptor was re-registered on every command.
- Now keyed by the document's `RuntimeUID` (falling back to its URL). A
  failed registration records the exception, and diagnostics prints it
  instead of a bare "no".
- `build_menu` refuses to add a second LibreCompass submenu to the same
  container, so chained interceptors can no longer produce duplicates.

**Context menu no longer depends on the interceptor at all**
- New: entries are written into the module context menus through the UI
  configuration manager — the same mechanism behind Tools → Customize →
  Context Menus, and the same API layer that made the shortcuts work.
  They survive a restart and need neither the startup job nor a listener.
- **LibreCompass → Set up context menu** installs them (Writer, Calc,
  Impress, Draw) and additionally attaches the interceptor to the current
  document; **Remove context menu** takes them back out, leaving other
  entries untouched.
- Repeated installation is a no-op rather than a growing pile of submenus.

**Diagnostics**
- Reports the persistent context-menu entries per module, whether the
  interceptor is active here, and the last registration error.

**Note on shortcuts:** "FEHLT" before running **Set up shortcuts** is the
expected state — since 1.3.0 they are assigned on request, not at install
time. The report now also shows how many of the six combinations are
already taken by something else per module (2 each in Impress and Draw on
26.2); those are skipped rather than overwritten.

**Tests**
- 255 tests (27 new: persistent menu entries, install/remove/idempotence,
  the stable document key, duplicate protection).

## 1.4.1 — 2026-08-02

Preparation for publishing the project; no functional change to the
extension itself.

**Licensing**
- Added the **Apache License 2.0** — permissive, with an explicit patent
  grant. No copyleft: LibreCompass can be embedded in or combined with
  proprietary software without an obligation to release changes.
- Every source file carries the standard Apache header; `LICENSE` ships
  inside the .oxt as well.

**Repository**
- `.gitignore`, `.gitattributes`, `CONTRIBUTING.md`, `SECURITY.md`.
- CI workflow: tests plus the consistency check on Python 3.9, 3.11 and
  3.13, and a packaging job that uploads the .oxt as an artifact.
- Release workflow: pushing a `vX.Y.Z` tag verifies the tag matches the
  declared version, builds the .oxt and attaches it to a GitHub release.
- Issue templates — the bug report requires the **Diagnostics** output,
  which is usually the fastest route to a cause.

**Release tooling**
- `scripts/bump_version.py` sets the version in `__init__.py`,
  `description.xml` and `update.xml` including the download URL;
  `build.py --check` now compares all three.
- `scripts/set_repo.py` replaces the repository placeholder everywhere
  once, and again after a move.
- `update.xml` is wired up as an update source in `description.xml`, so
  installed copies are offered new releases.
- `build.py --check` warns while the placeholder is still in place.

**Tests**
- 227 tests (22 new: version consistency across all files, Apache headers, the
  URL rewriting logic, manifest/file agreement). These immediately caught a
  bug in the tooling itself — `set_repo.py` rewrote the placeholder inside
  `build.py`, which is where the placeholder is *detected*, so the check
  warned forever after. Both `build.py` and `tests/` are now excluded from
  the rewrite.

## 1.4.0 — 2026-07-31

**No more freezing while the model works**
- The quick commands (improve, rewrite, summarize, translate, custom
  prompt, analyze) ran synchronously on the main thread since 0.1. For the
  seconds or minutes llama.cpp needs, the whole of LibreOffice stood still.
  They now run in a worker thread; only the write-back happens on the main
  thread via `AsyncCallback`.
- The **write target is captured when the request is sent**, not when the
  answer arrives: you can keep working and change the selection meanwhile,
  and the answer still lands where you asked for it.
- Only one background request at a time; a second one is refused with a
  short message instead of racing the first.
- The panel already streamed, but built its messages on the main thread —
  which meant the knowledge-base lookup (an embedding request) still froze
  the UI. Document text is still read on the main thread; embedding and
  retrieval moved into the worker.
- Indexing the knowledge base also runs in the background now, with
  per-file progress in the dialog and the buttons disabled while it works.
  This was the longest freeze of all: minutes for a larger folder.

**Tests**
- 205 tests (25 new for the background runner — lock, result routing, error
  and indicator paths — and for captured write targets in Writer, Calc,
  Impress and Draw, including "selection changed meanwhile").

## 1.3.0 — 2026-07-31

Fixes both features properly, after diagnostics on LibreOffice 26.2 showed
what was actually wrong.

**Keyboard shortcuts — cause and fix**
- Diagnostics showed no LibreCompass binding anywhere: an
  `Accelerators.xcu` shipped by an extension is not merged into the
  keyboard configuration. The file has been removed; it did nothing.
- Shortcuts are now set through the documented API
  (`com.sun.star.ui.GlobalAcceleratorConfiguration` and each module's
  `getShortCutManager()`), via **LibreCompass → Set up shortcuts**.
- A combination already bound to something else is never overwritten; it is
  reported instead. **Remove shortcuts** takes only LibreCompass bindings
  back out.

**Context menu — second cause and fix**
- The job was registered and bound correctly, but the interceptor was still
  inactive, so the job apparently never executed.
- The extension no longer depends on it: every LibreCompass command now
  calls `ensure_active()`, which attaches the global document listener and
  registers the interceptor for the current document. After the first use
  of any command, right-click works — with or without the startup job.
- The startup job now writes a marker to `runtime.json` when it runs, so
  diagnostics can tell "configured" from "actually executed".

**Diagnostics**
- Reads bindings through the accelerator API instead of the raw
  configuration — the level where LibreOffice actually resolves keys — and
  reports LibreCompass bindings against other bindings on the same keys,
  so an unreadable node is distinguishable from an empty one.
- Reports whether the startup job ever ran.

**Tests**
- 180 tests (20 new for shortcut planning, conflict handling, apply/remove
  and the reworked diagnostics).

## 1.2.0 — 2026-07-31

Fixes the two features added in 1.1, which did not show up in a real
LibreOffice.

**Context menu — cause and fix**
- 1.1 bound the job to the document events `OnViewCreated`, `OnLoad` and
  `OnNew`. Those are document event names, not job event names: the job
  never ran, so no interceptor was ever registered.
- Now bound to `onFirstVisibleTask`, the documented startup event. The job
  registers the interceptor on all open documents and attaches a listener
  to `com.sun.star.frame.GlobalEventBroadcaster` for later ones.
- New command **Enable context menu** attaches the interceptor to the
  current document by hand, as a fallback.

**Keyboard shortcuts**
- `Accelerators.xcu` is unchanged, but the commands are now also exported
  through an `AddonMenu` node. That makes them appear under
  Tools → Add-Ons and — the point — in the *Add-ons* category of
  Tools → Customize → Keyboard, so shortcuts can be assigned by hand if the
  shipped ones do not register.

**Diagnostics**
- New command **Diagnostics …** reads the live LibreOffice configuration
  and reports which mechanisms actually registered: the accelerator entries
  per module, whether the context-menu job exists and which events it is
  bound to, and whether the interceptor is active in the current document.
  It names the next step for whatever is missing, instead of leaving the
  failure silent.

**Tests**
- 160 tests (15 new for diagnostics and the startup/listener paths).

## 1.1.0 — 2026-07-30

**Context menu**
- Right-clicking in Writer, Calc, Impress or Draw now offers a
  **LibreCompass** submenu with improve, rewrite, summarize, translate,
  custom prompt and the panel.
- Implemented as an `XContextMenuInterceptor` registered by a job bound to
  the document events `OnViewCreated`, `OnLoad` and `OnNew` (`Jobs.xcu`) —
  LibreOffice has no configuration-only way to extend context menus.
- Menu building, entry order and job-argument parsing are unit tested;
  every failure path falls back to leaving the context menu untouched.

**Keyboard shortcuts**
- `Accelerators.xcu` ships defaults on Ctrl+Shift+Alt: C panel, I improve,
  R rewrite, Z summarize, T translate, P custom prompt.
- Ctrl+Shift+Alt was chosen deliberately: Ctrl+Shift is heavily used by
  LibreOffice itself, and Ctrl+Alt is AltGr on German keyboards.
- Rebindable under Tools → Customize → Keyboard.

**Build options**
- `build.py --no-shortcuts` and `--no-context-menu` package the extension
  without those parts; the matching entries are stripped from the manifest
  automatically.

**Tests**
- 145 tests (17 new for the context menu).

## 1.0.0 — 2026-07-30

**Knowledge base (RAG), local and dependency-free**
- Index your own files and ask questions across them; answers name their
  sources.
- Text extraction: `txt`, `md`, `csv`, `json`, `xml`, `html`, `odt`, `ods`,
  `odp`, `docx`, `xlsx`, `pptx` via the standard library; `pdf`, `doc`,
  `rtf`, `epub` by loading them invisibly in LibreOffice itself.
- Chunking with overlap, embeddings over `/v1/embeddings`, vector index as
  `knowledge.json`, cosine search in plain Python — no ChromaDB/FAISS,
  because the embedded LibreOffice Python has no pip.
- Management dialog: add file/folder, remove, rebuild, clear.
- New panel context option *Knowledge base*.

**Document analysis**
- New command producing a report in a *new* document: hard structural
  metrics read from the document (paragraphs, words, heading outline,
  tables, images; sheets, filled cells, formulas; slides, shapes with
  text) plus the model's observations. Metrics come from LibreOffice, not
  from the model.

**Plugins**
- Own actions as single Python files in `user/librecompass/plugins/`.
- Two kinds: prompt plugins (`NAME` + `PROMPT`) and action plugins
  (`run(api)`).
- Stable `PluginAPI`: read selection/document/module/settings, ask the
  model, replace/insert/new document, show messages.
- Broken plugins are skipped; errors inside `run()` are caught and shown
  with a traceback.
- Three ready-to-copy examples in `examples/plugins/`.

**Internationalization**
- English msgids with a German catalog; `language` setting (`auto`/`en`/
  `de`), `auto` follows the LibreOffice UI locale.
- Model instructions and the default prompt library follow the active
  language too.

**Tests**
- 128 tests running without LibreOffice: UNO stubs plus fakes for Writer,
  Calc, Impress and Draw documents, so the module-specific code paths are
  covered. Real HTTP round trips against a local throwaway server for the
  client (sync, streaming, abort, error paths).

**Installer and tooling**
- `build.py --check` verifies XML well-formedness, Python syntax and that
  the version in `__init__.py` matches `description.xml`.
- `Makefile` (test/check/build/install/uninstall/dist/clean),
  `scripts/install.sh`, `update.xml` template for auto-updates.

**Documentation**
- User guide, plugin API and development guide, each in English and German.

**Settings added**
- `language`, `embedding_model`, `chunk_size`, `chunk_overlap`,
  `rag_top_k`, `max_index_file_chars`, `knowledge_sources`.

**Still open (candidates for 1.1)**
- Real dockable sidebar (`XUIElementFactory` + `Sidebar.xcu`) instead of
  the non-modal panel.
- Asynchronous indexing with progress and cancel.
- A license file; signing; publishing to the extension directory.

## 0.5.0 — 2026-07-30

- Renamed to **LibreCompass** (identifier `org.librecompass.extension`,
  package `librecompass`, profile directory `user/librecompass`).
- Bilingual extension metadata and README (English + German).
- Note: the identifier change means LibreOffice treats this as a new
  extension. Remove the previous entry first; old settings are not
  migrated.

## 0.4.0 — 2026-07-30

- Available in **all** LibreOffice modules (menu context restriction
  removed).
- Document access generalized to Writer, Calc, Impress and Draw with
  module-specific read/replace/insert behavior; clean fallback message in
  modules without apply support.

## 0.3.0 — 2026-07-30

- Chat mode with conversation history and document context.
- Prompt library (`prompts.json`) with save from the panel.
- History (`history.json`, last 200 entries) reloadable into the panel.

## 0.2.0 — 2026-07-30

- Non-modal panel with the planned sidebar layout.
- Live streaming (SSE) with abort, throttled display updates.
- Model picker filled from `/v1/models`; settings dialog.

## 0.1.0 — 2026-07-29

- OXT scaffold, menu entry, read selection, model answer, replace text.
- One OpenAI-compatible client for Ollama, llama.cpp, LM Studio and vLLM.
- Optional tracked-changes mode for AI replacements.
