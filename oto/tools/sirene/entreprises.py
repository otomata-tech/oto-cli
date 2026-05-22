"""
API Recherche Entreprises client (data.gouv.fr).

Provides enriched company data including:
- Directors (dirigeants)
- Financial data (chiffre d'affaires)
- Extended company information

No API key required.
"""

from typing import Optional, List, Dict, Any

import requests


class EntreprisesClient:
    """
    API Recherche Entreprises client (data.gouv.fr).

    Features:
    - Company search with rich filters
    - Directors information
    - Financial data
    - No authentication required
    """

    BASE_URL = "https://recherche-entreprises.api.gouv.fr"

    def search(
        self,
        query: str = None,
        naf: List[str] = None,
        departement: str = None,
        code_postal: str = None,
        commune: str = None,
        employees: List[str] = None,
        ca_min: int = None,
        ca_max: int = None,
        idcc: List[str] = None,
        page: int = 1,
        per_page: int = 25,
    ) -> Dict[str, Any]:
        """
        Search companies with enriched data.

        Args:
            query: Full-text search query
            naf: List of NAF codes (activite_principale)
            departement: Department code (e.g., '75')
            code_postal: Postal code
            commune: City name
            employees: List of employee range codes
            ca_min: Minimum turnover (chiffre d'affaires)
            ca_max: Maximum turnover
            idcc: List of IDCC codes (convention collective, e.g. ['1285', '3090'])
            page: Page number (1-based)
            per_page: Results per page (max 25)

        Returns:
            API response with results array and metadata

        Raises:
            ValueError: If no search parameters provided
            Exception: On API error
        """
        params = {
            "page": page,
            "per_page": min(per_page, 25),
        }

        if query:
            params["q"] = query
        if naf:
            params["activite_principale"] = ",".join(naf)
        if departement:
            params["departement"] = departement
        if code_postal:
            params["code_postal"] = code_postal
        if commune:
            params["commune"] = commune
        if employees:
            params["tranche_effectif_salarie_entreprise"] = ",".join(employees)
        if ca_min:
            params["ca_min"] = ca_min
        if ca_max:
            params["ca_max"] = ca_max
        if idcc:
            params["id_convention_collective"] = ",".join(idcc)

        # API requires at least one search parameter
        search_params = [
            "q", "activite_principale", "departement", "code_postal",
            "commune", "tranche_effectif_salarie_entreprise", "ca_min", "ca_max",
            "id_convention_collective",
        ]
        if not any(p in params for p in search_params):
            raise ValueError(
                "At least one search parameter required: "
                "query, naf, departement, code_postal, commune, employees, ca_min, ca_max"
            )

        resp = requests.get(
            f"{self.BASE_URL}/search",
            params=params,
            timeout=30,
        )

        if not resp.ok:
            try:
                error_msg = resp.json().get("erreur", f"API error: {resp.status_code}")
            except Exception:
                error_msg = f"API error: {resp.status_code} {resp.text}"
            raise Exception(error_msg)

        return resp.json()

    def get_by_siren(self, siren: str) -> Optional[Dict[str, Any]]:
        """
        Get company by SIREN with enriched data.

        Args:
            siren: 9-digit SIREN number

        Returns:
            Company data or None if not found
        """
        resp = requests.get(
            f"{self.BASE_URL}/search",
            params={"q": siren, "per_page": 1},
            timeout=30,
        )

        if not resp.ok:
            raise Exception(f"API error: {resp.status_code} {resp.text}")

        data = resp.json()
        results = data.get("results", [])

        if not results:
            return None

        # Find exact SIREN match
        for r in results:
            if r.get("siren") == siren:
                return r

        return results[0] if results else None

    def get_directors(self, siren: str) -> List[Dict[str, Any]]:
        """
        Get company directors (dirigeants).

        Args:
            siren: 9-digit SIREN number

        Returns:
            List of directors with name, role, and dates
        """
        company = self.get_by_siren(siren)
        if not company:
            return []

        return company.get("dirigeants", [])

    def get_finances(self, siren: str) -> Optional[Dict[str, Any]]:
        """
        Get company financial data.

        Args:
            siren: 9-digit SIREN number

        Returns:
            Financial data (chiffre_affaires, resultat, etc.) or None
        """
        company = self.get_by_siren(siren)
        if not company:
            return None

        return company.get("finances")
