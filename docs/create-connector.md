---
title: Create a connector
type: how-to
description: >-
  Guide étape par étape pour ajouter un connecteur oto : décision core vs custom/privé
  (entry-point `oto.commands` pour les packages privés, jamais dans le repo public pour
  les endpoints confidentiels), puis création du fichier `oto/commands/myservice.py` (Typer,
  imports lazy, JSON stdout) et du client `oto/tools/myservice/client.py` (API `requests`,
  Browser `BrowserClient` async, ou SDK). Référence un package bridge privé
  comme exemple d'entry-point privé et l'issue otomata-tech/oto-cli#9.
  Charger dès qu'un agent ou développeur doit créer ou plugger un nouveau connecteur.
adr: ["0003"]
---

# Create a connector

A connector is a pair: **command** + **tool client**. Write clear `--help`
strings — that's how agents (and the `oto` plugin's universal skill) discover it.

## Core vs custom/client connector — where does it live?

`oto-cli` is a **public** repo, published to **public PyPI** (source readable by
anyone). Decide before writing a line of code:

- **Core connector** — generic / open-data / mainstream SaaS (fr, dvf, culture,
  serper, reddit, folk…). Lives **in this repo** (`oto/commands/` +
  `oto/tools/`), discovered by the filesystem glob in `cli.py`. PR welcome.
- **Custom / client-specific connector** — anything that exposes a client's
  internals, a private workflow, a reverse-engineered auth, or a confidential
  endpoint. **Never in this repo.** It must be a **separate package** (usually
  private) that plugs into the CLI via the `oto.commands` **entry-point group**.

The entry-point path means you never patch the public `cli.py` to add a private
command. Install the private package in the same environment as `oto-cli` and
`oto <name>` appears automatically. This is symmetric to the `o_browser.sites`
entry-point group used for site adapters.

### Writing a custom connector as an entry-point package

A standalone package with its own top-level module (e.g. `oto_mm`, **not**
`oto.commands.*` — that namespace belongs to the public core):

```toml
# pyproject.toml of the private package
[project]
name = "oto-myclient"
dependencies = ["oto-cli>=1.1.0", "requests>=2.28", "typer>=0.12"]

[project.entry-points."oto.commands"]
myclient = "oto_myclient.commands:app"   # name = the `oto <name>` sub-command
```

```python
# oto_myclient/commands.py
import typer
app = typer.Typer(help="My client — short description")
# ... @app.command(...) as usual
```

Install: `pipx inject oto-cli oto-myclient@git+ssh://...` (or `pip install` in a
venv). Reference: a private bridge package and issue
otomata-tech/oto-cli#9.

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
