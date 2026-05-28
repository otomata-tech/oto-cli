"""Slack commands (send, read, list-channels, find-user).

Multi-workspace : use `-w/--workspace <slug>` (or env `OTO_SLACK_WORKSPACE`)
to target a specific workspace. Default is `otomata`. Tokens for workspace
`<slug>` are read from secrets `SLACK_<SLUG>_BOT_TOKEN` and
`SLACK_<SLUG>_USER_TOKEN` (with legacy fallback `SLACK_BOT_TOKEN` /
`SLACK_USER_TOKEN` for the default workspace).
"""

import json
import os
import sys
from typing import Optional

import typer

app = typer.Typer(help="Slack messaging — channels, DMs, history")


@app.callback()
def _slack_callback(
    ctx: typer.Context,
    workspace: Optional[str] = typer.Option(
        None,
        "--workspace",
        "-w",
        help="Workspace slug (default: env OTO_SLACK_WORKSPACE or 'otomata')",
    ),
):
    """Multi-workspace dispatcher (see module docstring)."""
    ctx.ensure_object(dict)
    ctx.obj["workspace"] = workspace or os.environ.get("OTO_SLACK_WORKSPACE") or "otomata"


def _client(ctx: typer.Context, default_as_user: bool = True):
    """Default `as_user=True` for the CLI: outbound human-style com (Oto pour Alexis).

    Pass `default_as_user=False` for automation that should look like the bot app.
    """
    from oto.tools.slack import SlackClient
    workspace = (ctx.obj or {}).get("workspace") if ctx else None
    return SlackClient(default_as_user=default_as_user, workspace=workspace)


@app.command("send")
def send(
    ctx: typer.Context,
    channel: str = typer.Argument(..., help="Channel ID, channel name, user ID, or @email for a DM"),
    text: Optional[str] = typer.Option(None, "--text", "-t", help="Message text (or read from stdin)"),
    thread_ts: Optional[str] = typer.Option(None, "--thread", help="Thread parent ts to reply into"),
    as_bot: bool = typer.Option(False, "--as-bot", help="Post as the bot app (default: as the user)"),
):
    """Send a Slack message. Text from --text or stdin.

    Default posts as the human user (Oto pour Alexis). Use --as-bot to post as
    the bot app (useful for automated notifications).

    If `channel` starts with `@` and contains `.`, it's treated as an email and
    resolved to a DM channel via users.lookupByEmail + conversations.open.

    Tip — messages with apostrophes/accents: pipe the text via stdin
    (`oto slack send <chan> < message.txt`) rather than building a shell-quoted
    --text. Mixing quote styles (e.g. the `'\''` idiom inside a double-quoted
    string) leaks literal characters into the message.
    """
    client = _client(ctx, default_as_user=not as_bot)

    if text is None:
        if sys.stdin.isatty():
            raise typer.BadParameter("Provide --text or pipe text to stdin")
        text = sys.stdin.read().rstrip()
    if not text:
        raise typer.BadParameter("Empty message")

    if "'\\''" in text:
        print(
            "warning: message contains the literal sequence \"'\\''\" — this is "
            "almost always a shell-quoting accident. Sending as-is. To avoid it, "
            "pipe the text via stdin instead of an inline --text.",
            file=sys.stderr,
        )

    target = channel
    if channel.startswith("@") and "." in channel:
        email = channel.lstrip("@")
        user = client.find_user_by_email(email)["user"]
        target = client.open_dm(user["id"])["channel"]["id"]

    result = client.post_message(target, text=text, thread_ts=thread_ts)
    print(json.dumps(result, indent=2, ensure_ascii=False))


@app.command("delete")
def delete(
    ctx: typer.Context,
    channel: str = typer.Argument(..., help="Channel ID"),
    ts: str = typer.Argument(..., help="Message timestamp"),
    as_bot: bool = typer.Option(False, "--as-bot", help="Delete a bot-posted message"),
):
    """Delete a message. Must use the same token that posted it."""
    client = _client(ctx, default_as_user=not as_bot)
    result = client.delete_message(channel, ts)
    print(json.dumps(result, indent=2, ensure_ascii=False))


@app.command("list-channels")
def list_channels(
    ctx: typer.Context,
    types: str = typer.Option("public_channel", help="Types: public_channel,private_channel,mpim,im"),
):
    """List Slack channels (uses bot token — read scopes are granted on bot)."""
    channels = _client(ctx, default_as_user=False).list_channels(types=types)
    print(json.dumps(channels, indent=2, ensure_ascii=False))


@app.command("read")
def read(
    ctx: typer.Context,
    channel: str = typer.Argument(..., help="Channel ID"),
    limit: int = typer.Option(20, "--limit", "-n", help="Max messages"),
):
    """Read recent messages from a channel (uses bot token for history scopes)."""
    result = _client(ctx, default_as_user=False).history(channel, limit=limit)
    print(json.dumps(result, indent=2, ensure_ascii=False))


@app.command("find-user")
def find_user(
    ctx: typer.Context,
    email: str = typer.Argument(..., help="Email address"),
):
    """Look up a Slack user by email."""
    client = _client(ctx, default_as_user=False)
    try:
        result = client.find_user_by_email(email)
    except Exception as e:
        if "users_not_found" in str(e):
            raise typer.Exit(
                f"No user with email '{email}' in workspace '{client.workspace}' ({_workspace_name(client)})."
            )
        raise
    print(json.dumps(result, indent=2, ensure_ascii=False))


@app.command("dm")
def open_dm(
    ctx: typer.Context,
    user: str = typer.Argument(..., help="User ID (or email — auto-resolved)"),
):
    """Open a DM channel with a user and print the channel ID."""
    client = _client(ctx, default_as_user=False)
    user_id = user
    if "@" in user and "." in user:
        user_id = client.find_user_by_email(user.lstrip("@"))["user"]["id"]
    result = client.open_dm(user_id)
    print(json.dumps(result, indent=2, ensure_ascii=False))


@app.command("search")
def search(
    ctx: typer.Context,
    query: str = typer.Argument(..., help="Slack search query (e.g. 'from:@jb', 'in:#general bug')"),
    count: int = typer.Option(20, "--count", "-n", help="Max results"),
):
    """Search messages across the workspace. Requires `search:read` on the user token."""
    # search.messages is user-token only on Slack's side
    result = _client(ctx, default_as_user=True).search_messages(query, count=count)
    print(json.dumps(result, indent=2, ensure_ascii=False))


@app.command("download")
def download(
    ctx: typer.Context,
    file_id: str = typer.Argument(..., help="Slack file ID (F...)"),
    output: Optional[str] = typer.Option(None, "--output", "-o", help="Destination path (default: ./<original_name>)"),
):
    """Download a Slack file (audio, image, PDF…) to local disk."""
    client = _client(ctx, default_as_user=True)
    info = client.file_info(file_id)
    f = info["file"]
    dest = output or f.get("name", file_id)
    client.download_file(file_id, dest)
    size_kb = os.path.getsize(dest) / 1024
    typer.echo(f"Downloaded {f.get('name', file_id)} ({f.get('pretty_type', '?')}, {size_kb:.0f} KB) → {dest}")


def _workspace_name(client) -> str:
    import requests
    try:
        r = requests.get(
            "https://slack.com/api/auth.test",
            headers={"Authorization": f"Bearer {client.bot_token or client.user_token}"},
            timeout=5,
        ).json()
        return r.get("team", "unknown")
    except Exception:
        return "unknown"
