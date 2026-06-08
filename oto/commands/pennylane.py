"""Pennylane accounting commands."""

import json
from typing import List, Optional

import typer

app = typer.Typer(help="Pennylane accounting API")


def _client():
    from oto.tools.pennylane import PennylaneClient
    return PennylaneClient()


def _out(data):
    print(json.dumps(data, indent=2, ensure_ascii=False))


# --- Read commands ---


@app.command("company")
def company():
    """Get company info."""
    _out(_client().get_company_info())


@app.command("fiscal-years")
def fiscal_years():
    """Get fiscal years."""
    _out(_client().get_fiscal_years())


@app.command("trial-balance")
def trial_balance(
    start: str = typer.Option(..., "--start", help="Period start (YYYY-MM-DD)"),
    end: str = typer.Option(..., "--end", help="Period end (YYYY-MM-DD)"),
):
    """Get trial balance for a period."""
    _out(_client().get_trial_balance(start, end))


@app.command("ledger-accounts")
def ledger_accounts():
    """Get all ledger accounts."""
    _out(_client().get_ledger_accounts())


@app.command("customer-invoices")
def customer_invoices(
    max_pages: int = typer.Option(50, "--max-pages", help="Max pages to fetch"),
):
    """List customer invoices."""
    _out(_client().get_customer_invoices(max_pages=max_pages))


@app.command("supplier-invoices")
def supplier_invoices(
    max_pages: int = typer.Option(50, "--max-pages", help="Max pages to fetch"),
):
    """List supplier invoices."""
    _out(_client().get_supplier_invoices(max_pages=max_pages))


@app.command("categories")
def categories():
    """Get expense categories."""
    _out(_client().get_categories())


@app.command("complete")
def complete(
    year: int = typer.Option(2025, "--year", help="Fiscal year to fetch"),
):
    """Fetch complete financial data for a year."""
    _out(_client().fetch_complete_data(year=year))


# --- Transactions ---


@app.command("transactions")
def transactions(
    max_pages: int = typer.Option(50, "--max-pages", help="Max pages to fetch"),
):
    """List bank transactions."""
    _out(_client().get_transactions(max_pages=max_pages))


@app.command("suppliers")
def suppliers(
    max_pages: int = typer.Option(50, "--max-pages", help="Max pages to fetch"),
):
    """List suppliers."""
    _out(_client().fetch_all_pages("suppliers", max_pages=max_pages))


# --- File uploads ---


@app.command("upload")
def upload(
    file_path: str = typer.Argument(..., help="Path to PDF file"),
):
    """Upload a PDF file (invoice) to Pennylane."""
    _out(_client().upload_file(file_path))


@app.command("upload-dir")
def upload_dir(
    directory: str = typer.Argument(..., help="Directory containing PDF files"),
):
    """Upload all PDFs in a directory to Pennylane."""
    import glob
    import time as _time

    client = _client()
    files = sorted(glob.glob(f"{directory}/*.pdf"))
    results = {"ok": 0, "errors": 0}
    for f in files:
        name = f.split("/")[-1]
        result = client.upload_file(f)
        _time.sleep(0.3)
        if "error" in result:
            print(f"  ERR {name}: {result.get('details', result.get('error'))[:80]}")
            results["errors"] += 1
        else:
            print(f"  OK  {name} (id={result['id']})")
            results["ok"] += 1
    print(f"\nDone: {results['ok']} uploaded, {results['errors']} errors")


# --- Match ---


@app.command("match")
def match_transaction(
    invoice_id: int = typer.Argument(..., help="Supplier or customer invoice ID"),
    transaction_id: int = typer.Argument(..., help="Transaction ID"),
    invoice_type: str = typer.Option("supplier", "--type", "-t", help="supplier or customer"),
):
    """Match a transaction to an invoice."""
    _out(_client().match_transaction(invoice_id, transaction_id, invoice_type))


# --- Customers ---


@app.command("customers")
def customers(
    max_pages: int = typer.Option(50, "--max-pages", help="Max pages to fetch"),
):
    """List customers."""
    _out(_client().list_customers(max_pages=max_pages))


@app.command("create-customer")
def create_customer(
    name: str = typer.Argument(..., help="Customer name"),
    email: Optional[str] = typer.Option(None, "--email", "-e", help="Email"),
    address: Optional[str] = typer.Option(None, "--address", help="Street address"),
    postal_code: Optional[str] = typer.Option(None, "--postal-code", help="Postal code"),
    city: Optional[str] = typer.Option(None, "--city", help="City"),
    ref: Optional[str] = typer.Option(None, "--ref", help="External reference (Attio Deal slug — join key Pennylane/Attio/FS, NOT the SIREN)"),
):
    """Create a customer.

    SIREN/SIRET (reg_no) and VAT number are not set here — run `update-customer`
    afterwards with --reg-no and --vat to fill those native fields.
    """
    result = _client().create_customer(
        name=name,
        emails=[email] if email else None,
        address=address, postal_code=postal_code,
        city=city, external_reference=ref,
    )
    _out(result)


@app.command("update-customer")
def update_customer(
    customer_id: int = typer.Argument(..., help="Customer ID"),
    name: Optional[str] = typer.Option(None, "--name", help="Customer name"),
    reg_no: Optional[str] = typer.Option(None, "--reg-no", help="Registration number (SIREN for FR, KvK for NL, etc.)"),
    vat_number: Optional[str] = typer.Option(None, "--vat", help="VAT number (e.g. FR06993454404, NL817576320B01)"),
    ref: Optional[str] = typer.Option(None, "--ref", help="External reference (Attio Deal slug)"),
    email: Optional[str] = typer.Option(None, "--email", "-e", help="Email"),
    address: Optional[str] = typer.Option(None, "--address", help="Street address"),
    postal_code: Optional[str] = typer.Option(None, "--postal-code", help="Postal code"),
    city: Optional[str] = typer.Option(None, "--city", help="City"),
):
    """Update a customer."""
    fields = {}
    if name:
        fields["name"] = name
    if reg_no:
        fields["reg_no"] = reg_no
    if vat_number:
        fields["vat_number"] = vat_number
    if ref:
        fields["external_reference"] = ref
    if email:
        fields["emails"] = [email]
    if address or postal_code or city:
        fields["billing_address"] = {
            k: v for k, v in {
                "address": address, "postal_code": postal_code, "city": city,
            }.items() if v
        }
    _out(_client().update_customer(customer_id, **fields))


# --- Products ---


@app.command("products")
def products(
    max_pages: int = typer.Option(50, "--max-pages", help="Max pages to fetch"),
):
    """List products."""
    _out(_client().list_products(max_pages=max_pages))


@app.command("create-product")
def create_product(
    label: str = typer.Argument(..., help="Product label"),
    price: str = typer.Option(..., "--price", "-p", help="Unit price HT (e.g. '700.00')"),
    unit: str = typer.Option("day", "--unit", "-u", help="Unit: day, hour, piece"),
    vat_rate: str = typer.Option("FR_200", "--vat", help="VAT rate code (FR_200, FR_100, FR_055, exempt)"),
    description: Optional[str] = typer.Option(None, "--desc", help="Description"),
):
    """Create a product."""
    result = _client().create_product(
        label=label, unit_price=price, unit=unit,
        vat_rate=vat_rate, description=description,
    )
    _out(result)


# --- Invoices ---


@app.command("create-invoice")
def create_invoice(
    customer_id: int = typer.Option(..., "--customer", "-c", help="Customer ID"),
    date: str = typer.Option(..., "--date", "-d", help="Invoice date (YYYY-MM-DD)"),
    deadline: str = typer.Option(..., "--deadline", help="Payment deadline (YYYY-MM-DD)"),
    line: List[str] = typer.Option(..., "--line", "-l", help="Line: product_id:quantity[:unit_price]"),
    ref: Optional[str] = typer.Option(None, "--ref", help="External reference"),
    finalize: bool = typer.Option(False, "--finalize", help="Finalize (not draft)"),
):
    """Create a customer invoice (draft by default).

    Lines format: --line product_id:quantity[:unit_price]
    Example: --line 123:5 --line 456:2:800.00
    """
    lines = []
    for l in line:
        parts = l.split(":")
        entry = {"product_id": int(parts[0]), "quantity": float(parts[1])}
        if len(parts) >= 3:
            entry["raw_currency_unit_price"] = parts[2]
        lines.append(entry)

    result = _client().create_customer_invoice(
        customer_id=customer_id, date=date, deadline=deadline,
        lines=lines, draft=not finalize, external_reference=ref,
    )
    _out(result)


@app.command("update-invoice")
def update_invoice(
    invoice_id: int = typer.Argument(..., help="Invoice ID"),
    customer_id: Optional[int] = typer.Option(None, "--customer", "-c", help="New customer ID"),
    date: Optional[str] = typer.Option(None, "--date", "-d", help="Invoice date"),
    deadline: Optional[str] = typer.Option(None, "--deadline", help="Payment deadline"),
):
    """Update a draft invoice header (customer/date/deadline). Use update-invoice-line for line edits."""
    fields = {}
    if customer_id:
        fields["customer_id"] = customer_id
    if date:
        fields["date"] = date
    if deadline:
        fields["deadline"] = deadline
    _out(_client().update_invoice(invoice_id, **fields))


@app.command("invoice-lines")
def invoice_lines(
    invoice_id: int = typer.Argument(..., help="Invoice ID"),
):
    """List lines of a customer invoice (with their IDs)."""
    _out(_client().get_invoice_lines(invoice_id))


@app.command("update-invoice-line")
def update_invoice_line(
    invoice_id: int = typer.Argument(..., help="Invoice ID"),
    line_id: int = typer.Argument(..., help="Line ID (use invoice-lines to list)"),
    quantity: Optional[float] = typer.Option(None, "--qty", "-q", help="New quantity"),
    unit_price: Optional[str] = typer.Option(None, "--price", "-p", help="New unit price HT (e.g. '700.00')"),
    label: Optional[str] = typer.Option(None, "--label", help="New label"),
):
    """Update a line on a draft invoice (qty, unit price, label)."""
    fields = {}
    if quantity is not None:
        fields["quantity"] = str(quantity)
    if unit_price is not None:
        fields["raw_currency_unit_price"] = unit_price
    if label is not None:
        fields["label"] = label
    if not fields:
        raise typer.BadParameter("Provide at least one of --qty, --price, --label")
    _out(_client().update_invoice_line(invoice_id, line_id, **fields))


@app.command("finalize-invoice")
def finalize_invoice(
    invoice_id: int = typer.Argument(..., help="Invoice ID to finalize"),
):
    """Finalize a draft invoice."""
    _out(_client().finalize_invoice(invoice_id))


@app.command("delete-invoice")
def delete_invoice(
    invoice_id: int = typer.Argument(..., help="Draft invoice ID to delete"),
):
    """Delete a draft customer invoice.

    Only drafts can be deleted. A finalized invoice cannot — it must be
    cancelled with a credit note.
    """
    _out(_client().delete_invoice(invoice_id))


@app.command("send-invoice")
def send_invoice(
    invoice_id: int = typer.Argument(..., help="Invoice ID to send by email"),
):
    """Send a finalized invoice to the customer by email."""
    _out(_client().send_invoice(invoice_id))


# --- Quotes ---


@app.command("create-quote")
def create_quote(
    customer_id: int = typer.Option(..., "--customer", "-c", help="Customer ID"),
    date: str = typer.Option(..., "--date", "-d", help="Quote date (YYYY-MM-DD)"),
    deadline: str = typer.Option(..., "--deadline", help="Validity deadline (YYYY-MM-DD)"),
    line: List[str] = typer.Option(..., "--line", "-l", help="Line: product_id:quantity[:unit_price]"),
    ref: Optional[str] = typer.Option(None, "--ref", help="External reference"),
):
    """Create a quote.

    Lines format: --line product_id:quantity[:unit_price]

    Product details (label, unit, vat_rate) are resolved automatically from the product_id.
    """
    client = _client()
    products = {p["id"]: p for p in client.list_products()}

    lines = []
    for l in line:
        parts = l.split(":")
        pid = int(parts[0])
        product = products.get(pid)
        if not product:
            raise typer.BadParameter(f"Product {pid} not found")
        entry = {
            "product_id": pid,
            "quantity": float(parts[1]),
            "label": product["label"],
            "raw_currency_unit_price": parts[2] if len(parts) >= 3 else product["price_before_tax"],
            "unit": product["unit"],
            "vat_rate": product["vat_rate"],
        }
        lines.append(entry)

    result = client.create_quote(
        customer_id=customer_id, date=date, deadline=deadline,
        lines=lines, external_reference=ref,
    )
    _out(result)
