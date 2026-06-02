"""
Supabase Management API client.

Auth : SUPABASE_ACCESS_TOKEN (Personal Access Token `sbp_...`, créé sur
https://supabase.com/dashboard/account/tokens). Stocké dans SOPS (secrets.yaml).
Docs API : https://api.supabase.com

Requires: requests
"""

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

import requests

from ...config import require_secret

BASE = "https://api.supabase.com"
# UA explicite : l'endpoint analytics renvoie un 403 Cloudflare (1010) sur le
# User-Agent python-urllib par défaut ; un UA non-vide passe.
_UA = "oto-supabase-client/1.0"


def _headers(token: Optional[str] = None) -> Dict[str, str]:
    return {
        "Authorization": f"Bearer {token or require_secret('SUPABASE_ACCESS_TOKEN')}",
        "User-Agent": _UA,
        "Accept": "application/json",
    }


def _request(
    method: str,
    path: str,
    params: Optional[Dict[str, Any]] = None,
    json_body: Optional[Dict[str, Any]] = None,
    token: Optional[str] = None,
) -> Any:
    resp = requests.request(
        method, f"{BASE}{path}", headers=_headers(token),
        params=params, json=json_body, timeout=30,
    )
    resp.raise_for_status()
    return resp.json() if resp.content else None


def list_projects(token: Optional[str] = None) -> List[Dict[str, Any]]:
    """Liste les projets accessibles avec ce PAT."""
    return _request("GET", "/v1/projects", token=token)


def get_auth_config(project_ref: str, token: Optional[str] = None) -> Dict[str, Any]:
    """Config Auth d'un projet (site_url, uri_allow_list, providers, etc.)."""
    return _request("GET", f"/v1/projects/{project_ref}/config/auth", token=token)


def query_logs(
    project_ref: str,
    sql: Optional[str] = None,
    source: str = "auth_logs",
    limit: int = 50,
    minutes: int = 120,
    token: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    Interroge les logs d'un projet (Logflare via l'API Management).

    Args:
        project_ref: ref du projet (ex: doebdriroupduqpggcsj).
        sql: requête SQL Logflare. Si None, dernières lignes de `source`.
        source: table de logs (auth_logs, edge_logs, function_edge_logs,
                function_logs, postgres_logs, postgrest_logs, storage_logs...).
        limit: nb de lignes (si sql None).
        minutes: fenêtre temporelle (l'API exige une plage iso_timestamp_*).

    Returns:
        Liste de lignes (dict). Chaque ligne a typiquement `timestamp` + `event_message`.
    """
    if sql is None:
        sql = (
            f"select timestamp, event_message from {source} "
            f"order by timestamp desc limit {limit}"
        )
    now = datetime.now(timezone.utc)
    start = now - timedelta(minutes=minutes)
    params = {
        "sql": sql,
        # format RFC3339 avec suffixe Z (l'API rejette l'offset +00:00).
        "iso_timestamp_start": start.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "iso_timestamp_end": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    data = _request(
        "GET", f"/v1/projects/{project_ref}/analytics/endpoints/logs.all",
        params=params, token=token,
    )
    if isinstance(data, dict):
        return data.get("result", [])
    return data or []
