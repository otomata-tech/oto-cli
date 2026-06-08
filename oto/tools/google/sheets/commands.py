"""`oto google sheets` command surface."""

import json

import typer
from typing import Optional

app = typer.Typer(help="Google Sheets tools (create, info, read, write, append)")

@app.command("create")
def sheets_create(
    title: str = typer.Argument(..., help="Spreadsheet title"),
    csv_path: Optional[str] = typer.Option(None, "--csv", "-c", help="CSV file to import"),
    account: Optional[str] = typer.Option(None, "--account", "-a", help="Google account name"),
):
    """Create a new Google Sheets spreadsheet, optionally importing a CSV."""
    from oto.tools.google.sheets.lib.sheets_client import SheetsClient

    client = SheetsClient(account=account)
    result = client.create(title)
    if csv_path:
        client.write_csv(result['id'], csv_path)
        result['imported'] = csv_path
    print(json.dumps(result, indent=2, ensure_ascii=False))

@app.command("info")
def sheets_info(
    spreadsheet_id: str = typer.Argument(..., help="Google Sheets spreadsheet ID"),
    account: Optional[str] = typer.Option(None, "--account", "-a", help="Google account name"),
):
    """Get spreadsheet metadata (title, sheet names, dimensions)."""
    from oto.tools.google.sheets.lib.sheets_client import SheetsClient

    client = SheetsClient(account=account)
    meta = client.get_metadata(spreadsheet_id)
    print(json.dumps(meta, indent=2, ensure_ascii=False))

@app.command("read")
def sheets_read(
    spreadsheet_id: str = typer.Argument(..., help="Google Sheets spreadsheet ID"),
    range: str = typer.Argument("A:ZZ", help="Cell range (e.g. 'Sheet1!A1:D10', 'A:ZZ')"),
    format: str = typer.Option("csv", "--format", "-f", help="Output format: csv or json"),
    account: Optional[str] = typer.Option(None, "--account", "-a", help="Google account name"),
):
    """Read data from a Google Sheets spreadsheet."""
    from oto.tools.google.sheets.lib.sheets_client import SheetsClient

    client = SheetsClient(account=account)

    if format == "csv":
        print(client.read_csv(spreadsheet_id, range), end="")
    else:
        rows = client.read(spreadsheet_id, range)
        print(json.dumps({"rows": len(rows), "data": rows}, indent=2, ensure_ascii=False))

@app.command("write")
def sheets_write(
    spreadsheet_id: str = typer.Argument(..., help="Google Sheets spreadsheet ID"),
    csv_path: str = typer.Argument(..., help="Path to CSV file to write"),
    sheet: Optional[str] = typer.Option(None, "--sheet", "-s", help="Target sheet name"),
    account: Optional[str] = typer.Option(None, "--account", "-a", help="Google account name"),
):
    """Write a CSV file to a Google Sheets spreadsheet (overwrites sheet)."""
    from oto.tools.google.sheets.lib.sheets_client import SheetsClient

    client = SheetsClient(account=account)
    result = client.write_csv(spreadsheet_id, csv_path, sheet_name=sheet)
    print(json.dumps(result, indent=2, ensure_ascii=False))

@app.command("append")
def sheets_append(
    spreadsheet_id: str = typer.Argument(..., help="Google Sheets spreadsheet ID"),
    csv_path: str = typer.Argument(..., help="Path to CSV file with rows to append"),
    range: str = typer.Option("A:ZZ", "--range", "-r", help="Range to append to"),
    account: Optional[str] = typer.Option(None, "--account", "-a", help="Google account name"),
):
    """Append rows from a CSV file to a Google Sheets spreadsheet."""
    from oto.tools.google.sheets.lib.sheets_client import SheetsClient
    import csv as csv_mod

    client = SheetsClient(account=account)
    with open(csv_path, 'r', encoding='utf-8') as f:
        values = list(csv_mod.reader(f))
    result = client.append(spreadsheet_id, range, values)
    print(json.dumps(result, indent=2, ensure_ascii=False))
