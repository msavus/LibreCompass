# Security Policy

## Reporting a vulnerability

Please report security issues privately through GitHub's
[private vulnerability reporting](https://github.com/msavus/librecompass/security/advisories/new)
rather than in a public issue. Include the LibreCompass version, your
LibreOffice version and the steps to reproduce.

## Threat model

LibreCompass runs entirely on the user's machine and talks only to a model
server the user configures (by default `http://localhost:11434/v1`). It has
no telemetry and sends nothing to any other host.

Two areas deserve explicit attention:

**Plugins execute arbitrary Python.** Files in
`<profile>/user/librecompass/plugins/` run inside the LibreOffice process
with the user's full rights. This is by design — it is what makes plugins
useful — but it means a malicious plugin is as dangerous as any script the
user runs. Only install plugin files you wrote or reviewed. LibreCompass
does not download, install or update plugins on its own.

**Document content goes to the configured endpoint.** Whatever you send
(selection, whole document, knowledge-base excerpts) is transmitted to the
`base_url` in `settings.json`. Point it at a remote endpoint and your
document leaves the machine. Check that setting before using LibreCompass
with confidential material.

## What is not a vulnerability

- A model producing wrong or unwanted text. Enable
  `track_changes` to keep every AI edit individually reversible.
- Reaching a remote endpoint that the user configured themselves.
- A plugin the user installed doing what its code says.
