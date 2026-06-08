"""`oto google calendar` command surface."""

import json

import typer
from typing import Optional

app = typer.Typer(help="Google Calendar tools (list, today, upcoming, search, get)")

@app.command("list")
def calendar_list(
    account: Optional[str] = typer.Option(None, "--account", "-a", help="Google account name"),
):
    """List available calendars."""
    from oto.tools.google.calendar.lib.calendar_client import CalendarClient

    client = CalendarClient(account=account)
    calendars = client.list_calendars()
    print(json.dumps({"count": len(calendars), "calendars": calendars}, indent=2, ensure_ascii=False))

@app.command("today")
def calendar_today(
    calendar_id: str = typer.Option("primary", "--calendar", "-c", help="Calendar ID"),
    account: Optional[str] = typer.Option(None, "--account", "-a", help="Google account name"),
):
    """List today's events."""
    from oto.tools.google.calendar.lib.calendar_client import CalendarClient

    client = CalendarClient(account=account)
    events = client.today(calendar_id=calendar_id)
    print(json.dumps({"count": len(events), "events": events}, indent=2, ensure_ascii=False))

@app.command("upcoming")
def calendar_upcoming(
    days: int = typer.Option(7, "--days", "-d", help="Number of days ahead"),
    calendar_id: str = typer.Option("primary", "--calendar", "-c", help="Calendar ID"),
    limit: int = typer.Option(50, "--limit", "-n", help="Max events"),
    account: Optional[str] = typer.Option(None, "--account", "-a", help="Google account name"),
):
    """List upcoming events (default: next 7 days)."""
    from oto.tools.google.calendar.lib.calendar_client import CalendarClient

    client = CalendarClient(account=account)
    events = client.upcoming(days=days, calendar_id=calendar_id, max_results=limit)
    print(json.dumps({"count": len(events), "events": events}, indent=2, ensure_ascii=False))

@app.command("search")
def calendar_search(
    query: str = typer.Argument(..., help="Search query"),
    days: int = typer.Option(30, "--days", "-d", help="Search window in days (future). Use --past for past events."),
    past: int = typer.Option(0, "--past", "-p", help="Search window in past days"),
    calendar_id: str = typer.Option("primary", "--calendar", "-c", help="Calendar ID"),
    limit: int = typer.Option(20, "--limit", "-n", help="Max events"),
    account: Optional[str] = typer.Option(None, "--account", "-a", help="Google account name"),
):
    """Search calendar events."""
    from oto.tools.google.calendar.lib.calendar_client import CalendarClient
    from datetime import datetime, timedelta, timezone

    client = CalendarClient(account=account)
    now = datetime.now(timezone.utc)
    time_min = (now - timedelta(days=past)).isoformat() if past else now.isoformat()
    time_max = (now + timedelta(days=days)).isoformat()
    events = client.list_events(
        calendar_id=calendar_id,
        time_min=time_min,
        time_max=time_max,
        max_results=limit,
        query=query,
    )
    print(json.dumps({"count": len(events), "events": events}, indent=2, ensure_ascii=False))

@app.command("get")
def calendar_get(
    event_id: str = typer.Argument(..., help="Event ID"),
    calendar_id: str = typer.Option("primary", "--calendar", "-c", help="Calendar ID"),
    account: Optional[str] = typer.Option(None, "--account", "-a", help="Google account name"),
):
    """Get details of a calendar event."""
    from oto.tools.google.calendar.lib.calendar_client import CalendarClient

    client = CalendarClient(account=account)
    event = client.get_event(event_id, calendar_id=calendar_id)
    print(json.dumps(event, indent=2, ensure_ascii=False))

@app.command("create")
def calendar_create(
    summary: str = typer.Argument(..., help="Event title"),
    date: str = typer.Option(..., "--date", "-d", help="Date or datetime (YYYY-MM-DD or ISO 8601)"),
    end: Optional[str] = typer.Option(None, "--end", "-e", help="End date/datetime (defaults to same day or +1h)"),
    description: Optional[str] = typer.Option(None, "--desc", help="Event description"),
    location: Optional[str] = typer.Option(None, "--location", "-l", help="Event location"),
    account: Optional[str] = typer.Option(None, "--account", "-a", help="Google account name"),
):
    """Create a calendar event."""
    from oto.tools.google.calendar.lib.calendar_client import CalendarClient

    client = CalendarClient(account=account)
    event = client.create_event(summary=summary, start=date, end=end, description=description, location=location)
    print(json.dumps(event, indent=2, ensure_ascii=False))
