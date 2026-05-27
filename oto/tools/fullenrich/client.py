"""
FullEnrich API Client — waterfall multi-provider contact enrichment.

Async bulk API: POST job → poll until FINISHED (~30s-4min).
Pricing: 10 cr/phone, 1 cr/work_email, 3 cr/personal_email (pay-per-result).
Phone hit rate ~70% vs Kaspr ~13%.

Requires: requests
"""

from __future__ import annotations

import time
from typing import Optional

import requests

from ...config import require_secret


class FullenrichProfile:
    """Parsed enrichment result for 1 LinkedIn profile."""

    def __init__(
        self,
        linkedin_slug: str,
        first_name: str | None = None,
        last_name: str | None = None,
        full_name: str | None = None,
        title: str | None = None,
        company_name: str | None = None,
        phones: list[str] | None = None,
        work_emails: list[str] | None = None,
        personal_emails: list[str] | None = None,
        location: str | None = None,
        raw_data: dict | None = None,
        fetched_at: str | None = None,
    ):
        self.linkedin_slug = linkedin_slug
        self.first_name = first_name
        self.last_name = last_name
        self.full_name = full_name
        self.title = title
        self.company_name = company_name
        self.phones = phones or []
        self.work_emails = work_emails or []
        self.personal_emails = personal_emails or []
        self.location = location
        self.raw_data = raw_data
        self.fetched_at = fetched_at

    def to_dict(self) -> dict:
        return {
            "linkedin_slug": self.linkedin_slug,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "full_name": self.full_name,
            "title": self.title,
            "company_name": self.company_name,
            "phones": self.phones,
            "work_emails": self.work_emails,
            "personal_emails": self.personal_emails,
            "location": self.location,
            "fetched_at": self.fetched_at,
        }


class FullenrichClient:
    BASE_URL = "https://app.fullenrich.com/api/v2"
    POLL_INTERVAL_S = 8
    MAX_POLLS = 30

    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or require_secret("FULLENRICH_API_KEY")

    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    def enrich_linkedin(
        self,
        linkedin_slug: str,
        first_name: str,
        last_name: str,
        company_name: Optional[str] = None,
    ) -> FullenrichProfile | None:
        """Enrich a LinkedIn profile. Returns None if no data found."""
        slug = linkedin_slug.strip().strip("/")
        linkedin_url = f"https://www.linkedin.com/in/{slug}/"

        payload = {
            "name": f"oto-{int(time.time())}",
            "data": [
                {
                    "first_name": first_name,
                    "last_name": last_name,
                    **({"company_name": company_name} if company_name else {}),
                    "linkedin_url": linkedin_url,
                    "enrich_fields": ["contact.work_emails", "contact.phones"],
                    "custom": {"slug": slug},
                }
            ],
        }

        resp = requests.post(
            f"{self.BASE_URL}/contact/enrich/bulk",
            headers=self._headers(),
            json=payload,
            timeout=30,
        )
        if resp.status_code != 200:
            raise RuntimeError(f"FullEnrich POST {resp.status_code}: {resp.text[:200]}")

        enrichment_id = resp.json().get("enrichment_id")
        if not enrichment_id:
            raise RuntimeError(f"FullEnrich POST: no enrichment_id in response: {resp.text[:200]}")

        return self._poll(enrichment_id, slug)

    def _poll(self, enrichment_id: str, slug: str) -> FullenrichProfile | None:
        for _ in range(self.MAX_POLLS):
            time.sleep(self.POLL_INTERVAL_S)

            resp = requests.get(
                f"{self.BASE_URL}/contact/enrich/bulk/{enrichment_id}",
                headers=self._headers(),
                timeout=30,
            )
            if resp.status_code != 200:
                raise RuntimeError(f"FullEnrich GET {resp.status_code}: {resp.text[:200]}")

            body = resp.json()
            status = body.get("status", "")

            if status == "CREDITS_INSUFFICIENT":
                raise RuntimeError("FullEnrich : crédits insuffisants. Recharger sur app.fullenrich.com.")

            if status != "FINISHED":
                continue

            data_list = body.get("data", [])
            if not data_list:
                return None

            return self._parse(data_list[0], slug, body)

        raise RuntimeError("FullEnrich : timeout polling (>4 min)")

    def _parse(self, item: dict, slug: str, raw: dict) -> FullenrichProfile | None:
        contact = item.get("contact_info") or {}
        profile = item.get("profile") or {}
        employment = (profile.get("employment") or {}).get("all") or []
        loc = profile.get("location") or {}

        phones = [p["number"] for p in (contact.get("phones") or []) if p.get("number")]
        work_emails = [e["email"] for e in (contact.get("work_emails") or []) if e.get("email")]
        personal_emails = [e["email"] for e in (contact.get("personal_emails") or []) if e.get("email")]

        if not phones and not work_emails and not personal_emails:
            return None

        title = employment[0].get("title") if employment else None
        company = employment[0].get("company", {}).get("name") if employment else None
        location_parts = [loc.get("city"), loc.get("country")]
        location_str = ", ".join(p for p in location_parts if p) or None

        from datetime import datetime, timezone

        return FullenrichProfile(
            linkedin_slug=slug,
            first_name=profile.get("first_name"),
            last_name=profile.get("last_name"),
            full_name=profile.get("full_name"),
            title=title,
            company_name=company,
            phones=phones,
            work_emails=work_emails,
            personal_emails=personal_emails,
            location=location_str,
            raw_data=raw,
            fetched_at=datetime.now(timezone.utc).isoformat(),
        )
