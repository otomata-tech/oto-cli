"""
GoCardless API Pro Client — READ-ONLY surface for direct-debit data.

Pourquoi read-only : dans les usages oto (réconciliation, traitement des
prélèvements échoués → avoirs), GoCardless n'est qu'une **source de lecture**.
La mutation (émettre un avoir) vit ailleurs (Pennylane). On n'expose donc
aucun POST/PUT/DELETE ici — un agent ne peut pas annuler un prélèvement par
erreur.

Auth : Bearer token. Header `GoCardless-Version` obligatoire.
Clé résolue via `require_secret("GOCARDLESS_API_KEY")` (env ou SOPS), ou
passée explicitement. ⚠️ Un token `live_` frappe les données réelles.

Chaîne de données : payment → links.mandate → mandate.links.customer.
Le motif d'un échec vit dans l'Events API (action=failed).

Usage :
    client = GoCardlessClient(api_key="live_...")
    failed = client.list_payments(status="failed", limit=20)
    party = client.payment_party(failed[0]["id"])   # customer + motif résolu
"""

import time
from typing import Optional

import requests

from ...config import require_secret


class GoCardlessClient:
    """Client lecture seule pour l'API GoCardless Pro v2015-07-06."""

    BASE_URL = "https://api.gocardless.com"
    API_VERSION = "2015-07-06"

    def __init__(self, api_key: str = None, rate_limit_delay: float = 0.2):
        """
        Args:
            api_key: Bearer token GoCardless (ou secret GOCARDLESS_API_KEY).
            rate_limit_delay: pause entre requêtes paginées.
        """
        self.api_key = api_key or require_secret("GOCARDLESS_API_KEY")
        self.rate_limit_delay = rate_limit_delay
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {self.api_key}",
            "GoCardless-Version": self.API_VERSION,
            "Accept": "application/json",
        })

    # --- Primitive GET ---

    def fetch(self, endpoint: str, params: Optional[dict] = None, retries: int = 3) -> dict:
        """GET sur l'API avec retry sur rate-limit (429)."""
        url = f"{self.BASE_URL}/{endpoint.lstrip('/')}"
        for attempt in range(retries):
            try:
                response = self.session.get(url, params=params, timeout=30)
                if response.status_code == 429:
                    time.sleep(2 ** attempt)
                    continue
                if not response.ok:
                    return {
                        "error": str(response.status_code),
                        "details": response.text,
                        "status_code": response.status_code,
                    }
                return response.json()
            except Exception as e:
                return {"error": str(e)}
        return {"error": "Max retries exceeded"}

    def fetch_all(self, resource: str, params: Optional[dict] = None,
                  max_pages: Optional[int] = None) -> list:
        """Pagination cursor GoCardless (`meta.cursors.after`).

        `resource` est la clé de collection (ex. 'payments', 'events') qui sert
        à la fois d'endpoint et de clé dans la réponse.
        """
        params = dict(params or {})
        out, pages, after = [], 0, None
        while True:
            if after:
                params["after"] = after
            data = self.fetch(resource, params)
            if "error" in data:
                if not out:
                    return data  # remonte l'erreur si rien collecté
                break
            out.extend(data.get(resource, []))
            after = data.get("meta", {}).get("cursors", {}).get("after")
            pages += 1
            if not after or (max_pages and pages >= max_pages):
                break
            time.sleep(self.rate_limit_delay)
        return out

    # --- Lectures simples ---

    def list_creditors(self) -> list:
        """Comptes marchands GoCardless (le compte encaisseur)."""
        return self.fetch("creditors").get("creditors", [])

    def list_payments(self, status: Optional[str] = None, limit: int = 50,
                      mandate: Optional[str] = None, customer: Optional[str] = None,
                      created_gt: Optional[str] = None) -> list:
        """Liste de prélèvements (1 page).

        Args:
            status: filtre statut. Valeurs : pending_submission, submitted,
                confirmed, paid_out, failed, cancelled, charged_back, etc.
            limit: taille de page (max 500 côté API).
            mandate / customer: filtres par lien.
            created_gt: ISO8601, prélèvements créés après cette date.
        """
        params = {"limit": limit}
        if status:
            params["status"] = status
        if mandate:
            params["mandate"] = mandate
        if customer:
            params["customer"] = customer
        if created_gt:
            params["created_at[gt]"] = created_gt
        return self.fetch("payments", params).get("payments", [])

    def get_payment(self, payment_id: str) -> dict:
        return self.fetch(f"payments/{payment_id}").get("payments", {})

    def get_mandate(self, mandate_id: str) -> dict:
        return self.fetch(f"mandates/{mandate_id}").get("mandates", {})

    def get_customer(self, customer_id: str) -> dict:
        return self.fetch(f"customers/{customer_id}").get("customers", {})

    def list_events(self, payment: Optional[str] = None, mandate: Optional[str] = None,
                    action: Optional[str] = None, resource_type: Optional[str] = None,
                    limit: int = 50) -> list:
        """Events (timeline). Le motif d'un échec : action='failed' sur un payment."""
        params = {"limit": limit}
        if payment:
            params["payment"] = payment
        if mandate:
            params["mandate"] = mandate
        if action:
            params["action"] = action
        if resource_type:
            params["resource_type"] = resource_type
        return self.fetch("events", params).get("events", [])

    # --- Agrégats métier ---

    def payment_party(self, payment_id: str) -> dict:
        """Résout la chaîne payment → mandate → customer pour un prélèvement.

        Renvoie un dict aplati : montant, statut, dates, et la contrepartie
        (email, nom/société, metadata). ⚠️ La metadata GoCardless ne contient
        pas forcément d'identifiant client externe (cas Movinmotion : vide).
        """
        p = self.get_payment(payment_id)
        if "error" in p:
            return p
        mandate_id = p.get("links", {}).get("mandate")
        mandate = self.get_mandate(mandate_id) if mandate_id else {}
        customer_id = mandate.get("links", {}).get("customer")
        customer = self.get_customer(customer_id) if customer_id else {}
        name = customer.get("company_name") or " ".join(
            filter(None, [customer.get("given_name"), customer.get("family_name")])
        )
        return {
            "payment_id": payment_id,
            "amount": p.get("amount", 0) / 100,
            "currency": p.get("currency"),
            "status": p.get("status"),
            "charge_date": p.get("charge_date"),
            "created_at": p.get("created_at"),
            "mandate_id": mandate_id,
            "mandate_status": mandate.get("status"),
            "scheme": mandate.get("scheme"),
            "customer_id": customer_id,
            "email": customer.get("email"),
            "name": name,
            "metadata": customer.get("metadata", {}),
        }

    def failure_reason(self, payment_id: str) -> dict:
        """Motif du dernier échec d'un prélèvement (Events API).

        Renvoie cause/description/reason_code/will_attempt_retry. Si
        `will_attempt_retry` est True, GoCardless va retenter — ne pas émettre
        d'avoir tant que ce n'est pas False.
        """
        events = self.list_events(payment=payment_id, action="failed", limit=10)
        if isinstance(events, dict):  # erreur remontée
            return events
        if not events:
            return {"failed": False}
        ev = events[0]  # le plus récent
        d = ev.get("details", {})
        return {
            "failed": True,
            "created_at": ev.get("created_at"),
            "cause": d.get("cause"),
            "description": d.get("description"),
            "reason_code": d.get("reason_code"),
            "scheme": d.get("scheme"),
            "will_attempt_retry": d.get("will_attempt_retry"),
        }
