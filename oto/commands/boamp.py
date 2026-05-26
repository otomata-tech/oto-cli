"""BOAMP — appels d'offres publics (open data DILA)."""

import typer
from typing import Optional

app = typer.Typer(help="BOAMP public procurement notices (open data)")


@app.command("search")
def search(
    query: Optional[str] = typer.Argument(None, help="Full-text search in objet"),
    descripteur: Optional[str] = typer.Option(None, "--descripteur", "-d", help="Descriptor label (e.g. Photovoltaïque)"),
    departement: Optional[str] = typer.Option(None, "--departement", "--dep", help="Department code"),
    date_from: Optional[str] = typer.Option(None, "--from", help="Start date (YYYY-MM-DD)"),
    date_to: Optional[str] = typer.Option(None, "--to", help="End date (YYYY-MM-DD)"),
    type_marche: Optional[str] = typer.Option(None, "--type", help="Market type (TRAVAUX, FOURNITURES, SERVICES)"),
    limit: int = typer.Option(20, "--limit", "-n"),
):
    """Search BOAMP procurement notices."""
    import json
    from oto.tools.boamp import BoampClient

    client = BoampClient()
    result = client.search(
        query=query, descripteur=descripteur, departement=departement,
        date_from=date_from, date_to=date_to, type_marche=type_marche,
        limit=limit,
    )
    print(json.dumps(result, indent=2, ensure_ascii=False))


@app.command("get")
def get(idweb: str = typer.Argument(..., help="BOAMP notice ID (e.g. 20-12345)")):
    """Fetch a single BOAMP notice by ID."""
    import json
    from oto.tools.boamp import BoampClient

    client = BoampClient()
    result = client.get(idweb)
    if result is None:
        print(json.dumps({"error": "not_found", "idweb": idweb}, indent=2))
        raise typer.Exit(1)
    print(json.dumps(result, indent=2, ensure_ascii=False))
