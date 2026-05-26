"""INPI/BCE — bilans financiers (ratios Banque de France, open data)."""

import typer
from typing import Optional

app = typer.Typer(help="INPI/BCE financial ratios (open data)")


@app.command("exercises")
def exercises(siren: str = typer.Argument(..., help="SIREN (9 digits)")):
    """List available annual filings for a SIREN."""
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
    """Fetch one annual filing (full ratios) by SIREN + closing date."""
    import json
    from oto.tools.inpi import InpiClient

    client = InpiClient()
    result = client.get_bilan(siren, date)
    if result is None:
        print(json.dumps({"error": "not_found", "siren": siren, "date_cloture": date}, indent=2))
        raise typer.Exit(1)
    print(json.dumps(result, indent=2, ensure_ascii=False))
