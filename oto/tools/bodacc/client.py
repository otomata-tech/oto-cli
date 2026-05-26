"""BODACC — publications légales des entreprises françaises (open data DILA).

Dataset: annonces-commerciales on OpenDataSoft v2.1.
No auth required. Licence Ouverte / Etalab 2.0.
"""
from __future__ import annotations

from typing import Any, Optional

import requests


class BodaccClient:
    BASE_URL = "https://bodacc-datadila.opendatasoft.com/api/explore/v2.1/catalog/datasets/annonces-commerciales/records"

    def search_by_siren(
        self,
        siren: str,
        famille: Optional[str] = None,
        limit: int = 20,
    ) -> dict[str, Any]:
        """Search BODACC announcements for a SIREN.

        Args:
            siren: 9-digit SIREN.
            famille: Filter by family (creation, modification, radiation,
                     vente, procedure_collective, dpc).
            limit: Max results.
        """
        clauses = [f'registre like "{siren}"']
        if famille:
            clauses.append(f'familleavis="{famille}"')

        resp = requests.get(self.BASE_URL, params={
            "where": " AND ".join(clauses),
            "order_by": "dateparution desc",
            "limit": str(min(limit, 100)),
        })
        resp.raise_for_status()
        data = resp.json()
        return {
            "results": self._clean_results(data.get("results", [])),
            "total_count": data.get("total_count", 0),
        }

    def search(
        self,
        query: Optional[str] = None,
        departement: Optional[str] = None,
        famille: Optional[str] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        limit: int = 20,
    ) -> dict[str, Any]:
        """Search BODACC announcements by keyword / filters."""
        clauses: list[str] = []
        if query:
            clauses.append(f'search(commercant, "{query}")')
        if departement:
            clauses.append(f'numerodepartement="{departement}"')
        if famille:
            clauses.append(f'familleavis="{famille}"')
        if date_from:
            clauses.append(f'dateparution>="{date_from}"')
        if date_to:
            clauses.append(f'dateparution<="{date_to}"')

        params: dict[str, str] = {
            "order_by": "dateparution desc",
            "limit": str(min(limit, 100)),
        }
        if clauses:
            params["where"] = " AND ".join(clauses)

        resp = requests.get(self.BASE_URL, params=params)
        resp.raise_for_status()
        data = resp.json()
        return {
            "results": self._clean_results(data.get("results", [])),
            "total_count": data.get("total_count", 0),
        }

    @staticmethod
    def _clean_results(results: list[dict]) -> list[dict]:
        """Keep only non-null fields and parse JSON strings."""
        import json as _json

        cleaned = []
        for r in results:
            out: dict[str, Any] = {}
            for k, v in r.items():
                if v is None:
                    continue
                if isinstance(v, str) and v.startswith("{"):
                    try:
                        v = _json.loads(v)
                    except ValueError:
                        pass
                out[k] = v
            cleaned.append(out)
        return cleaned
