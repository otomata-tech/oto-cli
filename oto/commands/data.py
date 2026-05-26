"""Datastore — stockage de données structurées légères par user.

Backend Google Sheets via le MCP server (`mcp.oto.ninja`). Auth via le
secret `OTO_API_KEY` (issu sur `https://oto.ninja/account` ou via le script
`issue_token.py` côté serveur).

Chaque namespace = un Google Sheet dans le Drive du user. Schéma libre :
les colonnes apparaissent quand de nouveaux champs sont écrits.

Exemples :
    oto data namespaces
    oto data create timetrack
    oto data append timetrack '{"date":"2026-05-19","project":"roundtable","hours":3}'
    oto data list timetrack --filter project=roundtable
    oto data get timetrack <_id>
    oto data update timetrack <_id> '{"billed":true}'
    oto data rm-row timetrack <_id>
    oto data url timetrack
    oto data rm timetrack
"""
from __future__ import annotations

import json
from typing import Optional

import typer

app = typer.Typer(help="Datastore — stockage structuré per-user (Google Sheets via MCP)")


def _client():
    from oto.tools.datastore.client import DatastoreClient
    return DatastoreClient()


def _print(data) -> None:
    print(json.dumps(data, indent=2, ensure_ascii=False))


@app.command("namespaces")
def namespaces():
    """Liste les namespaces du user."""
    _print(_client().list_namespaces())


@app.command("create")
def create(namespace: str = typer.Argument(..., help="Nom du namespace (kebab-case)")):
    """Crée un namespace (provisionne le Google Sheet)."""
    _print(_client().create_namespace(namespace))


@app.command("rm")
def rm(namespace: str = typer.Argument(...)):
    """Supprime un namespace (Sheet → corbeille Drive)."""
    _print(_client().delete_namespace(namespace))


@app.command("url")
def url(namespace: str = typer.Argument(...)):
    """Affiche l'URL du Google Sheet."""
    print(_client().url(namespace))


@app.command("append")
def append(
    namespace: str = typer.Argument(...),
    row_json: str = typer.Argument(..., help="JSON de la row à ajouter"),
):
    """Ajoute une row (JSON dict). Les nouveaux champs créent des colonnes."""
    try:
        row = json.loads(row_json)
    except json.JSONDecodeError as e:
        raise typer.BadParameter(f"JSON invalide: {e}")
    if not isinstance(row, dict):
        raise typer.BadParameter("row doit être un dict JSON")
    _print(_client().append(namespace, row))


@app.command("list")
def list_rows(
    namespace: str = typer.Argument(...),
    filter: Optional[list[str]] = typer.Option(
        None, "--filter", "-f",
        help="Filtre exact `key=value`, répétable",
    ),
    limit: int = typer.Option(100, "--limit", "-n"),
):
    """Liste les rows. Filtres exacts répétables : `-f project=roundtable -f billed=True`."""
    filter_dict: dict[str, str] = {}
    for f in (filter or []):
        if "=" not in f:
            raise typer.BadParameter(f"filtre invalide `{f}` (format: key=value)")
        k, v = f.split("=", 1)
        filter_dict[k.strip()] = v.strip()
    _print(_client().list_rows(namespace, filter=filter_dict or None, limit=limit))


@app.command("get")
def get(
    namespace: str = typer.Argument(...),
    row_id: str = typer.Argument(..., help="_id de la row"),
):
    """Affiche une row par _id."""
    _print(_client().get(namespace, row_id))


@app.command("update")
def update(
    namespace: str = typer.Argument(...),
    row_id: str = typer.Argument(...),
    patch_json: str = typer.Argument(..., help="JSON partiel à appliquer"),
):
    """Update partiel d'une row par _id."""
    try:
        patch = json.loads(patch_json)
    except json.JSONDecodeError as e:
        raise typer.BadParameter(f"JSON invalide: {e}")
    if not isinstance(patch, dict):
        raise typer.BadParameter("patch doit être un dict JSON")
    _print(_client().update(namespace, row_id, patch))


@app.command("rm-row")
def rm_row(
    namespace: str = typer.Argument(...),
    row_id: str = typer.Argument(...),
):
    """Supprime une row par _id."""
    _print(_client().delete_row(namespace, row_id))


@app.command("share")
def share(
    namespace: str = typer.Argument(..., help="Namespace à partager"),
    email: str = typer.Argument(..., help="Email du destinataire (user oto)"),
    permission: str = typer.Option("write", "--permission", "-p", help="'read' ou 'write'"),
):
    """Partage un namespace avec un autre user oto (DB + Google Drive)."""
    _print(_client().share(namespace, email, permission))


@app.command("unshare")
def unshare(
    namespace: str = typer.Argument(..., help="Namespace à départager"),
    email: str = typer.Argument(..., help="Email du user à retirer"),
):
    """Retire l'accès d'un user à un namespace partagé."""
    _print(_client().unshare(namespace, email))
