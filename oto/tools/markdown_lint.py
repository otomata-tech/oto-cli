"""Markdown pitfalls that render wrong, detection + auto-fix.

Dependency-free (stdlib only) so it can be reused by the PDF path (pandoc),
the Google Docs/HTML renderer and the Gmail body renderer without pulling in
the `markdown` package.

Currently handles one pitfall: a list glued to the preceding paragraph (no
blank line in between). Python-Markdown/CommonMark won't recognise it as a
list — the bullets render run together. Detection only: we warn, never modify
the source — the author fixes it.
"""

from __future__ import annotations

import re
import warnings

_LIST_LINE = re.compile(r'^\s*([-*+]|\d+[.)])\s+')  # bullet or ordered item


def find_glued_lists(text: str) -> list[int]:
    """1-based line numbers of list items glued to the preceding paragraph.

    Returns the line number of each offending first item; empty if none.
    """
    lines = text.split('\n')
    hits: list[int] = []
    for i in range(1, len(lines)):
        if _LIST_LINE.match(lines[i]):
            prev = lines[i - 1]
            if prev.strip() and not _LIST_LINE.match(prev):
                hits.append(i + 1)
    return hits


def lint_markdown(text: str, source: str = '') -> list[str]:
    """Return human-readable warnings for markdown that renders wrong.

    Pure: no side effects. Empty list when nothing is wrong.
    """
    msgs: list[str] = []
    glued = find_glued_lists(text)
    if glued:
        loc = f'{source}: ' if source else ''
        nums = ', '.join(str(n) for n in glued)
        msgs.append(
            f'{loc}liste collée au paragraphe précédent (ligne(s) {nums}) : '
            'ajoutez une ligne vide avant la puce, sinon le rendu colle les puces.'
        )
    return msgs


def warn_markdown(text: str, source: str = '') -> list[str]:
    """Emit a ``warnings.warn`` for each pitfall found; return the messages.

    Detection only — the text is never modified. Lets the CLI/MCP surface an
    alert so the author fixes the source.
    """
    msgs = lint_markdown(text, source)
    for msg in msgs:
        warnings.warn(msg, stacklevel=2)
    return msgs
