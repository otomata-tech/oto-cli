"""`oto google docs` command surface."""

import json

import typer
from typing import Optional

app = typer.Typer(help="Google Docs tools (create, write, headings, section)")

@app.command("create")
def docs_create(
    title: str = typer.Argument(..., help="Document title"),
    file: Optional[str] = typer.Option(None, "--file", "-f", help="Text/markdown file to import as content"),
    markdown: bool = typer.Option(False, "--markdown", "-m", help="Render markdown via HTML → Drive (tables, lists, code, links). Style resolved from .otomata/google-docs-style.css (project) or ~/.otomata/ (user)."),
    account: Optional[str] = typer.Option(None, "--account", "-a", help="Google account name"),
):
    """Create a new Google Doc, optionally importing content from a file.

    With --markdown, content is rendered to HTML and uploaded via Drive's
    native HTML importer. CSS is auto-resolved from .otomata/google-docs-style.css
    (project > user). See docs/google-docs.md for details.
    """
    from oto.tools.google.docs.lib.docs_client import DocsClient

    content = ''
    if file:
        with open(file, 'r', encoding='utf-8') as fh:
            content = fh.read()
        if not markdown and file.endswith('.md'):
            markdown = True

    client = DocsClient(account=account)
    result = client.create(title, content, markdown=markdown, account=account)
    if file:
        result['imported'] = file
    print(json.dumps(result, indent=2, ensure_ascii=False))

@app.command("write")
def docs_write(
    doc_id: str = typer.Argument(..., help="Google Docs document ID"),
    file: str = typer.Argument(..., help="Text/markdown file to write"),
    markdown: bool = typer.Option(False, "--markdown", "-m", help="Render markdown via HTML → Drive (tables, lists, code, links). Same fidelity as docs create -m."),
    account: Optional[str] = typer.Option(None, "--account", "-a", help="Google account name"),
):
    """Replace entire content of a Google Doc with a file's content.

    With --markdown, the file is rendered to HTML and the doc is overwritten
    via Drive's HTML importer — proper tables, nested lists, fenced code,
    blockquotes. Same path as `docs create -m`.
    """
    from oto.tools.google.docs.lib.docs_client import DocsClient

    with open(file, 'r', encoding='utf-8') as fh:
        content = fh.read()

    if not markdown and file.endswith('.md'):
        markdown = True

    client = DocsClient(account=account)
    result = client.replace_content(doc_id, content, markdown=markdown, account=account)
    print(json.dumps(result, indent=2, ensure_ascii=False))

@app.command("headings")
def docs_headings(
    doc_id: str = typer.Argument(..., help="Google Docs document ID"),
    account: Optional[str] = typer.Option(None, "--account", "-a", help="Google account name"),
):
    """List headings in a Google Doc."""
    from oto.tools.google.docs.lib.docs_client import DocsClient

    client = DocsClient(account=account)
    headings = client.list_headings(doc_id)
    print(json.dumps(headings, indent=2))

@app.command("section")
def docs_section(
    doc_id: str = typer.Argument(..., help="Google Docs document ID"),
    heading: str = typer.Argument(..., help="Heading text to find"),
    account: Optional[str] = typer.Option(None, "--account", "-a", help="Google account name"),
):
    """Get content of a section in a Google Doc."""
    from oto.tools.google.docs.lib.docs_client import DocsClient

    client = DocsClient(account=account)
    section = client.get_section_content(doc_id, heading)
    if section:
        print(f"# {section.title}\n")
        print(section.content)
    else:
        print(f"Section not found: {heading}")
        raise typer.Exit(1)
