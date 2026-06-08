"""`oto google gmail` command surface."""

import json

import typer
from typing import Optional

app = typer.Typer(help="Gmail tools (search, list, get, send, draft, draft-list, draft-delete, reply, archive, attachments)")

def _apply_signature(client, body: str, html: Optional[str]) -> Optional[str]:
    """Convert plain text body to HTML with Gmail signature appended."""
    import html as html_mod
    signature = client.get_signature()
    if not signature:
        return html
    body_html = html or '<div dir="ltr">' + html_mod.escape(body).replace('\n', '<br>') + '</div>'
    return body_html + '<br>--<br>' + signature

def _markdown_to_html_fragment(text: str) -> str:
    """Render markdown body to an HTML fragment suitable for Gmail.

    Warns (no auto-fix) on markdown pitfalls such as a list glued to the
    preceding paragraph; supports tables, fenced code, inline attributes. No
    <html>/<body> wrapping — Gmail accepts the fragment directly inside the
    multipart text/html part.
    """
    import markdown as _md
    from oto.tools.markdown_lint import warn_markdown
    warn_markdown(text, source='corps du mail')
    return _md.markdown(
        text,
        extensions=['tables', 'fenced_code', 'sane_lists', 'attr_list'],
        output_format='html',
    )

def _resolve_body_format(body: str, markdown: bool, html: bool) -> tuple[str, Optional[str]]:
    """Resolve the (plain_text, html) tuple to send based on format flags.

    --html              : body is raw HTML, sent as-is in text/html. Takes
                          precedence over --markdown when both are set.
    --markdown (default): body is markdown, rendered to HTML for the multipart
                          text/html part. Markdown source remains plain text.
    --no-markdown alone : plain text only, no HTML part.
    """
    if html:
        return body, body
    if markdown:
        return body, _markdown_to_html_fragment(body)
    return body, None

@app.command("list")
def gmail_list(
    query: Optional[str] = typer.Option(None, help="Gmail search query"),
    label: Optional[str] = typer.Option(None, help="Filter by label ID"),
    limit: int = typer.Option(20, "--limit", "-n", help="Max messages"),
    account: Optional[str] = typer.Option(None, "--account", "-a", help="Google account name"),
):
    """List recent Gmail messages."""
    from oto.tools.google.gmail.lib.gmail_client import GmailClient

    client = GmailClient(account=account)
    label_ids = [label] if label else None
    messages = client.list_messages(query=query, label_ids=label_ids, max_results=limit)
    print(json.dumps({"count": len(messages), "messages": messages}, indent=2, ensure_ascii=False))

@app.command("search")
def gmail_search(
    query: str = typer.Argument(..., help="Gmail search query (e.g. 'is:unread', 'from:user@example.com')"),
    limit: int = typer.Option(20, "--limit", "-n", help="Max messages"),
    account: Optional[str] = typer.Option(None, "--account", "-a", help="Google account name"),
):
    """Search Gmail messages."""
    from oto.tools.google.gmail.lib.gmail_client import GmailClient

    client = GmailClient(account=account)
    messages = client.search(query=query, max_results=limit)
    print(json.dumps({"count": len(messages), "messages": messages}, indent=2, ensure_ascii=False))

@app.command("get")
def gmail_get(
    message_id: str = typer.Argument(..., help="Gmail message ID"),
    account: Optional[str] = typer.Option(None, "--account", "-a", help="Google account name"),
):
    """Read a Gmail message."""
    from oto.tools.google.gmail.lib.gmail_client import GmailClient

    client = GmailClient(account=account)
    message = client.get_message(message_id)
    print(json.dumps(message, indent=2, ensure_ascii=False))

@app.command("attachments")
def gmail_attachments(
    message_id: str = typer.Argument(..., help="Gmail message ID"),
    output: str = typer.Option(".", "--output", "-o", help="Output directory"),
    account: Optional[str] = typer.Option(None, "--account", "-a", help="Google account name"),
):
    """Download attachments from a Gmail message."""
    from oto.tools.google.gmail.lib.gmail_client import GmailClient

    client = GmailClient(account=account)
    files = client.download_attachments(message_id, output)
    print(json.dumps({"count": len(files), "files": files}, indent=2, ensure_ascii=False))

@app.command("draft")
def gmail_draft(
    to: Optional[str] = typer.Option(None, help="Recipient email (auto-detected with --reply-to)"),
    subject: Optional[str] = typer.Option(None, help="Email subject (auto-detected with --reply-to)"),
    body: str = typer.Option(..., help="Email body. Format depends on --markdown / --html / neither (plain)."),
    markdown: bool = typer.Option(True, "--markdown/--no-markdown", "-m", help="Body is markdown — rendered to HTML. Mutually exclusive with --html. Default: on."),
    html: bool = typer.Option(False, "--html", help="Body is raw HTML — sent as-is. Mutually exclusive with --markdown."),
    cc: Optional[str] = typer.Option(None, help="CC recipients"),
    bcc: Optional[str] = typer.Option(None, help="BCC recipients"),
    reply_to: Optional[str] = typer.Option(None, "--reply-to", "-r", help="Message ID to reply to (threads the draft)"),
    attach: Optional[list[str]] = typer.Option(None, "--attach", "-f", help="File paths to attach"),
    sign: bool = typer.Option(True, "--sign/--no-sign", help="Append Gmail signature"),
    account: Optional[str] = typer.Option(None, "--account", "-a", help="Google account name"),
):
    """Create a draft email in Gmail. Use --reply-to for threaded replies. Body defaults to markdown; pass --html for raw HTML or --no-markdown for plain text."""
    from oto.tools.google.gmail.lib.gmail_client import GmailClient

    plain, body_html = _resolve_body_format(body, markdown, html)
    client = GmailClient(account=account)
    final_html = _apply_signature(client, plain, body_html) if sign else body_html
    if reply_to:
        result = client.create_draft_reply(message_id=reply_to, body=plain, html=final_html, cc=cc, attachments=attach)
    else:
        if not to or not subject:
            raise typer.BadParameter("--to and --subject are required (unless using --reply-to)")
        result = client.create_draft(to=to, subject=subject, body=plain, html=final_html, cc=cc, bcc=bcc, attachments=attach)
    print(json.dumps(result, indent=2))

@app.command("draft-list")
def gmail_draft_list(
    max_results: int = typer.Option(20, "--max-results", "-n", help="Maximum number of drafts to list"),
    account: Optional[str] = typer.Option(None, "--account", "-a", help="Google account name"),
):
    """List Gmail drafts (id, subject, to, date)."""
    from oto.tools.google.gmail.lib.gmail_client import GmailClient

    client = GmailClient(account=account)
    drafts = client.list_drafts(max_results=max_results)
    print(json.dumps({"count": len(drafts), "drafts": drafts}, indent=2, ensure_ascii=False))

@app.command("draft-delete")
def gmail_draft_delete(
    draft_ids: list[str] = typer.Argument(..., help="One or more draft IDs to delete"),
    account: Optional[str] = typer.Option(None, "--account", "-a", help="Google account name"),
):
    """Delete one or more Gmail drafts by ID."""
    from oto.tools.google.gmail.lib.gmail_client import GmailClient

    client = GmailClient(account=account)
    results = []
    for did in draft_ids:
        try:
            results.append(client.delete_draft(did))
        except Exception as e:
            results.append({"id": did, "error": str(e)})
    print(json.dumps({"count": len(results), "results": results}, indent=2))

@app.command("reply")
def gmail_reply(
    message_id: str = typer.Argument(..., help="Gmail message ID to reply to"),
    body: str = typer.Option(..., help="Reply body. Format depends on --markdown / --html / neither (plain)."),
    markdown: bool = typer.Option(True, "--markdown/--no-markdown", "-m", help="Body is markdown — rendered to HTML. Default: on."),
    html: bool = typer.Option(False, "--html", help="Body is raw HTML — sent as-is. Takes precedence over --markdown."),
    cc: Optional[str] = typer.Option(None, help="CC recipients"),
    attach: Optional[list[str]] = typer.Option(None, "--attach", "-f", help="File paths to attach"),
    sign: bool = typer.Option(True, "--sign/--no-sign", help="Append Gmail signature"),
    from_name: Optional[str] = typer.Option(None, "--from-name", help="Display name override for the From header (email stays the authenticated address)"),
    account: Optional[str] = typer.Option(None, "--account", "-a", help="Google account name"),
):
    """Reply to a Gmail message (preserves thread). Body defaults to markdown; pass --html for raw HTML or --no-markdown for plain text."""
    from oto.tools.google.gmail.lib.gmail_client import GmailClient

    plain, body_html = _resolve_body_format(body, markdown, html)
    client = GmailClient(account=account)
    final_html = _apply_signature(client, plain, body_html) if sign else body_html
    result = client.reply(message_id=message_id, body=plain, html=final_html, cc=cc, attachments=attach, from_name=from_name)
    print(json.dumps(result, indent=2))

@app.command("send")
def gmail_send(
    to: str = typer.Option(..., help="Recipient email"),
    subject: str = typer.Option(..., help="Email subject"),
    body: str = typer.Option(..., help="Email body. Format depends on --markdown / --html / neither (plain)."),
    markdown: bool = typer.Option(True, "--markdown/--no-markdown", "-m", help="Body is markdown — rendered to HTML. Default: on."),
    html: bool = typer.Option(False, "--html", help="Body is raw HTML — sent as-is. Takes precedence over --markdown."),
    cc: Optional[str] = typer.Option(None, help="CC recipients"),
    bcc: Optional[str] = typer.Option(None, help="BCC recipients"),
    attach: Optional[list[str]] = typer.Option(None, "--attach", "-f", help="File paths to attach"),
    sign: bool = typer.Option(True, "--sign/--no-sign", help="Append Gmail signature"),
    from_name: Optional[str] = typer.Option(None, "--from-name", help="Display name override for the From header (email stays the authenticated address)"),
    account: Optional[str] = typer.Option(None, "--account", "-a", help="Google account name"),
):
    """Send an email via Gmail. Body defaults to markdown; pass --html for raw HTML or --no-markdown for plain text."""
    from oto.tools.google.gmail.lib.gmail_client import GmailClient

    plain, body_html = _resolve_body_format(body, markdown, html)
    client = GmailClient(account=account)
    final_html = _apply_signature(client, plain, body_html) if sign else body_html
    result = client.send(to=to, subject=subject, body=plain, html=final_html, cc=cc, bcc=bcc, attachments=attach, from_name=from_name)
    print(json.dumps(result, indent=2))

@app.command("archive")
def gmail_archive(
    message_ids: Optional[list[str]] = typer.Argument(None, help="Gmail message IDs to archive"),
    query: Optional[str] = typer.Option(None, "--query", "-q", help="Archive all messages matching this Gmail query"),
    account: Optional[str] = typer.Option(None, "--account", "-a", help="Google account name"),
):
    """Archive Gmail messages (remove from inbox)."""
    from oto.tools.google.gmail.lib.gmail_client import GmailClient

    client = GmailClient(account=account)
    ids = list(message_ids or [])
    if query:
        msgs = client.search(query=query, max_results=100)
        ids.extend(m['id'] for m in msgs if 'INBOX' in m.get('labelIds', []))
    if not ids:
        print(json.dumps({"archived": 0, "message": "No messages to archive"}))
        return
    results = client.archive_messages(ids)
    print(json.dumps({"archived": len(results), "results": results}, indent=2))
