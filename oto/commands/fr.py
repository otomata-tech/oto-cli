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




# --- SIRENE stock (HTTP client vers mcp.oto.ninja) ---

stock_app = typer.Typer(help="SIRENE stock — DuckDB côté serveur, accessed via mcp.oto.ninja")
app.add_typer(stock_app, name="stock")


@stock_app.command("info")
def stock_info():
    """Server-side parquet metadata (size, mtime, total rows)."""
    import json
    from oto.tools.sirene import SireneStock

    print(json.dumps(SireneStock().info(), indent=2, ensure_ascii=False))


@stock_app.command("addresses")
def stock_addresses(sirens: str = typer.Argument(..., help="SIREN numbers (comma-separated)")):
    """Get headquarters addresses for a batch of SIRENs (1 HTTP call per SIREN)."""
    import json
    from oto.tools.sirene import SireneStock

    siren_list = [s.strip() for s in sirens.split(",")]
    addresses = SireneStock().get_headquarters_addresses(siren_list)
    print(json.dumps(addresses, indent=2, ensure_ascii=False))


@stock_app.command("etablissements")
def stock_etablissements(
    siren: str = typer.Argument(..., help="SIREN (9 digits)"),
    all_states: bool = typer.Option(False, "--all", help="Inclure les fermés"),
):
    """List all establishments of a SIREN (siège + secondaires)."""
    import json
    from oto.tools.sirene import SireneStock

    items = SireneStock().get_all_establishments(siren, active_only=not all_states)
    print(json.dumps(items, indent=2, ensure_ascii=False))


@stock_app.command("search")
def stock_search(
    naf: Optional[str] = typer.Option(None, "--naf"),
    code_commune: Optional[str] = typer.Option(None, "--commune", help="Code INSEE COG"),
    code_postal: Optional[str] = typer.Option(None, "--cp"),
    departement: Optional[str] = typer.Option(None, "--dept", help="Préfixe code postal (ex. 26, 971)"),
    denomination: Optional[str] = typer.Option(None, "--denomination"),
    enseigne: Optional[str] = typer.Option(None, "--enseigne"),
    sieges_only: bool = typer.Option(False, "--sieges-only"),
    all_states: bool = typer.Option(False, "--all"),
    limit: int = typer.Option(100, "--limit", "-n"),
    offset: int = typer.Option(0, "--offset"),
):
    """Multi-criteria search over the SIRENE stock parquet."""
    import json
    from oto.tools.sirene import SireneStock

    res = SireneStock().search(
        naf=naf, code_commune=code_commune, code_postal=code_postal,
        departement=departement, denomination=denomination, enseigne=enseigne,
        active_only=not all_states, sieges_only=sieges_only,
        limit=limit, offset=offset,
    )
    print(json.dumps(res, indent=2, ensure_ascii=False))


# --- accords d'entreprise (index ACCO) ---------------------------------------
# Repli documenté quand le connecteur MCP est indisponible : l'index vit côté
# service FOD (réseau privé), on passe donc par l'API d'oto-mcp (token OTO_API_KEY).
accords_app = typer.Typer(help="Accords d'entreprise (index ACCO), via l'API oto")
app.add_typer(accords_app, name="accords")


@accords_app.command("search")
def accords_search(
    query: Optional[str] = typer.Option(None, "--query", "-q", help="Mots du titre"),
    idcc: Optional[str] = typer.Option(None, "--idcc", help="Convention collective (0573 ou 573)"),
    themes: Optional[str] = typer.Option(None, "--themes", help="Codes thème séparés par des virgules (ex. 111,112)"),
    nature: Optional[str] = typer.Option(None, "--nature", help="ACCORD | AVENANT | …"),
    siren: Optional[str] = typer.Option(None, "--siren"),
    departement: Optional[str] = typer.Option(None, "--dept", help="Préfixe code postal (2 chiffres)"),
    date_from: Optional[str] = typer.Option(None, "--from", help="AAAA-MM-JJ"),
    date_to: Optional[str] = typer.Option(None, "--to", help="AAAA-MM-JJ"),
    latest_per_siret: bool = typer.Option(False, "--latest", help="Un seul accord (le plus récent) par établissement"),
    limit: int = typer.Option(20, "--limit", "-n"),
    offset: int = typer.Option(0, "--offset"),
):
    """Chercher des accords d'entreprise (mêmes filtres que fr_accords_search)."""
    import json
    from oto.tools.accords import AccordsClient

    res = AccordsClient().search(
        query=query, idcc=idcc,
        themes=[t.strip() for t in themes.split(",")] if themes else None,
        nature=nature, siren=siren, departement=departement,
        date_from=date_from, date_to=date_to, latest_per_siret=latest_per_siret,
        limit=limit, offset=offset,
    )
    print(json.dumps(res, indent=2, ensure_ascii=False))


@accords_app.command("get")
def accords_get(id_or_numero: str = typer.Argument(..., help="id DILA (ACCOTEXT000…) ou numéro de dépôt (T…)")):
    """Un accord et ses métadonnées."""
    import json
    from oto.tools.accords import AccordsClient

    print(json.dumps(AccordsClient().get(id_or_numero), indent=2, ensure_ascii=False))


@accords_app.command("themes")
def accords_themes():
    """Nomenclature des thèmes (code + libellé), pour composer --themes."""
    import json
    from oto.tools.accords import AccordsClient

    print(json.dumps(AccordsClient().themes(), indent=2, ensure_ascii=False))


@accords_app.command("sirens")
def accords_sirens(
    idccs: str = typer.Argument(..., help="Codes IDCC séparés par des virgules (ex. 1596,1597,2609)"),
    themes: Optional[str] = typer.Option(None, "--themes", help="Codes thème séparés par des virgules"),
    departement: Optional[str] = typer.Option(None, "--dept"),
    limit_per_idcc: int = typer.Option(1000, "--limit-per-idcc"),
):
    """SIREN distincts couverts par PLUSIEURS conventions (dédup incluse).

    L'API n'accepte qu'un IDCC par requête alors qu'une entreprise en porte souvent
    trois ou quatre — cette commande boucle et déduplique à ta place.
    """
    import json
    from oto.tools.accords import AccordsClient

    extra = {}
    if themes:
        extra["themes"] = [t.strip() for t in themes.split(",")]
    if departement:
        extra["departement"] = departement
    sirens = AccordsClient().sirens_by_idcc(
        [c.strip() for c in idccs.split(",") if c.strip()],
        limit_per_idcc=limit_per_idcc, **extra,
    )
    print(json.dumps({"count": len(sirens), "sirens": sirens}, indent=2))
