# LibreCompass — 1.5.0

[![CI](https://github.com/msavus/librecompass/actions/workflows/ci.yml/badge.svg)](https://github.com/msavus/librecompass/actions/workflows/ci.yml)
[![License: Apache 2.0](https://img.shields.io/badge/License-Apache_2.0-brightgreen.svg)](LICENSE)
[![Release](https://img.shields.io/github/v/release/msavus/librecompass?display_name=tag&sort=semver)](https://github.com/msavus/librecompass/releases/latest)

Local generative AI for LibreOffice — all modules — via an OpenAI-compatible
local endpoint (Ollama, llama.cpp/llama-server, LM Studio, vLLM). No cloud,
no API keys.

The name is the product promise: the AI provides direction, **you keep the
wheel**. In Writer, AI edits can be recorded as tracked changes, so every
change remains individually reviewable.

Deutsche Version: [README.de.md](README.de.md)

## What it does

- **Quick commands** on a selection: improve, rewrite, summarize,
  translate, custom prompt — from the menu bar, the **right-click menu**
  or **keyboard shortcuts** (Ctrl+Shift+Alt+I/R/Z/T/P, panel on +C — set up on request)
- **Panel** with model picker, prompt library, live streaming, chat mode and
  three apply modes (replace / insert / new document)
- **Knowledge base (RAG)** over your own files, fully local — answers name
  their sources
- **Document analysis** producing a report in a new document: hard
  structural metrics plus the model's observations
- **Plugins**: your own actions as single Python files
- **Diagnostics** command that reports which parts of the extension actually
  registered in LibreOffice
- **English and German** UI, following the LibreOffice locale by default
- Works in **Writer, Calc, Impress and Draw**; panel and chat also work
  elsewhere

## Documentation

| Document | Contents |
| --- | --- |
| [docs/user-guide.en.md](docs/user-guide.en.md) | setup, every feature, troubleshooting |
| [docs/plugins.en.md](docs/plugins.en.md) | plugin API and examples |
| [docs/development.en.md](docs/development.en.md) | layout, threading, build, release |
| [CHANGELOG.md](CHANGELOG.md) | version history |

## Requirements and installation

- LibreOffice ≥ 7.4 (standard installation with bundled Python)
- A local backend, e.g. `ollama pull qwen3` and — for the knowledge base —
  `ollama pull nomic-embed-text`

1. Download the `.oxt` from the
   [latest release](https://github.com/msavus/librecompass/releases/latest) — or build
   it yourself with `python3 build.py`
2. LibreOffice: **Tools → Extension Manager → Add** → select the .oxt
   (or run `make install`, which uses `unopkg`)
3. Restart LibreOffice completely (including the quickstarter)
4. Open any document → **LibreCompass** menu appears

Optional after installing: **LibreCompass → Set up shortcuts** and
**Set up context menu** — both are opt-in rather than forced on you.

**Upgrading from a build before 0.5:** the identifier changed from
`org.libreaiwriter.*` to `org.librecompass.*`, so LibreOffice treats this as
a different extension — remove the old entry first. Old settings are not
migrated.

## Configuration

Stored in the LibreOffice user profile under `user/librecompass/`:
`settings.json`, `prompts.json`, `history.json`, `knowledge.json`,
`plugins/`.

| Backend | Endpoint (`base_url`) |
| --- | --- |
| Ollama | `http://localhost:11434/v1` (default) |
| llama.cpp (llama-server) | `http://localhost:8080/v1` |
| LM Studio | `http://localhost:1234/v1` |
| vLLM | `http://localhost:8000/v1` |

They all speak the same `/v1/chat/completions` API — which is why there is
exactly **one** client (`ai/client.py`, standard library only, since the
Python embedded in LibreOffice has no pip).

Important switches: `track_changes`, `stream` (`false` falls back to
synchronous requests), `language`, `max_context_chars`, `rag_top_k`.

## Architecture

```
registration.py                  thin UNO registration (XJobExecutor)
Addons.xcu                       menu entries (service:…?command)
Jobs.xcu                         registers the context-menu interceptor
pythonpath/librecompass/
├── app.py                       command router
├── i18n.py                      English msgids + German catalog
├── main_thread.py               AsyncCallback: worker → main thread
├── plugins.py                   plugin discovery + stable plugin API
├── commands/                    one class per action, execute()
├── ai/                          client (chat/streaming/embeddings), prompts, history
├── office/                      all UNO document access, analysis, text extraction
├── rag/                         chunking, vector store, indexing/retrieval
├── ui/                          panel, dialogs, knowledge base, plugins
└── config/settings.py           settings.json in the user profile
```

Two rules: UNO stays in `office/`, HTTP stays in `ai/client.py`.
**Threading:** HTTP runs in a worker thread; every touch of a control or the
document goes back via `main_thread.run_on_main()`.

## Development

```
make check      # XML, Python syntax, version consistency
make test       # 255 tests, no LibreOffice needed
make build      # dist/librecompass-1.5.0.oxt
make install    # unopkg add --force
```

## Test status — read this before shipping

- **Covered by the suite (255 tests, real HTTP round trips against a local
  server):** client sync/streaming/abort/error paths, embeddings, prompts,
  prompt library, history, settings, i18n, chunking, vector store,
  text extraction (ODF/OOXML/plain), knowledge indexing and retrieval,
  plugin loading and the plugin API, context-menu building and
  job-argument parsing, and — via UNO fakes — the Writer/Calc/Impress/Draw
  read and write paths plus document analysis.
- **Not covered (no LibreOffice runs in the build environment):** menu
  registration, dialog and panel construction, `AsyncCallback`, reading
  external files (PDF/DOC) through LibreOffice, and — new in 1.1 — whether
  the context-menu job actually fires and whether the shipped shortcuts
  collide with anything. These need a smoke test in LibreOffice ≥ 7.4.
  If the panel misbehaves, set `"stream": false` in `settings.json`; if
  the context menu or the shortcuts cause trouble, rebuild with
  `--no-context-menu` or `--no-shortcuts`.

## Open items

- Real dockable sidebar (`XUIElementFactory` + `Sidebar.xcu`) instead of the
  non-modal panel — deliberately deferred: it needs a control-container
  refactor and cannot be verified without LibreOffice.
- Asynchronous indexing with progress and cancel.
- Signing and the `update.xml` feed are prepared but not published.

## Contributing

Bug reports, plugins and patches are welcome — see
[CONTRIBUTING.md](CONTRIBUTING.md). For bugs, please include the output of
**LibreCompass → Diagnostics …**; it says which parts of the extension
actually registered in your LibreOffice.

## License

[Apache License 2.0](LICENSE) — permissive, with an explicit patent grant.
No copyleft: LibreCompass can be embedded in or combined with proprietary
software without an obligation to release changes.
