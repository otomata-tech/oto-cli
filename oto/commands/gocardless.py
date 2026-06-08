"""GoCardless direct-debit commands (read-only).

⚠️ Surface lecture seule. GoCardless est une source : pas de création/annulation
de prélèvement exposée ici. Clé : secret GOCARDLESS_API_KEY (env ou SOPS).
"""

import json
from typing import Optional

import typer

app = typer.Typer(help="GoCardless direct-debit API (read-only)")


def _client():
    from oto.tools.gocardless import GoCardlessClient
    return GoCardlessClient()


def _out(data):
    print(json.dumps(data, indent=2, ensure_ascii=False))


@app.command("creditors")
def creditors():
    """Comptes marchands (compte encaisseur GoCardless)."""
    _out(_client().list_creditors())


@app.command("payments")
def payments(
    status: Optional[str] = typer.Option(None, "--status", "-s", help="failed, confirmed, paid_out, submitted, cancelled, charged_back…"),
    limit: int = typer.Option(50, "--limit", "-n", help="Taille de page (max 500)"),
    mandate: Optional[str] = typer.Option(None, "--mandate", help="Filtrer par mandat (MD…)"),
    customer: Optional[str] = typer.Option(None, "--customer", help="Filtrer par customer (CU…)"),
    since: Optional[str] = typer.Option(None, "--since", help="Créés après (ISO8601, ex 2026-06-01)"),
):
    """Liste de prélèvements (1 page)."""
    _out(_client().list_payments(status=status, limit=limit, mandate=mandate,
                                 customer=customer, created_gt=since))


@app.command("payment")
def payment(payment_id: str = typer.Argument(..., help="ID prélèvement (PM…)")):
    """Détail brut d'un prélèvement."""
    _out(_client().get_payment(payment_id))


@app.command("mandate")
def mandate(mandate_id: str = typer.Argument(..., help="ID mandat (MD…)")):
    """Détail brut d'un mandat."""
    _out(_client().get_mandate(mandate_id))


@app.command("customer")
def customer(customer_id: str = typer.Argument(..., help="ID customer (CU…)")):
    """Détail brut d'un customer."""
    _out(_client().get_customer(customer_id))


@app.command("events")
def events(
    payment: Optional[str] = typer.Option(None, "--payment", "-p", help="Filtrer par prélèvement (PM…)"),
    mandate: Optional[str] = typer.Option(None, "--mandate", "-m", help="Filtrer par mandat (MD…)"),
    action: Optional[str] = typer.Option(None, "--action", "-a", help="Filtrer par action (ex failed, paid_out)"),
    limit: int = typer.Option(50, "--limit", "-n", help="Taille de page"),
):
    """Timeline d'events (motif d'échec : --action failed sur un --payment)."""
    _out(_client().list_events(payment=payment, mandate=mandate, action=action, limit=limit))


@app.command("party")
def party(payment_id: str = typer.Argument(..., help="ID prélèvement (PM…)")):
    """Résout payment → mandat → customer (email/société/metadata aplatis)."""
    _out(_client().payment_party(payment_id))


@app.command("failure")
def failure(payment_id: str = typer.Argument(..., help="ID prélèvement (PM…)")):
    """Motif du dernier échec (cause, description, will_attempt_retry)."""
    _out(_client().failure_reason(payment_id))


@app.command("failed")
def failed(
    since: Optional[str] = typer.Option(None, "--since", help="Créés après (ISO8601, ex 2026-05-25)"),
    limit: int = typer.Option(200, "--limit", "-n", help="Taille de page des failed à enrichir (max 500)"),
):
    """Prélèvements refusés enrichis (client + motif + état mandat) en un appel."""
    _out(_client().failed_payments(since=since, limit=limit))
