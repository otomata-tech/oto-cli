"""Façade CLI pour les endpoints `mcp.oto.ninja` — gestion des secrets
multi-user stockés côté DB (cookies LinkedIn/Crunchbase, API keys
provider). Auth via `OTO_API_KEY` (SOPS).

Pattern d'usage typique pour composer avec un outil qui attend un secret
en variable d'env :

    export LINKEDIN_COOKIE=$(oto ninja secrets get LINKEDIN_COOKIE)
    export LINKEDIN_USER_AGENT=$(oto ninja secrets get LINKEDIN_USER_AGENT)
    oto browser linkedin posts <url>

Commandes :
    oto ninja secrets list                 → noms des secrets configurés
    oto ninja secrets get <NAME>           → valeur raw sur stdout
    oto ninja secrets set <NAME> <VALUE>   → écrit la valeur (cookie ou clé)
    oto ninja secrets delete <NAME>        → efface (par groupe)

Conventions de nommage (mapping name → endpoint) :
    LINKEDIN_COOKIE       → /api/settings/linkedin       (champ `cookie`)
    LINKEDIN_USER_AGENT   → /api/settings/linkedin       (champ `user_agent`)
    CRUNCHBASE_USER_AGENT → /api/settings/crunchbase     (champ `user_agent`)
    SERPER_API_KEY        → /api/settings/api-keys/serper  (champ `key`)
    HUNTER_API_KEY, SIRENE_API_KEY, ATTIO_API_KEY, LEMLIST_API_KEY

CRUNCHBASE_COOKIES (liste JSON) n'est pas exposé via cette interface
flat — utiliser le SDK Python ou poser via l'UI oto.ninja/account.
"""
from __future__ import annotations

import json
import sys
from typing import Optional

import typer


app = typer.Typer(help="Façade vers mcp.oto.ninja (secrets, configuration)")
secrets_app = typer.Typer(help="Lecture/écriture des secrets stockés côté DB")
app.add_typer(secrets_app, name="secrets")


# --- name → endpoint mapping -------------------------------------------------

_LINKEDIN_FIELDS = ("LINKEDIN_COOKIE", "LINKEDIN_USER_AGENT")
_CRUNCHBASE_FIELDS = ("CRUNCHBASE_USER_AGENT",)  # cookies = JSON list, hors scope
_API_KEY_PROVIDERS = ("serper", "hunter", "sirene", "attio", "lemlist")


def _client():
    from oto.tools.ninja import NinjaClient
    return NinjaClient()


def _resolve(name: str) -> tuple[str, str]:
    """Renvoie (group, field) où group ∈ {linkedin, crunchbase, api_key:<provider>}
    et field est le nom de la propriété dans la réponse JSON.
    """
    if name == "LINKEDIN_COOKIE":
        return "linkedin", "cookie"
    if name == "LINKEDIN_USER_AGENT":
        return "linkedin", "user_agent"
    if name == "CRUNCHBASE_USER_AGENT":
        return "crunchbase", "user_agent"
    if name.endswith("_API_KEY"):
        provider = name[: -len("_API_KEY")].lower()
        if provider in _API_KEY_PROVIDERS:
            return f"api_key:{provider}", "key"
    raise typer.BadParameter(
        f"Unknown secret name {name!r}. Supported: "
        f"{', '.join(_LINKEDIN_FIELDS + _CRUNCHBASE_FIELDS)}, "
        f"or <provider>_API_KEY for {_API_KEY_PROVIDERS}"
    )


def _fetch_value(client, group: str, field: str):
    if group == "linkedin":
        data = client.get_linkedin()
    elif group == "crunchbase":
        data = client.get_crunchbase()
    elif group.startswith("api_key:"):
        provider = group.split(":", 1)[1]
        data = client.get_api_key(provider)
    else:
        raise RuntimeError(f"unreachable group {group!r}")
    return data.get(field)


def _handle_error(e) -> None:
    from oto.tools.ninja import NinjaError
    if isinstance(e, NinjaError):
        if e.status == 404:
            detail = e.detail.get("error") if isinstance(e.detail, dict) else e.detail
            print(f"not configured ({detail})", file=sys.stderr)
            raise typer.Exit(1)
        print(f"ninja {e.status}: {e.detail}", file=sys.stderr)
        raise typer.Exit(1)
    raise e


# --- commands ----------------------------------------------------------------

@secrets_app.command("list")
def list_secrets():
    """Liste les secrets configurés côté DB (noms, pas les valeurs)."""
    try:
        me = _client().me()
    except Exception as e:
        _handle_error(e)
    configured = []
    li = me.get("linkedin") or {}
    if li.get("configured"):
        configured.append("LINKEDIN_COOKIE")
        if li.get("user_agent"):
            configured.append("LINKEDIN_USER_AGENT")
    cb = me.get("crunchbase") or {}
    if cb.get("configured"):
        configured.append("CRUNCHBASE_COOKIES")
        if cb.get("user_agent"):
            configured.append("CRUNCHBASE_USER_AGENT")
    providers = me.get("providers") or {}
    for prov in _API_KEY_PROVIDERS:
        p = providers.get(prov) or {}
        if p.get("user_configured"):
            configured.append(f"{prov.upper()}_API_KEY")
    for n in configured:
        print(n)


@secrets_app.command("get")
def get_secret(
    name: str = typer.Argument(..., help="Ex: LINKEDIN_COOKIE, SERPER_API_KEY"),
):
    """Affiche la valeur d'un secret en stdout (pas de newline trailing).

    Composable :  export FOO=$(oto ninja secrets get FOO)
    """
    group, field = _resolve(name)
    try:
        value = _fetch_value(_client(), group, field)
    except Exception as e:
        _handle_error(e)
    if value is None:
        print(f"{name} not configured", file=sys.stderr)
        raise typer.Exit(1)
    sys.stdout.write(value if isinstance(value, str) else json.dumps(value))
    sys.stdout.flush()


@secrets_app.command("set")
def set_secret(
    name: str = typer.Argument(..., help="Ex: LINKEDIN_COOKIE"),
    value: str = typer.Argument(..., help="Nouvelle valeur"),
    user_agent: Optional[str] = typer.Option(
        None, "--user-agent",
        help="(LINKEDIN_COOKIE/CRUNCHBASE) UA à associer au cookie",
    ),
):
    """Pose une valeur côté DB.

    Pour les UA seuls (LINKEDIN_USER_AGENT, CRUNCHBASE_USER_AGENT), un cookie
    doit déjà exister — on conserve le cookie existant en posant le nouvel UA.
    """
    group, field = _resolve(name)
    client = _client()
    try:
        if group == "linkedin":
            if field == "cookie":
                result = client.set_linkedin(value, user_agent=user_agent)
            else:  # user_agent
                current = client.get_linkedin()
                result = client.set_linkedin(current["cookie"], user_agent=value)
        elif group == "crunchbase":
            # field == user_agent only (cookies hors scope)
            current = client.get_crunchbase()
            result = client.set_crunchbase(current["cookies"], user_agent=value)
        elif group.startswith("api_key:"):
            provider = group.split(":", 1)[1]
            result = client.set_api_key(provider, value)
        else:
            raise RuntimeError(f"unreachable group {group!r}")
    except Exception as e:
        _handle_error(e)
    print(json.dumps(result, ensure_ascii=False))


@secrets_app.command("delete")
def delete_secret(
    name: str = typer.Argument(..., help="Ex: LINKEDIN_COOKIE, SERPER_API_KEY"),
):
    """Efface un secret côté DB.

    Pour LinkedIn/Crunchbase : efface cookie + UA ensemble (group-level).
    """
    group, _field = _resolve(name)
    client = _client()
    try:
        if group == "linkedin":
            result = client.delete_linkedin()
        elif group == "crunchbase":
            result = client.delete_crunchbase()
        elif group.startswith("api_key:"):
            provider = group.split(":", 1)[1]
            result = client.delete_api_key(provider)
        else:
            raise RuntimeError(f"unreachable group {group!r}")
    except Exception as e:
        _handle_error(e)
    print(json.dumps(result, ensure_ascii=False))
