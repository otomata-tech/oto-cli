---
title: Gmail — markdown / HTML body rendering
type: reference
description: >-
  Référence des flags de format du corps de message pour les commandes `oto google gmail send`,
  `reply` et `draft` : `--markdown` (défaut, rendu HTML multipart), `--html` (HTML brut),
  `--no-markdown` (texte pur). Documente la structure multipart, les extensions markdown
  supportées (`tables`, `fenced_code`, `sane_lists`, `attr_list`), les limites (images inline,
  CSS custom, footnotes), et les fonctions d'implémentation clés dans `oto/commands/google.py`.
  Charger quand un agent doit choisir le bon flag de format ou diagnostiquer un rendu mail.
---

# Gmail — markdown / HTML body rendering

`oto google gmail send`, `reply`, and `draft` accept a single `--body` argument
plus two mutually-exclusive format flags. The signature configured in Gmail is
appended automatically (toggle with `--sign / --no-sign`).

## Format flags

| Flag             | Behavior                                                                                |
|------------------|-----------------------------------------------------------------------------------------|
| `--markdown` *(default, on)* | Body is markdown — rendered to an HTML fragment for the multipart `text/html` part. Markdown source is kept as the `text/plain` fallback. |
| `--html`         | Body is raw HTML — sent as-is in `text/html`. Takes precedence when combined with `--markdown`. |
| `--no-markdown` (alone) | Plain text only. No `text/html` part is generated.                              |

## Examples

Markdown (default):

```bash
oto google gmail send -a myaccount \
  --to user@example.com \
  --subject "Quick update" \
  --body "$(cat note.md)"
```

Raw HTML:

```bash
oto google gmail send -a myaccount \
  --to user@example.com \
  --subject "Custom HTML" \
  --html \
  --body "<p>Hello <b>world</b></p>"
```

Plain text:

```bash
oto google gmail send -a myaccount \
  --to user@example.com \
  --subject "Plain" \
  --no-markdown \
  --body "Just text, no formatting."
```

Reply (threaded):

```bash
oto google gmail reply <message_id> -a myaccount \
  --body "$(cat reply.md)"
```

## Markdown features supported

Same renderer as `oto google docs -m`, restricted to extensions that render
well in mail clients: `tables`, `fenced_code`, `sane_lists`, `attr_list`.

A pre-processor inserts a blank line before any list block that follows a
non-list line (CommonMark requires it; GFM / most authors don't). So both of
these render as a list:

```markdown
Items:
- a
- b

Items:

- a
- b
```

## What is *not* supported

- Inline images via markdown `![alt](path)` — Gmail blocks remote images by
  default; for embedded inline images use `--attach` plus a CID-aware HTML body
  via `--html`.
- Custom CSS via `attr_list` — most mail clients strip class attributes; rely
  on inline styles in `--html` mode if needed.
- Footnotes / TOC — disabled in the gmail renderer (kept light for readability).

## Multipart structure

The sent message is always `multipart/alternative` (when `--sign` is on), with:

- `text/plain` — markdown source (or the body verbatim in `--html` / `--no-markdown` modes)
- `text/html` — rendered HTML fragment with the Gmail signature appended

Mail clients pick the part they prefer; modern ones default to `text/html`.

## Implementation

- `oto/commands/google.py:_markdown_to_html_fragment` — markdown → HTML fragment
- `oto/commands/google.py:_resolve_body_format` — flag → (plain, html) tuple
- `oto/commands/google.py:_apply_signature` — append Gmail signature to the HTML part
- `oto/tools/google/docs/lib/markdown_to_html.py:_normalize_lists` — shared list-normalization helper (also used by `oto google docs -m`)
