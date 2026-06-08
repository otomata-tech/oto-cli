"""`oto google tasks` command surface."""

import json

import typer
from typing import Optional

app = typer.Typer(help="Google Tasks tools (lists, list, get, add, update, done, reopen, rm)")

def _normalize_due(due: Optional[str]) -> Optional[str]:
    """Accept a YYYY-MM-DD date and expand it to the RFC 3339 the Tasks API wants."""
    if due is None:
        return None
    if len(due) == 10 and due[4] == '-' and due[7] == '-':
        return f"{due}T00:00:00.000Z"
    return due

@app.command("lists")
def tasks_lists(
    account: Optional[str] = typer.Option(None, "--account", "-a", help="Google account name"),
):
    """List the user's task lists."""
    from oto.tools.google.tasks.lib.tasks_client import TasksClient

    client = TasksClient(account=account)
    tasklists = client.list_tasklists()
    print(json.dumps({"count": len(tasklists), "tasklists": tasklists}, indent=2, ensure_ascii=False))

@app.command("list")
def tasks_list(
    tasklist: str = typer.Option("@default", "--list", "-l", help="Task list ID"),
    completed: bool = typer.Option(False, "--completed", help="Include completed tasks"),
    limit: int = typer.Option(100, "--limit", "-n", help="Max tasks"),
    account: Optional[str] = typer.Option(None, "--account", "-a", help="Google account name"),
):
    """List tasks in a task list (default: '@default')."""
    from oto.tools.google.tasks.lib.tasks_client import TasksClient

    client = TasksClient(account=account)
    tasks = client.list_tasks(tasklist=tasklist, show_completed=completed, max_results=limit)
    print(json.dumps({"count": len(tasks), "tasks": tasks}, indent=2, ensure_ascii=False))

@app.command("get")
def tasks_get(
    task_id: str = typer.Argument(..., help="Task ID"),
    tasklist: str = typer.Option("@default", "--list", "-l", help="Task list ID"),
    account: Optional[str] = typer.Option(None, "--account", "-a", help="Google account name"),
):
    """Get details of a task."""
    from oto.tools.google.tasks.lib.tasks_client import TasksClient

    client = TasksClient(account=account)
    task = client.get_task(task_id, tasklist=tasklist)
    print(json.dumps(task, indent=2, ensure_ascii=False))

@app.command("add")
def tasks_add(
    title: str = typer.Argument(..., help="Task title"),
    notes: Optional[str] = typer.Option(None, "--notes", help="Free-text notes"),
    due: Optional[str] = typer.Option(None, "--due", "-d", help="Due date (YYYY-MM-DD or RFC 3339)"),
    tasklist: str = typer.Option("@default", "--list", "-l", help="Task list ID"),
    parent: Optional[str] = typer.Option(None, "--parent", help="Parent task ID (nest as subtask)"),
    account: Optional[str] = typer.Option(None, "--account", "-a", help="Google account name"),
):
    """Add a task."""
    from oto.tools.google.tasks.lib.tasks_client import TasksClient

    client = TasksClient(account=account)
    task = client.create_task(title=title, notes=notes, due=_normalize_due(due), tasklist=tasklist, parent=parent)
    print(json.dumps(task, indent=2, ensure_ascii=False))

@app.command("update")
def tasks_update(
    task_id: str = typer.Argument(..., help="Task ID"),
    title: Optional[str] = typer.Option(None, "--title", help="New title"),
    notes: Optional[str] = typer.Option(None, "--notes", help="New notes"),
    due: Optional[str] = typer.Option(None, "--due", "-d", help="New due date (YYYY-MM-DD or RFC 3339)"),
    tasklist: str = typer.Option("@default", "--list", "-l", help="Task list ID"),
    account: Optional[str] = typer.Option(None, "--account", "-a", help="Google account name"),
):
    """Update a task's title, notes and/or due date."""
    from oto.tools.google.tasks.lib.tasks_client import TasksClient

    client = TasksClient(account=account)
    task = client.update_task(task_id, tasklist=tasklist, title=title, notes=notes, due=_normalize_due(due))
    print(json.dumps(task, indent=2, ensure_ascii=False))

@app.command("done")
def tasks_done(
    task_id: str = typer.Argument(..., help="Task ID"),
    tasklist: str = typer.Option("@default", "--list", "-l", help="Task list ID"),
    account: Optional[str] = typer.Option(None, "--account", "-a", help="Google account name"),
):
    """Mark a task as completed."""
    from oto.tools.google.tasks.lib.tasks_client import TasksClient

    client = TasksClient(account=account)
    task = client.complete_task(task_id, tasklist=tasklist, completed=True)
    print(json.dumps(task, indent=2, ensure_ascii=False))

@app.command("reopen")
def tasks_reopen(
    task_id: str = typer.Argument(..., help="Task ID"),
    tasklist: str = typer.Option("@default", "--list", "-l", help="Task list ID"),
    account: Optional[str] = typer.Option(None, "--account", "-a", help="Google account name"),
):
    """Reopen a completed task (back to needsAction)."""
    from oto.tools.google.tasks.lib.tasks_client import TasksClient

    client = TasksClient(account=account)
    task = client.complete_task(task_id, tasklist=tasklist, completed=False)
    print(json.dumps(task, indent=2, ensure_ascii=False))

@app.command("rm")
def tasks_rm(
    task_id: str = typer.Argument(..., help="Task ID"),
    tasklist: str = typer.Option("@default", "--list", "-l", help="Task list ID"),
    account: Optional[str] = typer.Option(None, "--account", "-a", help="Google account name"),
):
    """Delete a task."""
    from oto.tools.google.tasks.lib.tasks_client import TasksClient

    client = TasksClient(account=account)
    result = client.delete_task(task_id, tasklist=tasklist)
    print(json.dumps(result, indent=2, ensure_ascii=False))

@app.command("add-list")
def tasks_add_list(
    title: str = typer.Argument(..., help="Task list title"),
    account: Optional[str] = typer.Option(None, "--account", "-a", help="Google account name"),
):
    """Create a new task list."""
    from oto.tools.google.tasks.lib.tasks_client import TasksClient

    client = TasksClient(account=account)
    tasklist = client.create_tasklist(title)
    print(json.dumps(tasklist, indent=2, ensure_ascii=False))
