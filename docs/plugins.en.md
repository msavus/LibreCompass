# LibreCompass — Writing plugins

Deutsch: [plugins.de.md](plugins.de.md)

A plugin is a single Python file in your profile:
`<profile>/user/librecompass/plugins/`. Files starting with `_` are ignored.
A broken plugin is skipped silently — it cannot take the extension down.

> **Security:** plugins are ordinary Python code running with the rights of
> the LibreOffice process. Only install files you wrote or reviewed.

## Prompt plugins

The simplest kind contributes a reusable prompt:

```python
NAME = "Bullet points"
DESCRIPTION = "Turns the selection into a concise bullet list"
PROMPT = ("Rewrite the following text as a concise bullet list. "
          "One idea per bullet, no sub-bullets.")
```

It shows up under **LibreCompass → Plugins …**; *Insert prompt* puts it into
the panel's prompt field, where you choose the context and apply mode as
usual.

## Action plugins

For full control, define `run(api)` instead of (or in addition to) `PROMPT`:

```python
NAME = "Word count"
DESCRIPTION = "Counts words and characters"


def run(api):
    text = api.selection() or api.document_text()
    api.message("%d words, %d characters" % (len(text.split()), len(text)))
```

## The `api` object

This is the only interface LibreCompass promises to keep stable; everything
else in the codebase may change.

| Method | Returns / does |
| --- | --- |
| `api.selection()` | selected text (`""` if nothing selected) |
| `api.document_text()` | whole document as text |
| `api.module()` | `"writer"`, `"calc"`, `"impress"`, `"draw"` or `None` |
| `api.setting(name, default)` | a value from `settings.json` |
| `api.ask(prompt)` | one model request, returns the answer |
| `api.chat(messages)` | model request with a message list |
| `api.replace_selection(text)` | replaces the selection, `True` on success |
| `api.insert(text)` | inserts at the cursor, `True` on success |
| `api.new_document(text)` | opens a new Writer document with `text` |
| `api.message(text)` | shows an info box |

`replace_selection` and `insert` honour the `track_changes` setting
automatically. They return `False` in modules that do not support applying
(Math, Base) — check the return value or use `new_document`.

Model calls are synchronous: the UI waits. Keep prompts small, or write to a
new document rather than looping over a large text.

## Recommended pattern

Read → ask → write to a *new* document, so the original stays untouched:

```python
NAME = "Terminology check"

INSTRUCTION = ("List terms used inconsistently in the text below and "
               "suggest one variant each.\n\nTEXT:\n\"\"\"\n%s\n\"\"\"")


def run(api):
    text = api.selection() or api.document_text()
    if not text.strip():
        api.message("Nothing to check.")
        return
    limit = int(api.setting("max_context_chars", 24000))
    api.new_document("Terminology check\n\n" + api.ask(INSTRUCTION % text[:limit]))
```

## Testing a plugin

Errors inside `run()` are caught and shown with a traceback, so the fastest
loop is: edit the file, reopen the plugin dialog, run again. There is no
caching of plugin files between dialog openings.

Ready-to-copy examples ship in `examples/plugins/`:
`bullet_points.py`, `word_count.py`, `terminology_check.py`.
