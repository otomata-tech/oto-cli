"""Google Workspace commands — thin assembler over per-service modules.

Each service’s commands live in oto/tools/google/<service>/commands.py,
colocated with its API client. This file wires them under `oto google` and
keeps the cross-service `auth` command (multi-scope consent).
"""

import typer

from oto.tools.google.drive.commands import app as drive_app
from oto.tools.google.docs.commands import app as docs_app
from oto.tools.google.calendar.commands import app as calendar_app
from oto.tools.google.gmail.commands import app as gmail_app
from oto.tools.google.sheets.commands import app as sheets_app
from oto.tools.google.slides.commands import app as slides_app
from oto.tools.google.tasks.commands import app as tasks_app

app = typer.Typer(help="Google Workspace tools (Drive, Docs, Sheets, Slides, Gmail, Calendar, Tasks)")

app.add_typer(drive_app, name="drive")
app.add_typer(docs_app, name="docs")
app.add_typer(calendar_app, name="calendar")
app.add_typer(gmail_app, name="gmail")
app.add_typer(sheets_app, name="sheets")
app.add_typer(slides_app, name="slides")
app.add_typer(tasks_app, name="tasks")


@app.command("auth")
def auth(
    name: str = typer.Argument("default", help="Account name (e.g. 'gmail', 'work')"),
    list_accounts: bool = typer.Option(False, "--list", "-l", help="List configured accounts"),
):
    """Set up or list Google OAuth accounts."""
    from oto.tools.google.credentials import list_accounts as _list_accounts, setup_account, DEFAULT_SCOPES as DRIVE_SCOPES
    from oto.tools.google.gmail.lib.gmail_client import SCOPES as GMAIL_SCOPES
    from oto.tools.google.calendar.lib.calendar_client import SCOPES as CALENDAR_SCOPES
    from oto.tools.google.tasks.lib.tasks_client import SCOPES as TASKS_SCOPES

    ALL_SCOPES = list(set(GMAIL_SCOPES + CALENDAR_SCOPES + DRIVE_SCOPES + TASKS_SCOPES))

    if list_accounts:
        accounts = _list_accounts()
        if not accounts:
            print("No accounts configured. Run: oto google auth <name>")
        else:
            for a in accounts:
                print(f"  {a}")
        return

    print(f"Setting up account '{name}'... Opening browser for Google consent.")
    setup_account(name, ALL_SCOPES)
    print(f"Account '{name}' configured.")
