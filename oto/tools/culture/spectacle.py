"""Licences entrepreneurs de spectacles vivants (LES).

Source: data.culture.gouv.fr — dataset `declarations-des-entrepreneurs-de-spectacles-vivants`.
~110k récépissés depuis 2020, dont ~63k valides à l'instant T (renewed every 5 years).

Fields (cf. /api/explore/v2.1/catalog/datasets/.../records):
  numero_recepisse, date_validite, date_depot_dossier, statut_recepisse,
  categorie (1/2/3), type_declaration, type_declarant, raison_sociale,
  code_postal_siret, siren_siret (9 or 14 chars), nom_lieu, code_postal_lieu,
  code_naf_ape, geoloc_cp_siret (lat/lon), region_siret, departement_siret,
  date_expire_licence, date_retrait_licence.

Gotchas (vérifiés en live):
- statut_recepisse case-sensitive : "Valide", pas "valide".
- code_naf_ape non-normalisé : "90.01Z" coexiste avec "90.01Z - Arts du spectacle vivant"
  et "8411Z" sans point. → ce module normalise les filtres NAF en `like "<5chars>%"`.
- siren_siret polymorphe : SIRET 14 chars (personne morale) ou SIREN 9 chars
  (personne physique). Slicer [:9] avant pivot vers Recherche Entreprises.
- date_validite est la date d'effet (depot + 30j), pas l'expiration à 5 ans.
"""

from typing import Any, Iterable, Optional

from .opendatasoft import OpendatasoftClient


PORTAL = "https://data.culture.gouv.fr"
DATASET = "declarations-des-entrepreneurs-de-spectacles-vivants"

STATUS_VALUES = {"Valide", "Invalide", "Expiré", "Invalidé", "En instruction"}
CATEGORIES = {"1", "2", "3"}


def _quote(v: str) -> str:
    return '"' + v.replace('"', '\\"') + '"'


def _naf_clause(naf: str) -> str:
    """Build a NAF clause that handles the non-normalized field (dot optional,
    label suffix optional)."""
    core = naf.strip().upper().replace(".", "")  # "90.01Z" → "9001Z"
    # Match both "9001Z..." and "90.01Z..." prefixes.
    dotted = core[:2] + "." + core[2:] if len(core) >= 3 else core
    return f'(code_naf_ape like {_quote(core + "%")} OR code_naf_ape like {_quote(dotted + "%")})'


class SpectacleClient:
    """LES (Licences entrepreneurs spectacles vivants) — composable filters."""

    def __init__(self, client: Optional[OpendatasoftClient] = None):
        self.client = client or OpendatasoftClient(PORTAL)

    def _build_where(
        self,
        *,
        status: Optional[str] = None,
        categorie: Optional[str] = None,
        naf: Optional[str] = None,
        region: Optional[str] = None,
        departement: Optional[str] = None,
        code_postal: Optional[str] = None,
        siren: Optional[str] = None,
        type_declarant_like: Optional[str] = None,
        deposited_since: Optional[str] = None,
        raw_where: Optional[str] = None,
    ) -> Optional[str]:
        clauses: list[str] = []
        if status:
            if status not in STATUS_VALUES:
                raise ValueError(f"status must be one of {sorted(STATUS_VALUES)}, got {status!r}")
            clauses.append(f"statut_recepisse={_quote(status)}")
        if categorie:
            if str(categorie) not in CATEGORIES:
                raise ValueError(f"categorie must be one of {sorted(CATEGORIES)}, got {categorie!r}")
            clauses.append(f"categorie={_quote(str(categorie))}")
        if naf:
            clauses.append(_naf_clause(naf))
        if region:
            clauses.append(f"region_siret={_quote(region)}")
        if departement:
            clauses.append(f"departement_siret={_quote(departement)}")
        if code_postal:
            clauses.append(f"code_postal_siret={_quote(code_postal)}")
        if siren:
            # Match both SIRET (14) starting with this SIREN and bare SIREN.
            clauses.append(f"siren_siret like {_quote(siren + '%')}")
        if type_declarant_like:
            clauses.append(f"type_declarant like {_quote('%' + type_declarant_like + '%')}")
        if deposited_since:
            clauses.append(f"date_depot_dossier>={_quote(deposited_since)}")
        if raw_where:
            clauses.append(f"({raw_where})")
        return " AND ".join(clauses) if clauses else None

    def search(
        self,
        *,
        status: Optional[str] = "Valide",
        categorie: Optional[str] = None,
        naf: Optional[str] = None,
        region: Optional[str] = None,
        departement: Optional[str] = None,
        code_postal: Optional[str] = None,
        siren: Optional[str] = None,
        type_declarant_like: Optional[str] = None,
        deposited_since: Optional[str] = None,
        raw_where: Optional[str] = None,
        order_by: str = "date_depot_dossier desc",
        limit: int = 20,
        offset: int = 0,
    ) -> dict[str, Any]:
        """Composed AND filter on LES. Defaults to status=Valide."""
        where = self._build_where(
            status=status, categorie=categorie, naf=naf, region=region,
            departement=departement, code_postal=code_postal, siren=siren,
            type_declarant_like=type_declarant_like, deposited_since=deposited_since,
            raw_where=raw_where,
        )
        return self.client.records(
            DATASET, where=where, order_by=order_by, limit=limit, offset=offset,
        )

    def get(self, siren: str) -> dict[str, Any]:
        """Fetch all récépissés for a SIREN/SIRET (a structure may have L1+L2+L3)."""
        where = self._build_where(siren=siren, status=None)
        return self.client.records(DATASET, where=where, limit=100)

    def iter_search(
        self,
        *,
        page_size: int = 100,
        max_total: Optional[int] = None,
        **filters,
    ) -> Iterable[dict[str, Any]]:
        """Paginate `search` results. Same kwargs minus limit/offset."""
        where = self._build_where(**{k: v for k, v in filters.items() if k != "order_by"})
        order_by = filters.get("order_by", "date_depot_dossier desc")
        yield from self.client.iter_records(
            DATASET, where=where, order_by=order_by,
            page_size=page_size, max_total=max_total,
        )

    def stats(
        self,
        group_by: str,
        *,
        where_filters: Optional[dict] = None,
        limit: int = 20,
    ) -> dict[str, Any]:
        """Group-by aggregation (the gap of the official datagouv MCP).

        Args:
            group_by: Field to group on (e.g. "code_naf_ape", "region_siret",
                "categorie", "departement_siret").
            where_filters: Optional dict passed to `_build_where` to scope.
            limit: Number of buckets to return.
        """
        where = self._build_where(**(where_filters or {}))
        return self.client.records(
            DATASET, where=where, group_by=group_by,
            select=f"{group_by}, count(*) as n",
            order_by="count(*) desc",
            limit=limit,
        )

    def export_url(self, fmt: str = "csv", **filters) -> str:
        """Direct export URL — caller streams it (~6 MB CSV for full valid set)."""
        where = self._build_where(**filters)
        return self.client.export_url(DATASET, fmt, where=where)
