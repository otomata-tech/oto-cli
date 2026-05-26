"""Données entreprise France — identité, finances, événements légaux, appels d'offres."""

import typer
from typing import Optional

app = typer.Typer(help="French company data (identity, finances, legal events, tenders)")


@app.command("search")
def search(
    query: Optional[str] = typer.Argument(None, help="Company name, SIREN, brand…"),
    naf: Optional[str] = typer.Option(None, "--naf", help="NAF codes, comma-separated"),
    dept: Optional[str] = typer.Option(None, "--dept", help="Department code"),
    postal: Optional[str] = typer.Option(None, "--postal", help="Postal code"),
    commune: Optional[str] = typer.Option(None, "--commune", help="City name"),
    employees: Optional[str] = typer.Option(None, "--employees", help="Employee range codes"),
    ca_min: Optional[int] = typer.Option(None, "--ca-min", help="Min turnover (EUR)"),
    ca_max: Optional[int] = typer.Option(None, "--ca-max", help="Max turnover (EUR)"),
    idcc: Optional[str] = typer.Option(None, "--idcc", help="IDCC codes, comma-separated"),
    limit: int = typer.Option(25, "--limit", "-n"),
):
    """Search French companies (API Recherche Entreprises)."""
    import json
    from oto.tools.sirene import EntreprisesClient

    client = EntreprisesClient()
    result = client.search(
        query=query,
        naf=[s.strip() for s in naf.split(",")] if naf else None,
        departement=dept,
        code_postal=postal,
        commune=commune,
        employees=[s.strip() for s in employees.split(",")] if employees else None,
        ca_min=ca_min, ca_max=ca_max,
        idcc=[s.strip() for s in idcc.split(",")] if idcc else None,
        per_page=limit,
    )
    print(json.dumps(result, indent=2, ensure_ascii=False))


@app.command("get")
def get(siren: str = typer.Argument(..., help="SIREN (9 digits)")):
    """Get company identity (siège, dirigeants, finances, établissements)."""
    import json
    from oto.tools.sirene import EntreprisesClient

    client = EntreprisesClient()
    result = client.get_by_siren(siren)
    if not result:
        print(json.dumps({"error": "not_found", "siren": siren}))
        raise typer.Exit(1)
    print(json.dumps(result, indent=2, ensure_ascii=False))


@app.command("directors")
def directors(siren: str = typer.Argument(..., help="SIREN (9 digits)")):
    """List company directors."""
    import json
    from oto.tools.sirene import EntreprisesClient

    client = EntreprisesClient()
    result = client.get_directors(siren)
    print(json.dumps(result, indent=2, ensure_ascii=False))


@app.command("siret")
def siret(siret_num: str = typer.Argument(..., help="SIRET (14 digits)")):
    """Get establishment details by SIRET (INSEE SIRENE)."""
    import json
    from oto.tools.sirene import SireneClient

    client = SireneClient()
    result = client.get_siret(siret_num)
    print(json.dumps(result, indent=2, ensure_ascii=False))


@app.command("headquarters")
def headquarters(siren: str = typer.Argument(..., help="SIREN (9 digits)")):
    """Get company headquarters with address (INSEE SIRENE)."""
    import json
    from oto.tools.sirene import SireneClient

    client = SireneClient()
    result = client.get_headquarters(siren)
    if not result:
        print(json.dumps({"error": "not_found", "siren": siren}))
        raise typer.Exit(1)
    print(json.dumps(result, indent=2, ensure_ascii=False))


@app.command("suggest-naf")
def suggest_naf(
    description: str = typer.Argument(..., help="Activity description in French"),
    limit: int = typer.Option(3, "--limit", "-n"),
):
    """Suggest NAF codes from activity description using AI."""
    import json
    from oto.tools.naf import NAFSuggester

    suggester = NAFSuggester()
    suggestions = suggester.suggest(description, limit=limit)
    result = [{"code": s.code, "label": s.label, "confidence": s.confidence, "reason": s.reason} for s in suggestions]
    print(json.dumps({"suggestions": result}, indent=2, ensure_ascii=False))


@app.command("bilans")
def bilans(siren: str = typer.Argument(..., help="SIREN (9 digits)")):
    """List available INPI/BCE annual filings for a SIREN."""
    import json
    from oto.tools.inpi import InpiClient

    client = InpiClient()
    items = client.list_exercises(siren)
    print(json.dumps({"siren": siren, "items": items, "total": len(items)}, indent=2, ensure_ascii=False))


@app.command("bilan")
def bilan(
    siren: str = typer.Argument(..., help="SIREN (9 digits)"),
    date: str = typer.Argument(..., help="Closing date (YYYY-MM-DD)"),
):
    """Fetch one INPI/BCE annual filing with full financial ratios."""
    import json
    from oto.tools.inpi import InpiClient

    client = InpiClient()
    result = client.get_bilan(siren, date)
    if result is None:
        print(json.dumps({"error": "not_found", "siren": siren, "date_cloture": date}))
        raise typer.Exit(1)
    print(json.dumps(result, indent=2, ensure_ascii=False))


@app.command("events")
def events(
    siren: str = typer.Argument(..., help="SIREN (9 digits)"),
    famille: Optional[str] = typer.Option(None, "--famille", "-f",
        help="Filter: creation, modification, radiation, vente, procedure_collective, dpc"),
    limit: int = typer.Option(20, "--limit", "-n"),
):
    """List BODACC legal events for a SIREN (creations, modifications, proceedings)."""
    import json
    from oto.tools.bodacc import BodaccClient

    client = BodaccClient()
    result = client.search_by_siren(siren, famille=famille, limit=limit)
    print(json.dumps(result, indent=2, ensure_ascii=False))


@app.command("tenders")
def tenders(
    query: Optional[str] = typer.Argument(None, help="Full-text search"),
    descripteur: Optional[str] = typer.Option(None, "--descripteur", "-d", help="Descriptor label"),
    dept: Optional[str] = typer.Option(None, "--dept", help="Department code"),
    date_from: Optional[str] = typer.Option(None, "--from", help="Start date (YYYY-MM-DD)"),
    date_to: Optional[str] = typer.Option(None, "--to", help="End date (YYYY-MM-DD)"),
    type_marche: Optional[str] = typer.Option(None, "--type", help="TRAVAUX, FOURNITURES, SERVICES"),
    limit: int = typer.Option(20, "--limit", "-n"),
):
    """Search BOAMP public procurement tenders."""
    import json
    from oto.tools.boamp import BoampClient

    client = BoampClient()
    result = client.search(
        query=query, descripteur=descripteur, departement=dept,
        date_from=date_from, date_to=date_to, type_marche=type_marche,
        limit=limit,
    )
    print(json.dumps(result, indent=2, ensure_ascii=False))


@app.command("profile")
def profile(siren: str = typer.Argument(..., help="SIREN (9 digits)")):
    """Full company profile: identity + latest financials + recent legal events."""
    import json
    from concurrent.futures import ThreadPoolExecutor
    from oto.tools.sirene import EntreprisesClient
    from oto.tools.inpi import InpiClient
    from oto.tools.bodacc import BodaccClient

    entreprises = EntreprisesClient()
    inpi = InpiClient()
    bodacc = BodaccClient()

    with ThreadPoolExecutor(max_workers=3) as pool:
        f_identity = pool.submit(entreprises.get_by_siren, siren)
        f_bilans = pool.submit(inpi.list_exercises, siren)
        f_events = pool.submit(bodacc.search_by_siren, siren, None, 10)

    identity = f_identity.result()
    if not identity:
        print(json.dumps({"error": "not_found", "siren": siren}))
        raise typer.Exit(1)

    exercises = f_bilans.result()
    latest_bilan = None
    if exercises:
        latest_bilan = inpi.get_bilan(siren, exercises[0]["date_cloture_exercice"])

    events_data = f_events.result()

    result = {
        "siren": siren,
        "identity": identity,
        "latest_bilan": latest_bilan,
        "recent_events": events_data.get("results", []),
        "events_total": events_data.get("total_count", 0),
    }
    print(json.dumps(result, indent=2, ensure_ascii=False))


# --- SIRENE stock (batch) ---

stock_app = typer.Typer(help="SIRENE stock file for batch operations (~2GB local file)")
app.add_typer(stock_app, name="stock")


@stock_app.command("status")
def stock_status():
    """Show stock file status."""
    from oto.tools.sirene import SireneStock

    stock = SireneStock()
    print(f"Path: {stock.stock_file}")
    print(f"Available: {'Yes' if stock.is_available else 'No'}")
    if stock.is_available:
        print(f"Size: {stock.file_size_gb:.2f} GB")
        age = stock.file_age_days
        if age:
            print(f"Age: {age:.0f} days")
    if stock.is_downloading:
        print("Status: Downloading...")


@stock_app.command("download")
def stock_download(force: bool = typer.Option(False, "--force", "-f")):
    """Download SIRENE stock file (~2GB from data.gouv.fr)."""
    from oto.tools.sirene import SireneStock

    stock = SireneStock()
    if stock.is_available and not force:
        print(f"Stock file already exists: {stock.stock_file}")
        print(f"Size: {stock.file_size_gb:.2f} GB, Age: {stock.file_age_days:.0f} days")
        print("Use --force to re-download")
        return
    stock.download(force=force)


@stock_app.command("addresses")
def stock_addresses(sirens: str = typer.Argument(..., help="SIREN numbers (comma-separated)")):
    """Get headquarters addresses from stock file (batch mode)."""
    import json
    from oto.tools.sirene import SireneStock

    stock = SireneStock()
    siren_list = [s.strip() for s in sirens.split(",")]
    addresses = stock.get_headquarters_addresses(siren_list)
    print(json.dumps(addresses, indent=2, ensure_ascii=False))
