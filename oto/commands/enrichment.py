"""Contact enrichment commands (Kaspr, Hunter, Lemlist)."""

import typer
from typing import Optional

app = typer.Typer(help="Contact enrichment tools")

# Kaspr subcommands
kaspr_app = typer.Typer(help="Kaspr contact enrichment")
app.add_typer(kaspr_app, name="kaspr")

# Hunter subcommands
hunter_app = typer.Typer(help="Hunter.io email tools")
app.add_typer(hunter_app, name="hunter")

# Lemlist subcommands
lemlist_app = typer.Typer(help="Lemlist campaign & lead management")
app.add_typer(lemlist_app, name="lemlist")


@kaspr_app.command("enrich")
def kaspr_enrich(
    linkedin_slug: str = typer.Argument(..., help="LinkedIn profile slug"),
    name: Optional[str] = typer.Option(None, "--name", help="Person full name"),
    with_phone: bool = typer.Option(False, "--with-phone", help="Include phone (costs credits, reserved for UI)"),
):
    """Enrich a LinkedIn profile with Kaspr (emails by default, phone opt-in)."""
    import json
    from oto.tools.kaspr import KasprClient

    client = KasprClient()
    data_to_get = ["workEmail", "phone"] if with_phone else None
    result = client.enrich_linkedin(linkedin_slug, name=name, data_to_get=data_to_get)
    print(json.dumps(result, indent=2, ensure_ascii=False))


@hunter_app.command("domain")
def hunter_domain(
    domain: str = typer.Argument(..., help="Domain to search"),
    limit: int = typer.Option(10, "--limit", "-n", help="Max results"),
):
    """Search emails for a domain via Hunter."""
    import json
    from oto.tools.hunter import HunterClient

    client = HunterClient()
    result = client.domain_search(domain, limit=limit)
    print(json.dumps(result, indent=2, ensure_ascii=False))


@hunter_app.command("find")
def hunter_find(
    domain: str = typer.Argument(..., help="Domain"),
    name: str = typer.Option(..., "--name", help="Full name"),
):
    """Find email for a person at a domain via Hunter."""
    import json
    from oto.tools.hunter import HunterClient

    client = HunterClient()
    result = client.email_finder(domain, full_name=name)
    print(json.dumps(result, indent=2, ensure_ascii=False))


@hunter_app.command("verify")
def hunter_verify(
    email: str = typer.Argument(..., help="Email to verify"),
):
    """Verify an email address via Hunter."""
    import json
    from oto.tools.hunter import HunterClient

    client = HunterClient()
    result = client.email_verifier(email)
    print(json.dumps(result, indent=2, ensure_ascii=False))


@lemlist_app.command("campaigns")
def lemlist_campaigns():
    """List all Lemlist campaigns."""
    import json
    from oto.tools.lemlist import LemlistClient

    client = LemlistClient()
    campaigns = client.list_campaigns()
    result = [{"id": c.id, "name": c.name, "status": c.status, "senders": c.senders} for c in campaigns]
    print(json.dumps(result, indent=2, ensure_ascii=False))


@lemlist_app.command("leads")
def lemlist_leads(
    campaign_id: str = typer.Argument(..., help="Campaign ID"),
):
    """List leads in a campaign."""
    import json
    from oto.tools.lemlist import LemlistClient

    client = LemlistClient()
    leads = client.get_all_leads(campaign_id)
    print(json.dumps(leads, indent=2, ensure_ascii=False))


@lemlist_app.command("add-lead")
def lemlist_add_lead(
    campaign_id: str = typer.Argument(..., help="Campaign ID"),
    email: str = typer.Option(..., "--email", "-e", help="Lead email"),
    first_name: str = typer.Option(None, "--first-name", help="First name"),
    last_name: str = typer.Option(None, "--last-name", help="Last name"),
    company: str = typer.Option(None, "--company", help="Company name"),
    phone: str = typer.Option(None, "--phone", help="Phone number"),
    linkedin: str = typer.Option(None, "--linkedin", help="LinkedIn URL"),
):
    """Add a lead to a Lemlist campaign."""
    import json
    from oto.tools.lemlist import LemlistClient
    from oto.tools.lemlist.client import Lead

    client = LemlistClient()
    lead = Lead(
        email=email,
        firstName=first_name,
        lastName=last_name,
        companyName=company,
        phone=phone,
        linkedinUrl=linkedin,
    )
    result = client.add_lead(campaign_id, lead)
    print(json.dumps(result, indent=2, ensure_ascii=False))


@lemlist_app.command("delete-lead")
def lemlist_delete_lead(
    campaign_id: str = typer.Argument(..., help="Campaign ID"),
    email: str = typer.Argument(..., help="Lead email to remove"),
):
    """Remove a lead from a Lemlist campaign."""
    import json
    from oto.tools.lemlist import LemlistClient

    client = LemlistClient()
    result = client.delete_lead(campaign_id, email)
    print(json.dumps(result, indent=2, ensure_ascii=False))


@lemlist_app.command("export")
def lemlist_export(
    campaign_id: str = typer.Argument(..., help="Campaign ID"),
):
    """Export leads from a campaign as CSV."""
    from oto.tools.lemlist import LemlistClient

    client = LemlistClient()
    csv_data = client.export_leads(campaign_id)
    print(csv_data)
