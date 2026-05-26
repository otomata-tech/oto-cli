"""BOAMP (Bulletin Officiel des Annonces de Marchés Publics) — open data via DILA.

Dataset: boamp on OpenDataSoft v2.1.
No auth required.
"""
from __future__ import annotations

from typing import Any, Optional

import requests


class BoampClient:
    BASE_URL = "https://boamp-datadila.opendatasoft.com/api/explore/v2.1/catalog/datasets/boamp/records"

    def search(
        self,
        query: Optional[str] = None,
        descripteur: Optional[str] = None,
        departement: Optional[str] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        type_marche: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> dict[str, Any]:
        """Search BOAMP procurement notices.

        Returns {results, total_count}.
        """
        clauses: list[str] = []
        if query:
            clauses.append(f'search(objet, "{query}")')
        if descripteur:
            clauses.append(f'descripteur_libelle="{descripteur}"')
        if departement:
            clauses.append(f'code_departement="{departement}"')
        if date_from:
            clauses.append(f'dateparution>="{date_from}"')
        if date_to:
            clauses.append(f'dateparution<="{date_to}"')
        if type_marche:
            clauses.append(f'type_marche="{type_marche}"')

        params: dict[str, str] = {
            "order_by": "dateparution desc",
            "limit": str(min(limit, 100)),
            "offset": str(offset),
        }
        if clauses:
            params["where"] = " AND ".join(clauses)

        resp = requests.get(self.BASE_URL, params=params)
        resp.raise_for_status()
        data = resp.json()
        return {
            "results": data.get("results", []),
            "total_count": data.get("total_count", 0),
        }

    def get(self, idweb: str) -> Optional[dict[str, Any]]:
        """Fetch a single BOAMP notice by idweb."""
        resp = requests.get(self.BASE_URL, params={
            "where": f'idweb="{idweb}"',
            "limit": "1",
        })
        resp.raise_for_status()
        results = resp.json().get("results", [])
        return results[0] if results else None
