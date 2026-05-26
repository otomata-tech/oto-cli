"""INPI/BCE financial ratios — open data from data.economie.gouv.fr.

Dataset: ratios_inpi_bce (Banque de France via OpenDataSoft v2.1).
No auth required.
"""
from __future__ import annotations

from typing import Any, Optional

import requests


class InpiClient:
    BASE_URL = "https://data.economie.gouv.fr/api/explore/v2.1/catalog/datasets/ratios_inpi_bce/records"

    def list_exercises(self, siren: str) -> list[dict[str, Any]]:
        """List available annual filings for a SIREN (most recent first)."""
        items: list[dict] = []
        offset = 0
        while offset <= 1000:
            resp = requests.get(self.BASE_URL, params={
                "where": f'siren in ("{siren}")',
                "select": "siren,date_cloture_exercice,type_bilan,confidentiality,chiffre_d_affaires",
                "order_by": "date_cloture_exercice desc",
                "limit": "100",
                "offset": str(offset),
            })
            resp.raise_for_status()
            results = resp.json().get("results", [])
            items.extend(results)
            if len(results) < 100:
                break
            offset += 100
        return items

    def get_bilan(self, siren: str, date_cloture: str) -> Optional[dict[str, Any]]:
        """Fetch one annual filing by SIREN + closing date (YYYY-MM-DD)."""
        resp = requests.get(self.BASE_URL, params={
            "where": f"siren in (\"{siren}\") and date_cloture_exercice=date'{date_cloture}'",
            "limit": "1",
        })
        resp.raise_for_status()
        results = resp.json().get("results", [])
        return results[0] if results else None
