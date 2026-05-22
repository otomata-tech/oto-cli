"""SIRENE commands (French company data from INSEE)."""

import typer
from typing import Optional

app = typer.Typer(help="French company data (INSEE SIRENE, API Entreprises)")

# Stock subcommands
stock_app = typer.Typer(help="SIRENE stock file for batch operations (~2GB local file)")
app.add_typer(stock_app, name="stock")


@app.command("search")
def search(
    query: Optional[str] = typer.Argument(None, help="Company name to search"),
    naf: Optional[str] = typer.Option(None, "--naf", help="NAF codes (comma-separated)"),
    employees: Optional[str] = typer.Option(None, "--employees", help="Employee ranges (e.g. 11,12)"),
    dept: Optional[str] = typer.Option(None, "--dept", help="Department code for SIRET search"),
    postal: Optional[str] = typer.Option(None, "--postal", help="Postal code for SIRET search"),
    city: Optional[str] = typer.Option(None, "--city", help="City name for SIRET search"),
    limit: int = typer.Option(20, "--limit", "-n", help="Max results"),
):
    """Search French companies in INSEE SIRENE database."""
    import json
    from oto.tools.sirene import SireneClient

    client = SireneClient()
    naf_list = naf.split(",") if naf else None
    emp_list = employees.split(",") if employees else None

    if query or dept or postal or city:
        results = client.search_siret(
            name=query,
            naf=naf_list,
            employees=emp_list,
            postal_code=postal,
            city=city,
            headquarters_only=True,
            limit=limit,
        )
        companies = results.get("etablissements", [])
        print(json.dumps({
            "total": results.get("header", {}).get("total", len(companies)),
            "count": len(companies),
            "etablissements": companies,
        }, indent=2, ensure_ascii=False))
    else:
        results = client.search(
            naf=naf_list,
            employees=emp_list,
            limit=limit,
        )
        companies = results.get("unitesLegales", [])
        print(json.dumps({
            "total": results.get("header", {}).get("total", len(companies)),
            "count": len(companies),
            "unitesLegales": companies,
        }, indent=2, ensure_ascii=False))


@app.command("get")
def get(
    siren: str = typer.Argument(..., help="SIREN number (9 digits)"),
):
    """Get company details by SIREN."""
    import json
    from oto.tools.sirene import SireneClient

    client = SireneClient()
    company = client.get_by_siren(siren)
    print(json.dumps(company, indent=2, ensure_ascii=False))


@app.command("siret")
def siret(
    siret: str = typer.Argument(..., help="SIRET number (14 digits)"),
):
    """Get establishment details by SIRET."""
    import json
    from oto.tools.sirene import SireneClient

    client = SireneClient()
    establishment = client.get_siret(siret)
    print(json.dumps(establishment, indent=2, ensure_ascii=False))


@app.command("headquarters")
def headquarters(
    siren: str = typer.Argument(..., help="SIREN number (9 digits)"),
):
    """Get company headquarters with address."""
    import json
    from oto.tools.sirene import SireneClient

    client = SireneClient()
    hq = client.get_headquarters(siren)
    if hq:
        print(json.dumps(hq, indent=2, ensure_ascii=False))
    else:
        print("Headquarters not found")
        raise typer.Exit(1)


@app.command("suggest-naf")
def suggest_naf(
    description: str = typer.Argument(..., help="Activity description in French"),
    limit: int = typer.Option(3, "--limit", "-n", help="Max suggestions"),
):
    """Suggest NAF codes from activity description using AI."""
    import json
    from oto.tools.naf import NAFSuggester

    suggester = NAFSuggester()
    suggestions = suggester.suggest(description, limit=limit)

    result = [{
        "code": s.code,
        "label": s.label,
        "confidence": s.confidence,
        "reason": s.reason,
    } for s in suggestions]

    print(json.dumps({"suggestions": result}, indent=2, ensure_ascii=False))


@app.command("entreprises")
def entreprises(
    query: Optional[str] = typer.Argument(None, help="Search query"),
    naf: Optional[str] = typer.Option(None, "--naf", help="NAF codes (comma-separated)"),
    dept: Optional[str] = typer.Option(None, "--dept", help="Department code"),
    ca_min: Optional[int] = typer.Option(None, "--ca-min", help="Min turnover"),
    ca_max: Optional[int] = typer.Option(None, "--ca-max", help="Max turnover"),
    idcc: Optional[str] = typer.Option(None, "--idcc", help="IDCC codes / conventions collectives (comma-separated, e.g. 1285,3090)"),
    limit: int = typer.Option(25, "--limit", "-n", help="Max results"),
):
    """Search companies with enriched data (directors, finances) via API Entreprises."""
    import json
    from oto.tools.sirene import EntreprisesClient

    client = EntreprisesClient()
    naf_list = naf.split(",") if naf else None
    idcc_list = idcc.split(",") if idcc else None

    results = client.search(
        query=query,
        naf=naf_list,
        departement=dept,
        ca_min=ca_min,
        ca_max=ca_max,
        idcc=idcc_list,
        per_page=limit,
    )
    print(json.dumps(results, indent=2, ensure_ascii=False))


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
def stock_download(
    force: bool = typer.Option(False, "--force", "-f", help="Re-download even if exists"),
):
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
def stock_addresses(
    sirens: str = typer.Argument(..., help="SIREN numbers (comma-separated)"),
):
    """Get headquarters addresses from stock file (batch mode)."""
    import json
    from oto.tools.sirene import SireneStock

    stock = SireneStock()
    siren_list = [s.strip() for s in sirens.split(",")]
    addresses = stock.get_headquarters_addresses(siren_list)
    print(json.dumps(addresses, indent=2, ensure_ascii=False))
