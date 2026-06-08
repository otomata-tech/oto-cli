"""Google Tasks API client using OAuth2 user credentials."""

from typing import Optional

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

SCOPES = ['https://www.googleapis.com/auth/tasks']


class TasksClientError(Exception):
    """Tasks API error."""


class TasksClient:
    """Google Tasks API client.

    Args:
        credentials: OAuth2 user credentials. If None, uses get_user_credentials().
        account: Named account to use (None = auto-detect if single account).
    """

    def __init__(self, credentials: Optional[Credentials] = None, account: Optional[str] = None):
        if credentials is None:
            from oto.tools.google.credentials import get_user_credentials
            credentials = get_user_credentials(SCOPES, account=account)
        self.service = build('tasks', 'v1', credentials=credentials)

    def list_tasklists(self, max_results: int = 100) -> list[dict]:
        """List the user's task lists."""
        resp = self.service.tasklists().list(maxResults=max_results).execute()
        return [
            {
                'id': tl['id'],
                'title': tl.get('title', ''),
                'updated': tl.get('updated', ''),
            }
            for tl in resp.get('items', [])
        ]

    def list_tasks(
        self,
        tasklist: str = '@default',
        show_completed: bool = False,
        max_results: int = 100,
    ) -> list[dict]:
        """List tasks in a task list.

        Args:
            tasklist: Task list ID (default: '@default').
            show_completed: Include completed tasks.
            max_results: Maximum number of tasks.
        """
        kwargs = {
            'tasklist': tasklist,
            'maxResults': max_results,
            'showCompleted': show_completed,
        }
        if show_completed:
            kwargs['showHidden'] = True
        resp = self.service.tasks().list(**kwargs).execute()
        return [self._format_task(t) for t in resp.get('items', [])]

    def get_task(self, task_id: str, tasklist: str = '@default') -> dict:
        """Get a single task by ID."""
        task = self.service.tasks().get(tasklist=tasklist, task=task_id).execute()
        return self._format_task(task, detailed=True)

    def create_task(
        self,
        title: str,
        notes: Optional[str] = None,
        due: Optional[str] = None,
        tasklist: str = '@default',
        parent: Optional[str] = None,
    ) -> dict:
        """Create a task.

        Args:
            title: Task title.
            notes: Free-text notes.
            due: Due date (RFC 3339, e.g. '2026-06-30T00:00:00Z'; time is ignored by Tasks).
            tasklist: Task list ID.
            parent: Parent task ID to nest under (same task list).
        """
        body: dict = {'title': title}
        if notes:
            body['notes'] = notes
        if due:
            body['due'] = due
        kwargs = {'tasklist': tasklist, 'body': body}
        if parent:
            kwargs['parent'] = parent
        task = self.service.tasks().insert(**kwargs).execute()
        return self._format_task(task)

    def update_task(
        self,
        task_id: str,
        tasklist: str = '@default',
        title: Optional[str] = None,
        notes: Optional[str] = None,
        due: Optional[str] = None,
    ) -> dict:
        """Patch a task's title, notes and/or due date."""
        body: dict = {}
        if title is not None:
            body['title'] = title
        if notes is not None:
            body['notes'] = notes
        if due is not None:
            body['due'] = due
        if not body:
            raise TasksClientError("Nothing to update: provide title, notes or due.")
        task = self.service.tasks().patch(tasklist=tasklist, task=task_id, body=body).execute()
        return self._format_task(task)

    def complete_task(self, task_id: str, tasklist: str = '@default', completed: bool = True) -> dict:
        """Mark a task completed (or reopen it with completed=False)."""
        body = {'status': 'completed' if completed else 'needsAction'}
        if not completed:
            # Clearing status alone leaves a stale completion timestamp; null it out.
            body['completed'] = None
        task = self.service.tasks().patch(tasklist=tasklist, task=task_id, body=body).execute()
        return self._format_task(task)

    def delete_task(self, task_id: str, tasklist: str = '@default') -> dict:
        """Delete a task."""
        self.service.tasks().delete(tasklist=tasklist, task=task_id).execute()
        return {'deleted': task_id, 'tasklist': tasklist}

    def create_tasklist(self, title: str) -> dict:
        """Create a new task list."""
        tl = self.service.tasklists().insert(body={'title': title}).execute()
        return {'id': tl['id'], 'title': tl.get('title', ''), 'updated': tl.get('updated', '')}

    @staticmethod
    def _format_task(task: dict, detailed: bool = False) -> dict:
        """Format a task into a clean dict."""
        result = {
            'id': task['id'],
            'title': task.get('title', '(no title)'),
            'status': task.get('status', ''),
            'due': task.get('due', ''),
            'completed': task.get('completed', ''),
            'updated': task.get('updated', ''),
        }
        notes = task.get('notes')
        if notes:
            result['notes'] = notes
        parent = task.get('parent')
        if parent:
            result['parent'] = parent
        if detailed:
            result['position'] = task.get('position', '')
            links = task.get('links', [])
            if links:
                result['links'] = links
            web = task.get('webViewLink')
            if web:
                result['webViewLink'] = web
        return result
