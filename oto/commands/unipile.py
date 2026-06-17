"""Unipile commands — hosted LinkedIn (search / scrape / messaging).

La session LinkedIn vit chez Unipile (vrai Chrome + proxy résidentiel FR) :
pas de browser local requis, pas de RL horaire applicatif, et la session de
l'utilisateur n'est ni exposée ni déconnectée (cf. oto-mcp#5).
"""

import json
from typing import Optional

import typer

app = typer.Typer(help="Unipile — hosted LinkedIn (search/scrape/messaging)")


def _out(data):
    print(json.dumps(data, indent=2, ensure_ascii=False))


@app.command("accounts")
def accounts():
    """Comptes connectés sur Unipile (LinkedIn, etc.)."""
    from oto.tools.unipile import UnipileClient
    _out(UnipileClient().list_accounts())


@app.command("facets")
def facets(
    keywords: str = typer.Argument(..., help="Nom à résoudre (ex. 'McDonald\\'s France')"),
    facet_type: str = typer.Option("COMPANY", "--type", "-t", help="COMPANY|LOCATION|INDUSTRY|SCHOOL"),
):
    """Résout un nom en ids de facette LinkedIn (employeur, localisation…).

    La page company LinkedIn n'est pas forcément une facette people-search
    valide — TOUJOURS récupérer l'id ici avant de filtrer une recherche.
    """
    from oto.tools.unipile import UnipileClient
    _out(UnipileClient().resolve_facet(facet_type.upper(), keywords))


@app.command("search")
def search(
    keywords: Optional[str] = typer.Argument(None, help="Mots-clés (nom, intitulé…)"),
    category: str = typer.Option("people", "--category", "-c", help="people|companies"),
    company: Optional[list[str]] = typer.Option(None, "--company", help="Employeur — nom (auto-résolu) ou id de facette. Répétable."),
    location: Optional[list[str]] = typer.Option(None, "--location", "-l", help="Localisation — nom ou id. Répétable."),
    cursor: Optional[str] = typer.Option(None, help="Curseur de pagination"),
):
    """Recherche LinkedIn classic. `--company`/`--location` acceptent des noms
    (résolus automatiquement en facettes) ou des ids numériques."""
    from oto.tools.unipile import UnipileClient
    _out(UnipileClient().search(
        keywords=keywords, category=category,
        company=company, location=location, cursor=cursor,
    ))


@app.command("profile")
def profile(
    identifier: str = typer.Argument(..., help="public identifier ou provider id"),
    sections: str = typer.Option("*", "--sections", "-s", help="Sections LinkedIn ('*' = tout)"),
):
    """Profil complet (carrière datée, écoles, réseau)."""
    from oto.tools.unipile import UnipileClient
    _out(UnipileClient().get_profile(identifier, sections=sections))


@app.command("company")
def company(
    identifier: str = typer.Argument(..., help="public identifier ou id société"),
):
    """Fiche société LinkedIn."""
    from oto.tools.unipile import UnipileClient
    _out(UnipileClient().get_company(identifier))


@app.command("chats")
def chats(
    limit: int = typer.Option(20, "--limit", "-n", help="Nombre de fils"),
    cursor: Optional[str] = typer.Option(None, help="Curseur de pagination"),
):
    """Liste les conversations."""
    from oto.tools.unipile import UnipileClient
    _out(UnipileClient().list_chats(limit=limit, cursor=cursor))


@app.command("messages")
def messages(
    chat_id: str = typer.Argument(..., help="Id du fil"),
    limit: int = typer.Option(50, "--limit", "-n"),
):
    """Messages d'un fil."""
    from oto.tools.unipile import UnipileClient
    _out(UnipileClient().list_messages(chat_id, limit=limit))


@app.command("connect")
def connect(
    notify_url: Optional[str] = typer.Option(None, "--notify", help="Webhook qui recevra l'account_id au succès"),
    name: Optional[str] = typer.Option(None, "--name", help="Identifiant libre rattaché au compte"),
    ttl_minutes: int = typer.Option(60, "--ttl", help="Durée de validité du lien (minutes)"),
):
    """Génère une URL d'auth hébergée Unipile (l'user connecte son LinkedIn)."""
    from oto.tools.unipile import UnipileClient
    url = UnipileClient().hosted_auth_link(
        notify_url=notify_url, name=name, ttl_minutes=ttl_minutes,
    )
    _out({"url": url})


@app.command("send")
def send(
    text: str = typer.Argument(..., help="Texte du message"),
    chat_id: Optional[str] = typer.Option(None, "--chat", help="Répondre dans ce fil"),
    to: Optional[str] = typer.Option(None, "--to", help="provider id du destinataire (nouveau fil)"),
):
    """Envoie un message (--chat pour répondre, --to pour ouvrir un fil)."""
    from oto.tools.unipile import UnipileClient
    _out(UnipileClient().send_message(text, chat_id=chat_id, attendee_id=to))
