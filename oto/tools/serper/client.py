"""
Serper API Client for Google search and web scraping.

Requires: requests
"""

import time
from typing import Optional, Dict, Any, List

import requests

from ...config import require_secret


class SerperClient:
    """
    Serper API client for:
    - Web search
    - News search
    - Page scraping
    - Search suggestions
    """

    BASE_URL = "https://google.serper.dev"
    SCRAPE_URL = "https://scrape.serper.dev"

    def __init__(self, api_key: str = None):
        """
        Initialize Serper client.

        Args:
            api_key: Serper API key (or set SERPER_API_KEY env var)
        """
        self.api_key = api_key or require_secret("SERPER_API_KEY")
        self.session = requests.Session()
        self.session.headers.update({
            "X-API-KEY": self.api_key,
            "Content-Type": "application/json"
        })
        self._last_request = 0.0
        self._min_interval = 0.5

    def _rate_limit(self):
        """Ensure minimum time between requests."""
        elapsed = time.time() - self._last_request
        if elapsed < self._min_interval:
            time.sleep(self._min_interval - elapsed)
        self._last_request = time.time()

    def _request(self, endpoint: str, json_data: Dict) -> Dict:
        """Make API request. Surface le message d'erreur Serper plutôt qu'un
        opaque "400 Bad Request" (Serper renvoie 400 + {"message":...} pour
        "Not enough credits", clé invalide, etc.)."""
        self._rate_limit()

        url = f"{self.BASE_URL}{endpoint}"
        response = self.session.post(url, json=json_data)
        if response.status_code >= 400:
            try:
                msg = response.json().get("message") or response.text
            except Exception:
                msg = response.text
            raise RuntimeError(f"Serper API {response.status_code}: {msg}")
        return response.json()

    def search(
        self,
        query: str,
        num: int = 10,
        page: int = 1,
        location: str = None,
        country: str = None,
        language: str = None,
        tbs: str = None,
        site_filter: str = None,
    ) -> Dict[str, Any]:
        """
        Perform web search.

        Args:
            query: Search query
            num: Number of results (max 100)
            page: Page number
            location: Geographic location
            country: Country code (e.g., 'us', 'fr')
            language: Language code (e.g., 'en', 'fr')
            tbs: Google time filter (e.g., 'qdr:d' for past day)
            site_filter: Limit to site (e.g., 'linkedin.com')

        Returns:
            Search results with 'organic' array
        """
        payload = {
            "q": query if not site_filter else f"site:{site_filter} {query}",
            "num": min(num, 100),
            "page": page
        }

        if location:
            payload["location"] = location
        if country:
            payload["gl"] = country
        if language:
            payload["hl"] = language
        if tbs:
            payload["tbs"] = tbs

        return self._request("/search", payload)

    def search_news(
        self,
        query: str,
        num: int = 10,
        tbs: str = None,
        country: str = None,
        language: str = None,
    ) -> Dict[str, Any]:
        """
        Search Google News.

        Args:
            query: Search query
            num: Number of results (max 100)
            tbs: Time filter (e.g., 'qdr:w' for past week)
            country: Country code
            language: Language code

        Returns:
            News results with 'news' array
        """
        payload = {
            "q": query,
            "num": min(num, 100),
            "type": "news"
        }

        if tbs:
            payload["tbs"] = tbs
        if country:
            payload["gl"] = country
        if language:
            payload["hl"] = language

        return self._request("/search", payload)

    def scrape_page(
        self,
        url: str,
        include_markdown: bool = False,
    ) -> Dict[str, Any]:
        """
        Scrape a web page.

        Args:
            url: URL to scrape
            include_markdown: Include markdown version

        Returns:
            Page data with text, metadata, and JSON-LD
        """
        self._rate_limit()

        payload = {"url": url}
        if include_markdown:
            payload["includeMarkdown"] = True

        response = self.session.post(self.SCRAPE_URL, json=payload)
        if response.status_code >= 400:
            try:
                msg = response.json().get("message") or response.text
            except Exception:
                msg = response.text
            raise RuntimeError(f"Serper scrape {response.status_code}: {msg}")
        return response.json()

    def get_suggestions(self, query: str, country: str = None) -> List[str]:
        """
        Get search autocomplete suggestions.

        Args:
            query: Base query
            country: Country code

        Returns:
            List of suggested queries
        """
        payload = {"q": query}
        if country:
            payload["gl"] = country

        try:
            result = self._request("/autocomplete", payload)
            suggestions = result.get("suggestions", [])
            return [s.get("value", "") for s in suggestions if s.get("value")]
        except:
            return []

    def batch_search(
        self,
        queries: List[str],
        num_per_query: int = 10,
        **kwargs,
    ) -> List[Dict[str, Any]]:
        """
        Perform multiple searches.

        Args:
            queries: List of queries
            num_per_query: Results per query
            **kwargs: Additional search params

        Returns:
            List of results per query
        """
        results = []
        for query in queries:
            try:
                result = self.search(query, num=num_per_query, **kwargs)
                results.append({"query": query, "results": result})
            except Exception as e:
                results.append({"query": query, "error": str(e), "results": {}})
        return results
