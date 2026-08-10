---
title: Google Docs — markdown import & styling
type: reference
description: >-
  Référence pour `oto google docs create` avec le flag `-m` : rendu markdown → HTML via le Drive
  API HTML importer (`mimeType=application/vnd.google-apps.document`), convention de style CSS
  dans `.otomata/google-docs-style.css` (résolution projet → user → fallback natif Drive),
  sous-ensemble CSS supporté par Drive (font, margin, border ; pas de flex/grid/pseudo-sélecteurs)
  et extensions markdown activées (`tables`, `fenced_code`, `footnotes`, `toc`).
  Charger quand un agent crée ou style un Google Doc depuis du markdown.
---

# Google Docs — markdown import & styling

## Create a Doc from markdown

```bash
oto google docs create "Title" -f path/note.md -m -a myaccount
```

With `-m`, the markdown is rendered to HTML (tables, fenced code, links,
nested lists, blockquotes, footnotes) and uploaded via the Drive API with
`mimeType=application/vnd.google-apps.document`. Drive's native HTML
importer converts it into a Google Doc — no Docs API indexing dance.

Without `-m`, content is inserted as plain text via the Docs API.

## Styling — `.otomata/` convention

CSS resolution mirrors the secrets convention (`.otomata/secrets.env`):

1. **Project** — `.otomata/google-docs-style.css` in CWD or up to 4 parent
   directories.
2. **User** — `~/.otomata/google-docs-style.css`.
3. **Fallback** — no `<style>` block, Drive renders with its native defaults.

Project files override the user file. No CSS is hardcoded in oto.

### Drive-compatible CSS

Drive's HTML importer respects a subset of CSS. What works:

- `font-family`, `font-size`, `font-weight`, `color`
- `line-height`, `margin`, `padding`
- `border`, `border-collapse`, `background`
- `text-align`, `text-decoration`

What is ignored:

- `display: flex/grid`, `position`, `box-shadow`, gradients
- `:nth-child` and most pseudo-selectors

### Sample style

A sober report-style CSS:

```css
body { font-family: Arial, Helvetica, sans-serif; font-size: 11pt; line-height: 1.15; color: #1a1a1a; }
h1 { font-size: 20pt; font-weight: 600; margin-top: 0.2em; margin-bottom: 0.3em; }
h2 { font-size: 14pt; font-weight: 600; margin-top: 1.2em; margin-bottom: 0.4em; }
h3 { font-size: 12pt; font-weight: 600; color: #2a2a2a; }
p { margin: 0.6em 0; }
table { border-collapse: collapse; }
th, td { border: 1px solid #d0d7de; padding: 6px 10px; vertical-align: top; }
th { background: #f6f8fa; font-weight: 600; text-align: left; }
code { font-family: 'Roboto Mono', Consolas, monospace; background: #f6f8fa; padding: 1px 4px; border-radius: 3px; font-size: 90%; }
blockquote { border-left: 3px solid #d0d7de; padding-left: 12px; color: #57606a; }
a { color: #0969da; text-decoration: none; }
```

## Markdown features supported

The `markdown` Python library is invoked with these extensions:
`tables`, `fenced_code`, `sane_lists`, `attr_list`, `footnotes`, `toc`.

A pre-processor inserts a blank line before any list block that follows a
non-list line (CommonMark requires it; GFM/most authors don't). So both
of these render as a list:

```markdown
Items:
- a
- b

Items:

- a
- b
```

## What is *not* supported

- Diagrams (mermaid, graphviz) — Drive ignores them
- Math expressions (`$x$`, `$$...$$`) — pass through as text
- Custom CSS classes via `attr_list` — Drive strips them
- Embedded raw HTML beyond what `markdown` outputs

For these, edit the doc post-creation via the Docs API or a different tool.
