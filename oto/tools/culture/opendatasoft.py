"""Generic Opendatasoft Explore v2.1 client.

Targets any public Opendatasoft portal (data.culture.gouv.fr,
data.economie.gouv.fr, ANCT, ADEME, regional portals, etc.).

No auth required for public datasets.
"""

from typing import Any, Optional, Mapping
from urllib.parse import urlencode

import requests


class OpendatasoftClient:
    """Thin wrapper around the Opendatasoft Explore v2.1 records API.

    Args:
        base_url: Portal root, e.g. "https://data.culture.gouv.fr".
        timeout: HTTP timeout in seconds.
    """

    def __init__(self, base_url: str, timeout: int = 30):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def _records_url(self, dataset_id: str) -> str:
        return f"{self.base_url}/api/explore/v2.1/catalog/datasets/{dataset_id}/records"

    def _exports_url(self, dataset_id: str, fmt: str) -> str:
        return f"{self.base_url}/api/explore/v2.1/catalog/datasets/{dataset_id}/exports/{fmt}"

    def _facets_url(self, dataset_id: str) -> str:
        return f"{self.base_url}/api/explore/v2.1/catalog/datasets/{dataset_id}/facets"

    def records(
        self,
        dataset_id: str,
        *,
        where: Optional[str] = None,
        select: Optional[str] = None,
        order_by: Optional[str] = None,
        group_by: Optional[str] = None,
        limit: int = 20,
        offset: int = 0,
        refine: Optional[Mapping[str, str]] = None,
    ) -> dict[str, Any]:
        """Query the /records endpoint. Returns the raw JSON."""
        params: list[tuple[str, str]] = []
        if where: params.append(("where", where))
        if select: params.append(("select", select))
        if order_by: params.append(("order_by", order_by))
        if group_by: params.append(("group_by", group_by))
        params.append(("limit", str(min(100, max(1, limit)))))
        params.append(("offset", str(max(0, offset))))
        if refine:
            for k, v in refine.items():
                params.append(("refine", f"{k}:{v}"))
        resp = requests.get(self._records_url(dataset_id), params=params, timeout=self.timeout)
        resp.raise_for_status()
        return resp.json()

    def iter_records(
        self,
        dataset_id: str,
        *,
        where: Optional[str] = None,
        select: Optional[str] = None,
        order_by: Optional[str] = None,
        page_size: int = 100,
        max_total: Optional[int] = None,
    ):
        """Paginate through /records until exhausted or max_total reached.

        Yields individual record dicts.
        """
        offset = 0
        yielded = 0
        while True:
            page = self.records(
                dataset_id,
                where=where, select=select, order_by=order_by,
                limit=page_size, offset=offset,
            )
            results = page.get("results", [])
            if not results:
                return
            for row in results:
                yield row
                yielded += 1
                if max_total is not None and yielded >= max_total:
                    return
            if len(results) < page_size:
                return
            offset += page_size

    def export_url(self, dataset_id: str, fmt: str = "csv", *, where: Optional[str] = None) -> str:
        """Build a direct export URL — caller streams it (potentially large)."""
        q = {}
        if where: q["where"] = where
        qs = ("?" + urlencode(q)) if q else ""
        return f"{self._exports_url(dataset_id, fmt)}{qs}"

    def facets(
        self,
        dataset_id: str,
        facets: list[str],
        *,
        where: Optional[str] = None,
    ) -> dict[str, Any]:
        """Get facet counts. `facets` is the list of field names."""
        params: list[tuple[str, str]] = [("facet", f) for f in facets]
        if where:
            params.append(("where", where))
        resp = requests.get(self._facets_url(dataset_id), params=params, timeout=self.timeout)
        resp.raise_for_status()
        return resp.json()
