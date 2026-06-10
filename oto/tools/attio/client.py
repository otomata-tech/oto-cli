"""
Attio CRM API Client.

Requires: requests
"""

import re
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List

import requests

from ...config import require_secret


@dataclass
class Company:
    """Company record."""
    id: str
    name: str
    domain: str = None
    industry: str = None
    employee_count: int = None
    attributes: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Person:
    """Person record."""
    id: str
    name: str
    email: str = None
    phone: str = None
    company_id: str = None
    attributes: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Deal:
    """Deal record."""
    id: str
    name: str
    value: float = None
    stage: str = None
    company_id: str = None
    attributes: Dict[str, Any] = field(default_factory=dict)


class AttioResource:
    """Base class for Attio resources."""

    def __init__(self, client: "AttioClient", object_type: str):
        self.client = client
        self.object_type = object_type

    def list(
        self,
        limit: int = 50,
        offset: int = 0,
        sort: List[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """List records. Attio v2 n'a pas de GET records : on passe par records/query."""
        body: Dict[str, Any] = {"limit": limit, "offset": offset}
        if sort:
            body["sorts"] = sort

        return self.client._request("POST", f"objects/{self.object_type}/records/query", json=body)

    def get(self, record_id: str) -> Dict[str, Any]:
        """Get a specific record."""
        return self.client._request("GET", f"objects/{self.object_type}/records/{record_id}")

    def create(self, **attributes) -> Dict[str, Any]:
        """Create a new record."""
        data = {"data": {"values": attributes}}
        return self.client._request("POST", f"objects/{self.object_type}/records", json=data)

    def update(self, record_id: str, **attributes) -> Dict[str, Any]:
        """Update a record."""
        data = {"data": {"values": attributes}}
        return self.client._request("PATCH", f"objects/{self.object_type}/records/{record_id}", json=data)

    def delete(self, record_id: str) -> Dict[str, Any]:
        """Delete a record."""
        return self.client._request("DELETE", f"objects/{self.object_type}/records/{record_id}")

    def search(
        self,
        query: str = None,
        filters: Dict[str, Any] = None,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """Search records.

        `records/query` ne supporte pas de recherche full-text : un `query`
        est traduit en filtre `{"name": {"$contains": ...}}`. Un `filters`
        explicite (format Attio `filter`) est prioritaire.
        """
        data: Dict[str, Any] = {"limit": limit}
        if query:
            data["filter"] = {"name": {"$contains": query}}
        if filters:
            data["filter"] = filters

        return self.client._request("POST", f"objects/{self.object_type}/records/query", json=data)


class AttioNotes:
    """Notes resource."""

    def __init__(self, client: "AttioClient"):
        self.client = client

    def create(
        self,
        parent_object: str,
        parent_record_id: str,
        title: str,
        content: str,
    ) -> Dict[str, Any]:
        """
        Create a note.

        Args:
            parent_object: Object type (companies, people, deals)
            parent_record_id: Record ID to attach note to
            title: Note title
            content: Note content (markdown)

        Returns:
            Created note
        """
        data = {
            "data": {
                "parent_object": parent_object,
                "parent_record_id": parent_record_id,
                "title": title,
                "format": "markdown",
                "content": content,
            }
        }
        return self.client._request("POST", "notes", json=data)

    def list(self, parent_object: str = None, parent_record_id: str = None) -> List[Dict[str, Any]]:
        """List notes."""
        params = {}
        if parent_object:
            params["parent_object"] = parent_object
        if parent_record_id:
            params["parent_record_id"] = parent_record_id

        return self.client._request("GET", "notes", params=params)

    def get(self, note_id: str) -> Dict[str, Any]:
        """Get a single note by ID."""
        return self.client._request("GET", f"notes/{note_id}")

    def delete(self, note_id: str) -> Dict[str, Any]:
        """Delete a note by ID. Attio API does not support updating note body."""
        return self.client._request("DELETE", f"notes/{note_id}")


class AttioTasks:
    """Tasks resource."""

    def __init__(self, client: "AttioClient"):
        self.client = client

    def _get_default_assignee(self) -> str:
        """Get first workspace member ID as default assignee."""
        data = self.client._request("GET", "workspace_members")
        members = data.get("data", [])
        if not members:
            raise Exception("No workspace members found")
        return members[0]["id"]["workspace_member_id"]

    def create(
        self,
        content: str,
        deadline: str = None,
        assignee_id: str = None,
        linked_object: str = None,
        linked_record_id: str = None,
    ) -> Dict[str, Any]:
        """
        Create a task.

        Args:
            content: Task description (max 2000 chars)
            deadline: ISO date or YYYY-MM-DD deadline
            assignee_id: Workspace member ID (defaults to first member)
            linked_object: Object type to link (companies, people)
            linked_record_id: Record ID to link

        Returns:
            Created task
        """
        if not assignee_id:
            assignee_id = self._get_default_assignee()

        task_data = {
            "content": content,
            "format": "plaintext",
            "is_completed": False,
            "assignees": [{"referenced_actor_type": "workspace-member", "referenced_actor_id": assignee_id}],
        }
        if deadline:
            if len(deadline) == 10:  # YYYY-MM-DD
                deadline = f"{deadline}T00:00:00.000Z"
            task_data["deadline_at"] = deadline
        if linked_object and linked_record_id:
            task_data["linked_records"] = [{
                "target_object": linked_object,
                "target_record_id": linked_record_id,
            }]

        return self.client._request("POST", "tasks", json={"data": task_data})

    def list(self, completed: bool = None) -> List[Dict[str, Any]]:
        """List tasks."""
        params = {}
        if completed is not None:
            params["completed"] = completed

        return self.client._request("GET", "tasks", params=params)

    def update(
        self,
        task_id: str,
        deadline: str = None,
        is_completed: bool = None,
        assignee_id: str = None,
        linked_object: str = None,
        linked_record_id: str = None,
    ) -> Dict[str, Any]:
        """Update a task. Attio API only allows updating deadline_at, is_completed, assignees, linked_records."""
        task_data: Dict[str, Any] = {}
        if deadline is not None:
            if len(deadline) == 10:
                deadline = f"{deadline}T00:00:00.000Z"
            task_data["deadline_at"] = deadline
        if is_completed is not None:
            task_data["is_completed"] = is_completed
        if assignee_id is not None:
            task_data["assignees"] = [{"referenced_actor_type": "workspace-member", "referenced_actor_id": assignee_id}]
        if linked_object is not None and linked_record_id is not None:
            task_data["linked_records"] = [{
                "target_object": linked_object,
                "target_record_id": linked_record_id,
            }]
        if not task_data:
            raise ValueError("Nothing to update — pass at least one updatable field")
        return self.client._request("PATCH", f"tasks/{task_id}", json={"data": task_data})

    def get(self, task_id: str) -> Dict[str, Any]:
        """Get a single task by ID."""
        return self.client._request("GET", f"tasks/{task_id}")

    def delete(self, task_id: str) -> Dict[str, Any]:
        """Delete a task by ID."""
        return self.client._request("DELETE", f"tasks/{task_id}")


class AttioLists:
    """Lists resource — CRUD on Attio lists (saved collections of records)."""

    def __init__(self, client: "AttioClient"):
        self.client = client

    def list(self) -> Dict[str, Any]:
        """List all lists accessible to the access token."""
        return self.client._request("GET", "lists")

    def get(self, list_id_or_slug: str) -> Dict[str, Any]:
        """Get a single list by ID or slug."""
        return self.client._request("GET", f"lists/{list_id_or_slug}")

    def create(
        self,
        name: str,
        parent_object: str,
        api_slug: str = None,
        workspace_access: str = "full-access",
        workspace_member_access: List[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Create a new list.

        Args:
            name: Display name.
            parent_object: Object slug or ID the list targets (e.g. "companies").
            api_slug: API slug (optional, derived from name if omitted).
            workspace_access: "full-access" | "read-and-write" | "read-only" | None.
            workspace_member_access: per-member overrides (list of dicts with
                `workspace_member_id` + `level`).
        """
        # api_slug et workspace_member_access sont REQUIS par POST /v2/lists
        # (400 sinon) — slug dérivé du nom, accès membre vide par défaut.
        if not api_slug:
            api_slug = re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")
        data: Dict[str, Any] = {
            "name": name,
            "api_slug": api_slug,
            "parent_object": parent_object,
            "workspace_access": workspace_access,
            "workspace_member_access": workspace_member_access or [],
        }
        return self.client._request("POST", "lists", json={"data": data})

    def update(self, list_id_or_slug: str, **attributes) -> Dict[str, Any]:
        """Update an existing list (name, api_slug, access controls)."""
        return self.client._request("PATCH", f"lists/{list_id_or_slug}", json={"data": attributes})

    def views(self, list_id_or_slug: str) -> Dict[str, Any]:
        """List saved views for a list."""
        return self.client._request("GET", f"lists/{list_id_or_slug}/views")


class AttioEntries:
    """List entries — records added to a specific list."""

    def __init__(self, client: "AttioClient"):
        self.client = client

    def query(
        self,
        list_id_or_slug: str,
        filter: Dict[str, Any] = None,
        sorts: List[Dict[str, Any]] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Dict[str, Any]:
        """Query entries in a list with optional filter/sort."""
        body: Dict[str, Any] = {"limit": limit, "offset": offset}
        if filter is not None:
            body["filter"] = filter
        if sorts is not None:
            body["sorts"] = sorts
        return self.client._request("POST", f"lists/{list_id_or_slug}/entries/query", json=body)

    def get(self, list_id_or_slug: str, entry_id: str) -> Dict[str, Any]:
        """Get a single list entry by ID."""
        return self.client._request("GET", f"lists/{list_id_or_slug}/entries/{entry_id}")

    def create(
        self,
        list_id_or_slug: str,
        parent_record_id: str,
        parent_object: str,
        entry_values: Dict[str, Any] = None,
    ) -> Dict[str, Any]:
        """Add a record to a list as a new entry.

        `entry_values` est requis par l'API (400 sinon) — objet vide accepté.
        """
        data: Dict[str, Any] = {
            "parent_record_id": parent_record_id,
            "parent_object": parent_object,
            "entry_values": entry_values if entry_values is not None else {},
        }
        return self.client._request("POST", f"lists/{list_id_or_slug}/entries", json={"data": data})

    def update(
        self,
        list_id_or_slug: str,
        entry_id: str,
        entry_values: Dict[str, Any],
        overwrite_multiselect: bool = False,
    ) -> Dict[str, Any]:
        """Update entry values.

        PATCH (default) appends multiselect values; PUT overwrites.
        """
        method = "PUT" if overwrite_multiselect else "PATCH"
        return self.client._request(
            method,
            f"lists/{list_id_or_slug}/entries/{entry_id}",
            json={"data": {"entry_values": entry_values}},
        )

    def delete(self, list_id_or_slug: str, entry_id: str) -> Dict[str, Any]:
        """Delete a list entry (removes the record from the list)."""
        return self.client._request("DELETE", f"lists/{list_id_or_slug}/entries/{entry_id}")


class AttioWorkspaceMembers:
    """Workspace members — humans with access to the Attio workspace."""

    def __init__(self, client: "AttioClient"):
        self.client = client

    def list(self) -> Dict[str, Any]:
        """List all workspace members."""
        return self.client._request("GET", "workspace_members")

    def get(self, workspace_member_id: str) -> Dict[str, Any]:
        """Get a single workspace member by ID."""
        return self.client._request("GET", f"workspace_members/{workspace_member_id}")


class AttioComments:
    """Comments — threaded discussions on records, entries, or threads."""

    def __init__(self, client: "AttioClient"):
        self.client = client

    def get(self, comment_id: str) -> Dict[str, Any]:
        """Get a single comment by ID."""
        return self.client._request("GET", f"comments/{comment_id}")

    def create(
        self,
        content: str,
        author_id: str,
        thread_id: str = None,
        parent_object: str = None,
        parent_record_id: str = None,
        entry_id: str = None,
        list_id: str = None,
    ) -> Dict[str, Any]:
        """Create a comment, either on an existing thread or attached to a record/entry."""
        data: Dict[str, Any] = {
            "format": "plaintext",
            "content": content,
            "author": {"type": "workspace-member", "id": author_id},
        }
        if thread_id:
            data["thread_id"] = thread_id
        elif parent_object and parent_record_id:
            data["parent_object"] = parent_object
            data["parent_record_id"] = parent_record_id
        elif list_id and entry_id:
            data["list_id"] = list_id
            data["entry_id"] = entry_id
        else:
            raise ValueError("Provide thread_id, or (parent_object + parent_record_id), or (list_id + entry_id)")
        return self.client._request("POST", "comments", json={"data": data})

    def delete(self, comment_id: str) -> Dict[str, Any]:
        """Delete a comment. Deletes the whole thread if comment is the head."""
        return self.client._request("DELETE", f"comments/{comment_id}")


class AttioThreads:
    """Threads — collections of comments on a record/entry."""

    def __init__(self, client: "AttioClient"):
        self.client = client

    def list(
        self,
        parent_object: str = None,
        parent_record_id: str = None,
        list_id: str = None,
        entry_id: str = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Dict[str, Any]:
        """List threads, optionally filtered by parent record or entry."""
        params: Dict[str, Any] = {"limit": limit, "offset": offset}
        if parent_object:
            params["parent_object"] = parent_object
        if parent_record_id:
            params["parent_record_id"] = parent_record_id
        if list_id:
            params["list_id"] = list_id
        if entry_id:
            params["entry_id"] = entry_id
        return self.client._request("GET", "threads", params=params)

    def get(self, thread_id: str) -> Dict[str, Any]:
        """Get a thread with all its comments."""
        return self.client._request("GET", f"threads/{thread_id}")


class AttioMeetings:
    """Meetings — calendar events synced into Attio."""

    def __init__(self, client: "AttioClient"):
        self.client = client

    def list(self, limit: int = 50, offset: int = 0) -> Dict[str, Any]:
        """List meetings."""
        return self.client._request("GET", "meetings", params={"limit": limit, "offset": offset})

    def get(self, meeting_id: str) -> Dict[str, Any]:
        """Get a single meeting by ID."""
        return self.client._request("GET", f"meetings/{meeting_id}")


class AttioCallRecordings:
    """Call recordings — audio recordings attached to a meeting."""

    def __init__(self, client: "AttioClient"):
        self.client = client

    def list(self, meeting_id: str) -> Dict[str, Any]:
        """List recordings for a meeting."""
        return self.client._request("GET", f"meetings/{meeting_id}/call_recordings")

    def get(self, meeting_id: str, call_recording_id: str) -> Dict[str, Any]:
        """Get a single call recording."""
        return self.client._request("GET", f"meetings/{meeting_id}/call_recordings/{call_recording_id}")

    def transcript(self, meeting_id: str, call_recording_id: str) -> Dict[str, Any]:
        """Get the transcript for a call recording."""
        return self.client._request(
            "GET",
            f"meetings/{meeting_id}/call_recordings/{call_recording_id}/transcript",
        )


class AttioObjects:
    """Objects (meta) — system + custom objects in the workspace."""

    def __init__(self, client: "AttioClient"):
        self.client = client

    def list(self) -> Dict[str, Any]:
        """List all objects (system + custom)."""
        return self.client._request("GET", "objects")

    def get(self, object_id_or_slug: str) -> Dict[str, Any]:
        """Get a single object by ID or slug."""
        return self.client._request("GET", f"objects/{object_id_or_slug}")

    def views(self, object_id_or_slug: str) -> Dict[str, Any]:
        """List saved views for an object."""
        return self.client._request("GET", f"objects/{object_id_or_slug}/views")


class AttioAttributes:
    """Attributes (meta) — schema attributes on an object or list.

    `target` is "objects" or "lists"; `identifier` is the object/list ID or slug.
    """

    def __init__(self, client: "AttioClient"):
        self.client = client

    def list(self, target: str, identifier: str) -> Dict[str, Any]:
        """List attributes on an object or list."""
        return self.client._request("GET", f"{target}/{identifier}/attributes")

    def get(self, target: str, identifier: str, attribute: str) -> Dict[str, Any]:
        """Get a single attribute."""
        return self.client._request("GET", f"{target}/{identifier}/attributes/{attribute}")

    def options(self, target: str, identifier: str, attribute: str) -> Dict[str, Any]:
        """List select options for a select attribute."""
        return self.client._request("GET", f"{target}/{identifier}/attributes/{attribute}/options")

    def statuses(self, target: str, identifier: str, attribute: str) -> Dict[str, Any]:
        """List statuses for a status attribute."""
        return self.client._request("GET", f"{target}/{identifier}/attributes/{attribute}/statuses")


class AttioClient:
    """
    Attio CRM API client.

    Usage:
        client = AttioClient()
        companies = client.companies.list()
        client.companies.create(name="Acme Inc", domain="acme.com")
    """

    BASE_URL = "https://api.attio.com/v2"

    def __init__(self, api_key: str = None):
        """
        Initialize Attio client.

        Args:
            api_key: Attio API key (or set ATTIO_API_KEY env var)
        """
        self.api_key = api_key or require_secret("ATTIO_API_KEY")

        # Initialize resources
        self.companies = AttioResource(self, "companies")
        self.people = AttioResource(self, "people")
        self.deals = AttioResource(self, "deals")
        self.notes = AttioNotes(self)
        self.tasks = AttioTasks(self)
        self.lists = AttioLists(self)
        self.entries = AttioEntries(self)
        self.workspace_members = AttioWorkspaceMembers(self)
        self.comments = AttioComments(self)
        self.threads = AttioThreads(self)
        self.meetings = AttioMeetings(self)
        self.call_recordings = AttioCallRecordings(self)
        self.objects = AttioObjects(self)
        self.attributes = AttioAttributes(self)

    def _request(self, method: str, endpoint: str, **kwargs) -> Any:
        """Make API request."""
        url = f"{self.BASE_URL}/{endpoint}"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        response = requests.request(method, url, headers=headers, **kwargs)

        if response.status_code == 429:
            raise Exception("Rate limit exceeded")

        if not response.ok:
            # Le corps JSON d'Attio contient la vraie raison (validation,
            # scope manquant…) — le perdre rend les 400/404 indéchiffrables.
            raise Exception(
                f"Attio API {response.status_code} on {method} /{endpoint}: {response.text[:2000]}"
            )

        if response.content:
            return response.json()
        return {}
