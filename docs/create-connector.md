# Create a connector

A connector is a pair: **command** + **tool client**. Write clear `--help`
strings — that's how agents (and the `oto` plugin's universal skill) discover it.

## 1. Command file

Create `oto/commands/myservice.py`:

```python
import typer
from typing import Optional

app = typer.Typer(help="My service — short description")


@app.command("list")
def list_items(
    query: str = typer.Argument(..., help="Search query"),
    max_results: int = typer.Option(20, "--max-results", "-n"),
):
    """List items from MyService."""
    import json
    from oto.tools.myservice.client import MyServiceClient

    client = MyServiceClient()
    results = client.list(query=query, max_results=max_results)
    print(json.dumps(results, indent=2))
```

Rules:
- Export `app = typer.Typer(help="...")` — auto-discovered by cli.py
- Import tool clients **inside functions** (lazy) — keeps CLI startup fast
- Output: always `print(json.dumps(data, indent=2))`
- For sub-groups, use `app.add_typer(sub_app, name="sub")` (see `enrichment.py`)

## 2. Tool client

There are 3 types of clients. Pick the one that matches your service. There's no base class — just implement what the API requires.

### API client (most common)

For services with a REST API. Sync, uses `requests`.

```python
# oto/tools/myservice/client.py
from oto.config import get_secret


class MyServiceClient:
    def __init__(self):
        self.api_key = get_secret("MYSERVICE_API_KEY")
        self.base_url = "https://api.myservice.com/v1"

    def list(self, query: str, max_results: int = 20) -> list[dict]:
        import requests

        resp = requests.get(
            f"{self.base_url}/items",
            headers={"Authorization": f"Bearer {self.api_key}"},
            params={"q": query, "limit": max_results},
        )
        resp.raise_for_status()
        return resp.json()["items"]
```

Auth, pagination, and rate limiting depend on the API — handle them as the provider documents. See `tools/pennylane/client.py` (retry on 429), `tools/folk/client.py` (cursor pagination), `tools/notion/` (caching) for real examples.

### Browser client

For services without an API. Async, inherits from `o-browser.BrowserClient`.

```python
# oto/tools/browser/mysite.py
from o_browser import BrowserClient


class MySiteClient(BrowserClient):
    async def get_page(self, url: str) -> dict:
        await self.goto(url)
        title = await self.text_content("h1")
        return {"url": url, "title": title}
```

The command wraps it in `asyncio.run()`:

```python
# oto/commands/mysite.py
@app.command("get")
def get_page(url: str = typer.Argument(...)):
    """Get page data."""
    import asyncio, json
    from oto.tools.browser.mysite import MySiteClient

    async def run():
        async with MySiteClient(headless=True) as client:
            return await client.get_page(url)

    print(json.dumps(asyncio.run(run()), indent=2))
```

Requires `pip install oto-cli[browser]`. See `tools/browser/indeed.py` for a simple example.

### SDK client

For services with an official Python SDK. Use the SDK directly.

```python
# oto/tools/myservice/client.py
class MyServiceClient:
    def __init__(self):
        from some_sdk import Client
        self.client = Client(api_key=get_secret("MYSERVICE_API_KEY"))

    def list(self, query: str) -> list[dict]:
        return self.client.items.list(query=query)
```

Add the SDK to `pyproject.toml` optional dependencies. See `tools/google/` for the Google Workspace implementation.

`get_secret()` raises a `ValueError` with setup instructions if the key is missing — caught by `main()` in cli.py.

## 3. Optional: add to pyproject.toml

If your connector needs extra Python dependencies, add an optional group:

```toml
[project.optional-dependencies]
myservice = ["some-sdk>=1.0.0"]
```

If it only needs `requests` (included in base install), skip this step.

## Testing

```bash
# Verify it appears in help
oto --help

# Verify subcommands
oto myservice --help

# Run a command
oto myservice list "test"
```
