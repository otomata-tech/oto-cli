"""SIRENE stock — client HTTP vers `mcp.oto.ninja/api/sirene/*`.

Le parquet INSEE complet vit côté serveur, query via DuckDB. Cette classe ne
télécharge plus rien localement — elle fait des appels REST authentifiés.

Auth : token long-lived stocké dans le secret `OTO_API_KEY` (issu depuis
`app.oto.ninja/account` → "tokens cli"). Override URL : `OTO_API_URL`.

Use cases couverts :
- `get_headquarters_addresses(sirens)` — batch enrichissement (1 call HTTP par siren ;
  pour de très gros batches, paralléliser côté caller).
- `get_all_establishments(siren)` — tous les établissements d'une boîte.
- `lookup_siret(siret)` — fetch précis par SIRET.
- `search(...)` — recherche multi-critères (NAF, commune, CP, enseigne, denomination).

Pas de cache local — chaque appel HTTP. Si tu fais > 1000 lookups, considère
batcher côté serveur (à dev si besoin).
"""
from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

import requests

from oto.config import require_secret


_DEFAULT_BASE_URL = "https://mcp.oto.ninja"


class SireneStockError(RuntimeError):
    def __init__(self, status: int, detail: Any):
        self.status = status
        self.detail = detail
        super().__init__(f"sirene_stock {status}: {detail}")


class SireneStock:
    """HTTP client over `/api/sirene/*` exposed by oto-mcp.

    Example:
        stock = SireneStock()
        siege = stock.lookup_siege("443061841")
        ets = stock.get_all_establishments("443061841")
        addresses = stock.get_headquarters_addresses(["443061841", "552032534"])
    """

    def __init__(self, base_url: Optional[str] = None, token: Optional[str] = None):
        self.base_url = (
            base_url
            or os.environ.get("OTO_API_URL")
            or _DEFAULT_BASE_URL
        ).rstrip("/")
        self.token = token or require_secret("OTO_API_KEY")
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
        })

    # --- low-level ------------------------------------------------------------

    def _get(self, path: str, params: Optional[dict] = None) -> Any:
        r = self.session.get(f"{self.base_url}{path}", params=params or {}, timeout=30)
        if r.status_code >= 400:
            try:
                detail = r.json()
            except Exception:
                detail = r.text
            raise SireneStockError(r.status_code, detail)
        return r.json()

    # --- normalisation --------------------------------------------------------

    @staticmethod
    def _normalize(etab: dict) -> dict:
        """Normalise un dict établissement (snake_case INSEE) → forme stable
        pour les consommateurs historiques (street, postal_code, city, status…).
        """
        if not etab:
            return etab
        num = (etab.get("numero_voie") or "").strip()
        type_voie = (etab.get("type_voie") or "").strip()
        voie = (etab.get("libelle_voie") or "").strip()
        street = " ".join(p for p in (num, type_voie, voie) if p) or None
        out = {
            "siren": etab.get("siren"),
            "siret": etab.get("siret"),
            "is_headquarters": bool(etab.get("is_siege")),
            "street": street,
            "postal_code": etab.get("code_postal"),
            "city": etab.get("libelle_commune"),
            "code_commune": etab.get("code_commune"),
            "status": "active" if etab.get("etat") == "A" else "closed",
            "naf": etab.get("naf"),
            "denomination": etab.get("denomination"),
            "enseigne": etab.get("enseigne_1") or etab.get("enseigne_2") or etab.get("enseigne_3"),
            "tranche_effectifs": etab.get("tranche_effectifs"),
            "date_creation": etab.get("date_creation"),
        }
        if etab.get("lambert_x") is not None:
            out["lambert_x"] = float(etab["lambert_x"])
            out["lambert_y"] = float(etab["lambert_y"]) if etab.get("lambert_y") is not None else None
        return out

    # --- high-level (legacy API preservée) -----------------------------------

    def get_headquarters_addresses(self, sirens: List[str]) -> Dict[str, Dict[str, Any]]:
        """Headquarters address for each SIREN. Returns {siren: {street, postal_code, city, status, ...}}.

        Pour les SIRENs introuvables : absents du dict (ni siege ni siret côté serveur).
        """
        out: Dict[str, Dict[str, Any]] = {}
        for siren in sirens:
            siren = str(siren)
            data = self._get("/api/sirene/siege", params={"siren": siren})
            siege = data.get("siege")
            if siege:
                out[siren] = self._normalize(siege)
        return out

    def get_all_establishments(self, siren: str, active_only: bool = True) -> List[Dict[str, Any]]:
        """Tous les établissements d'un SIREN (siège + secondaires)."""
        params = {"siren": str(siren), "active_only": "true" if active_only else "false"}
        data = self._get("/api/sirene/etablissements", params=params)
        return [self._normalize(e) for e in data.get("items", [])]

    # --- nouvelles méthodes ---------------------------------------------------

    def lookup_siege(self, siren: str) -> Optional[Dict[str, Any]]:
        """Siège (headquarters) d'un SIREN, ou None."""
        data = self._get("/api/sirene/siege", params={"siren": str(siren)})
        siege = data.get("siege")
        return self._normalize(siege) if siege else None

    def lookup_siret(self, siret: str) -> Optional[Dict[str, Any]]:
        """Établissement précis par SIRET."""
        data = self._get("/api/sirene/siret", params={"siret": str(siret)})
        etab = data.get("etablissement")
        return self._normalize(etab) if etab else None

    def search(
        self,
        naf: Optional[str] = None,
        code_commune: Optional[str] = None,
        code_postal: Optional[str] = None,
        departement: Optional[str] = None,
        denomination: Optional[str] = None,
        enseigne: Optional[str] = None,
        active_only: bool = True,
        sieges_only: bool = False,
        limit: int = 100,
        offset: int = 0,
    ) -> Dict[str, Any]:
        """Recherche multi-critères côté serveur (DuckDB). Tous filtres AND.

        Returns: {items: [...], count: N, limit: N, offset: N}
        """
        params: dict[str, Any] = {
            "active_only": "true" if active_only else "false",
            "sieges_only": "true" if sieges_only else "false",
            "limit": int(limit),
            "offset": int(offset),
        }
        if naf:
            params["naf"] = naf
        if code_commune:
            params["code_commune"] = code_commune
        if code_postal:
            params["code_postal"] = code_postal
        if departement:
            params["departement"] = departement
        if denomination:
            params["denomination"] = denomination
        if enseigne:
            params["enseigne"] = enseigne
        data = self._get("/api/sirene/search", params=params)
        data["items"] = [self._normalize(e) for e in data.get("items", [])]
        return data

    def info(self) -> Dict[str, Any]:
        """Métadonnées du parquet côté serveur (size, mtime, total_rows)."""
        return self._get("/api/sirene/info")
