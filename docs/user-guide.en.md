# LibreCompass — User guide

Deutsch: [user-guide.de.md](user-guide.de.md)

LibreCompass adds local generative AI to every LibreOffice module. Nothing
leaves your machine: the extension talks to a local model server over an
OpenAI-compatible HTTP endpoint.

## 1. Setting up a model server

Any of these work; only the endpoint differs.

| Backend | Start | Endpoint |
| --- | --- | --- |
| Ollama | `ollama serve` (often already running) | `http://localhost:11434/v1` |
| llama.cpp | `llama-server -m model.gguf` | `http://localhost:8080/v1` |
| LM Studio | start the local server in the app | `http://localhost:1234/v1` |
| vLLM | `vllm serve <model>` | `http://localhost:8000/v1` |

Pull a chat model and — if you want the knowledge base — an embedding
model:

```
ollama pull qwen3
ollama pull nomic-embed-text
```

Then open **LibreCompass → Settings …** and check the endpoint, the chat
model and the embedding model.

## 2. Quick commands

Select text (or cells, or a shape) and pick one:

| Command | What happens |
| --- | --- |
| Improve selection | fixes spelling, grammar, punctuation, style |
| Rewrite selection … | asks for an instruction, then rewrites |
| Summarize | summarizes the selection; with no selection, the whole document |
| Translate … | asks for a target language |
| Custom prompt … | free instruction on the selection |

These run in the background: the status bar shows the pending request and
you can keep working while the model thinks. The result replaces the text
you had selected when you sent it, even if you have selected something
else meanwhile. One request runs at a time.

## 3. Context menu and keyboard shortcuts

Run **LibreCompass → Set up context menu** once. After that a right-click
in Writer, Calc, Impress or Draw offers a **LibreCompass** submenu with the
same commands as the menu bar. The entries are written into LibreOffice's
own context-menu configuration, so they survive a restart; **Remove context
menu** takes them back out, and you can also edit them under
Tools → Customize → Context Menus.

Shortcuts are **not** installed automatically. Run
**LibreCompass → Set up shortcuts** once; **Remove shortcuts**
takes them back out. A combination that is already bound to
something else is never overwritten — it is reported instead.

Defaults:

| Shortcut | Command |
| --- | --- |
| Ctrl+Shift+Alt+C | open the panel (works everywhere) |
| Ctrl+Shift+Alt+I | improve selection |
| Ctrl+Shift+Alt+R | rewrite selection |
| Ctrl+Shift+Alt+Z | summarize |
| Ctrl+Shift+Alt+T | translate |
| Ctrl+Shift+Alt+P | custom prompt |

Why three modifiers: Ctrl+Shift is heavily used by LibreOffice itself
(superscript, subscript, save as, print preview, paste special), and
Ctrl+Alt is AltGr on German keyboards, where it produces characters like
@ and €. Ctrl+Shift+Alt leaves both alone.

Change them under **Tools → Customize → Keyboard**; the LibreCompass
commands are listed there under the *Add-ons* category. If a
combination collides with something your desktop environment claims,
rebind it there — the desktop wins over LibreOffice.

**If neither appears:** run **LibreCompass → Diagnostics …**. It reads the
live configuration and reports which of the three mechanisms (menu,
shortcuts, context-menu job) actually registered, plus what to do about
the ones that did not. Shortcuts that never registered can always be
assigned by hand in Tools → Customize → Keyboard; a context menu that is
registered but inactive can be switched on with
**LibreCompass → Enable context menu**.

## 4. The panel

**LibreCompass → LibreCompass panel** opens the main interface. It stays
open while you work in the document.

- **Model** — filled from the server; ↻ reloads. Your choice is saved.
- **Prompt library** — pick an entry, *Insert* puts it in the prompt field,
  *Save* stores the current prompt under a name.
- **Prompt** — free text, multiple lines.
- **Context** — what the model sees besides your prompt:
  *Selection*, *Whole document* (truncated at `max_context_chars`),
  *Knowledge base* (see below), or *No context*.
- **Chat mode** — keeps the conversation. The context is frozen into the
  system message on the first send; *Clear chat* starts over.
- **Send** streams the answer live; **Stop** aborts and keeps what arrived.
- **Apply as** — *Replace selection*, *Insert at cursor* or *New document*,
  then **Apply**. Always applies the last answer.
- **History** — the last 200 prompt/answer pairs; picking one loads it back.

## 5. Staying in control

Turn on **Record replacements as tracked changes** in the settings. Every
AI edit in Writer then appears as a tracked change under
*Edit → Track Changes* and can be accepted or rejected individually. This
is the recommended setting for documents that matter.

In Calc, only the target cell is ever written — no other cell is touched.

## 6. Behavior per module

| Module | Read selection | Replace | Insert |
| --- | --- | --- | --- |
| Writer | selected text | replaces the selection | at the cursor |
| Calc | selected cells (tab/newline separated) | top-left cell of the selection | cell below the selection |
| Impress / Draw | text of the selected shapes | first selected shape | appends to the shape; without a selection, a new text box |
| Math, Base, … | – | – | – (panel and chat work; apply via *New document*) |

## 7. Knowledge base (RAG)

**LibreCompass → Knowledge base …** indexes your own files so you can ask
questions across them.

1. *Add file …* or *Add folder …* and enter a path.
2. Text is extracted, split into chunks and embedded with the embedding
   model; the index lands in `knowledge.json` in your profile.
3. In the panel, set **Context** to *Knowledge base* and ask your question.
   The answer names the sources it used.

Readable without extra software: `txt`, `md`, `csv`, `json`, `xml`, `html`,
`odt`, `ods`, `odp`, `docx`, `xlsx`, `pptx`. Formats like `pdf`, `doc`,
`rtf` and `epub` are read by loading them invisibly in LibreOffice itself.

Notes: changing the embedding model invalidates the index (vectors from
different models are not comparable) — LibreCompass clears it and you
rebuild. Indexing runs in the background with per-file progress. The search is a linear scan in Python, which is fine into the
thousands of chunks.

## 8. Document analysis

**LibreCompass → Analyze document** produces a report in a *new* document —
the analyzed document is not modified. The report has two parts:

- **Structure** — hard numbers read directly from the document (paragraphs,
  words, headings and their outline, tables, images; sheets, filled cells,
  formulas; slides, shapes with text). These come from LibreOffice, not
  from the model.
- **Observations** — the model's comments on structure, consistency,
  readability and gaps.

## 9. Plugins

**LibreCompass → Plugins …** lists your own actions. See
[plugins.en.md](plugins.en.md) for the API and examples.

## 10. Files and settings

Everything lives in your LibreOffice profile under `user/librecompass/`:

| File | Content |
| --- | --- |
| `settings.json` | all settings |
| `prompts.json` | prompt library (editable by hand) |
| `history.json` | prompt/answer history |
| `knowledge.json` | knowledge base index |
| `plugins/` | your plugin files |

Useful keys in `settings.json`: `language` (`auto`/`en`/`de`),
`track_changes`, `stream` (set to `false` for synchronous requests),
`max_context_chars`, `chunk_size`, `chunk_overlap`, `rag_top_k`,
`temperature`, `max_tokens`, `timeout_seconds`.

## 11. Troubleshooting

| Symptom | Cause / fix |
| --- | --- |
| "Server not reachable" | model server not running, or wrong endpoint in the settings |
| HTTP 404 with a model name | the model is not pulled on the server; `ollama pull <name>` |
| Panel freezes or streaming looks odd | set `"stream": false` in `settings.json`, then reopen the panel |
| Nothing happens on a quick command | nothing was selected — the status bar shows requests |
| Knowledge base finds nothing | index empty, or embedding model not pulled |
| Menu missing after install | LibreOffice was not fully restarted (quickstarter included) |
| No LibreCompass entry on right-click | the context-menu job did not run; rebuild with `--no-context-menu` and use the menu bar, or report it |
| A shortcut does nothing | the combination is claimed by the desktop environment; rebind under Tools → Customize → Keyboard |
| A shortcut overwrote one you rely on | rebind or remove it in Tools → Customize → Keyboard, or rebuild with `--no-shortcuts` |
