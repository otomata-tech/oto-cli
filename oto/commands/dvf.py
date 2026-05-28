"""DVF — transactions immobilières (open data Etalab geo-dvf)."""
import json

import typer
from typing import Optional

app = typer.Typer(help="DVF — valeurs foncières (immobilier) par commune, open data")


@app.command("comparables")
def comparables(
    code_commune: str = typer.Argument(..., help="Code INSEE commune (5 chiffres)"),
    type_local: Optional[str] = typer.Option(None, "--type", help="Appartement | Maison"),
    surface_min: Optional[float] = typer.Option(None, "--surface-min"),
    surface_max: Optional[float] = typer.Option(None, "--surface-max"),
    years: int = typer.Option(2, "--years", "-y"),
    limit: int = typer.Option(50, "--limit", "-n"),
):
    """Transactions comparables (mono-bien bâti) avec €/m²."""
    from oto.tools.dvf import DvfClient

    res = DvfClient().comparables(
        code_commune=code_commune, type_local=type_local,
        surface_min=surface_min, surface_max=surface_max,
        years=years, limit=limit,
    )
    print(json.dumps(res, indent=2, ensure_ascii=False))


@app.command("address")
def address(
    adresse: str = typer.Argument(..., help="Adresse libre (géocodée via BAN)"),
    radius: int = typer.Option(500, "--radius", "-r", help="Rayon mètres"),
    type_local: Optional[str] = typer.Option(None, "--type", help="Appartement | Maison"),
    surface_min: Optional[float] = typer.Option(None, "--surface-min"),
    surface_max: Optional[float] = typer.Option(None, "--surface-max"),
    years: int = typer.Option(3, "--years", "-y"),
    limit: int = typer.Option(50, "--limit", "-n"),
):
    """Comparables autour d'une adresse précise (géocode + rayon)."""
    from oto.tools.dvf import DvfClient

    res = DvfClient().comparables_by_address(
        adresse=adresse, radius_m=radius, type_local=type_local,
        surface_min=surface_min, surface_max=surface_max, years=years, limit=limit,
    )
    print(json.dumps(res, indent=2, ensure_ascii=False))


@app.command("stats")
def stats(
    code_commune: str = typer.Argument(..., help="Code INSEE commune (5 chiffres)"),
    type_local: Optional[str] = typer.Option(None, "--type", help="Appartement | Maison"),
    years: int = typer.Option(3, "--years", "-y"),
):
    """Stats €/m² d'une commune (médiane, moyenne, ventilation annuelle)."""
    from oto.tools.dvf import DvfClient

    res = DvfClient().stats(code_commune=code_commune, type_local=type_local, years=years)
    print(json.dumps(res, indent=2, ensure_ascii=False))
