"""Culture (Ministère de la Culture open data) commands.

Sub-namespaces by dataset:
- spectacle: Licences entrepreneurs de spectacles vivants (LES)

Future: festivals, cnc, adsv, …
"""

import json
import typer
from typing import Optional

app = typer.Typer(help="French Ministry of Culture open data (data.culture.gouv.fr)")

# spectacle sub-namespace
spectacle_app = typer.Typer(help="Licences entrepreneurs de spectacles vivants (LES)")
app.add_typer(spectacle_app, name="spectacle")


def _print(obj):
    print(json.dumps(obj, indent=2, ensure_ascii=False, default=str))


@spectacle_app.command("search")
def spectacle_search(
    status: str = typer.Option("Valide", "--status", help="Valide|Invalide|Expiré|Invalidé|En instruction (case-sensitive)"),
    categorie: Optional[str] = typer.Option(None, "--categorie", "-c", help="1 (lieu), 2 (producteur), 3 (diffuseur)"),
    naf: Optional[str] = typer.Option(None, "--naf", help="NAF prefix (e.g. 90.01Z or 9001Z) — handles unnormalized field"),
    region: Optional[str] = typer.Option(None, "--region", help="Région SIRET (e.g. 'Île-de-France')"),
    dept: Optional[str] = typer.Option(None, "--dept", help="Département SIRET (e.g. 'Paris', 'Bouches-du-Rhône')"),
    cp: Optional[str] = typer.Option(None, "--cp", help="Code postal SIRET"),
    declarant: Optional[str] = typer.Option(None, "--declarant", help="Substring match on type_declarant (e.g. 'privé', 'association', 'public')"),
    since: Optional[str] = typer.Option(None, "--since", help="Filed since YYYY-MM-DD"),
    raw_where: Optional[str] = typer.Option(None, "--where", help="Raw Opendatasoft where clause (advanced)"),
    order: str = typer.Option("date_depot_dossier desc", "--order", help="order_by clause"),
    limit: int = typer.Option(20, "--limit", "-n", help="Max results (1-100 per page)"),
    offset: int = typer.Option(0, "--offset", help="Pagination offset"),
):
    """Search LES with composed AND filters (statut + catégorie + NAF + région…)."""
    from oto.tools.culture import SpectacleClient
    client = SpectacleClient()
    _print(client.search(
        status=status, categorie=categorie, naf=naf, region=region,
        departement=dept, code_postal=cp, type_declarant_like=declarant,
        deposited_since=since, raw_where=raw_where, order_by=order,
        limit=limit, offset=offset,
    ))


@spectacle_app.command("get")
def spectacle_get(
    siren: str = typer.Argument(..., help="SIREN (9) or SIRET (14) — returns all récépissés for that entity"),
):
    """Fetch all récépissés (L1/L2/L3) for a SIREN/SIRET."""
    from oto.tools.culture import SpectacleClient
    client = SpectacleClient()
    _print(client.get(siren))


@spectacle_app.command("stats")
def spectacle_stats(
    by: str = typer.Argument(..., help="Field to group on: code_naf_ape|region_siret|departement_siret|categorie|type_declarant"),
    status: str = typer.Option("Valide", "--status"),
    categorie: Optional[str] = typer.Option(None, "--categorie", "-c"),
    naf: Optional[str] = typer.Option(None, "--naf"),
    region: Optional[str] = typer.Option(None, "--region"),
    dept: Optional[str] = typer.Option(None, "--dept"),
    limit: int = typer.Option(20, "--limit", "-n"),
):
    """Group-by aggregate (fills the gap of the official datagouv MCP)."""
    from oto.tools.culture import SpectacleClient
    client = SpectacleClient()
    _print(client.stats(
        by,
        where_filters={
            "status": status, "categorie": categorie, "naf": naf,
            "region": region, "departement": dept,
        },
        limit=limit,
    ))


@spectacle_app.command("export-url")
def spectacle_export_url(
    fmt: str = typer.Option("csv", "--format", "-f", help="csv|json|parquet|xlsx"),
    status: Optional[str] = typer.Option("Valide", "--status"),
    categorie: Optional[str] = typer.Option(None, "--categorie", "-c"),
    naf: Optional[str] = typer.Option(None, "--naf"),
    region: Optional[str] = typer.Option(None, "--region"),
    dept: Optional[str] = typer.Option(None, "--dept"),
):
    """Build a direct export URL — caller streams it (~6 MB CSV for full valid set)."""
    from oto.tools.culture import SpectacleClient
    client = SpectacleClient()
    print(client.export_url(
        fmt=fmt, status=status, categorie=categorie, naf=naf,
        region=region, departement=dept,
    ))
