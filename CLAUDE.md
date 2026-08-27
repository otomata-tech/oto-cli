# oto-cli

**Façade CLI** d'Oto — commandes Typer `oto <cmd>` au-dessus de la lib **oto-core**.

Repo: `otomata-tech/oto-cli` (public). Command: `oto`. Dépend d'**oto-core** (les clients connecteurs `oto.tools` + `oto.config`, namespace `oto` — split 2026-06-11, otomata#13).

⚠️ **Positionnement (2026-06) : la CLI n'est plus le produit principal.** Le produit central est **oto-mcp** (serveur MCP déployable SaaS/on-premise). La CLI est **basse priorité**, surtout utile comme **fallback local pour LinkedIn browser** (qui ne marche qu'en local). Tout est open source.

## Philosophy

- **Façade mince** : les clients vivent dans **oto-core** ; oto-cli n'a que `cli.py` (discovery) + `commands/` (1 fichier = 1 sous-commande Typer).
- **For AI agents** : JSON on stdout, errors on stderr, composable with pipes.
- **Local-first** : exécution locale, secrets résolus localement (env → SOPS). Pour le serveur/multi-user/chiffré, c'est oto-mcp.

## Stack

- Python 3.10+, Typer (CLI), setuptools (namespace package `oto`, ex-hatchling).
- **Dépend d'oto-core** (clients `oto.tools` + `oto.config`/secrets) + typer.
- Extras re-exportés d'oto-core : `google`, `browser`, `vivatech`, `anthropic`, `stock`, `all`.

## Architecture

```
oto/
├── oto/
│   ├── cli.py                  # Dynamic command discovery + main() (+ entry-point oto.commands)
│   ├── commands/               # 1 file = 1 sub-command Typer (auto-discovered) ; config.py = oto.config dans oto-core
│   │   ├── google.py           # drive, docs, sheets, slides, gmail, calendar, auth
│   │   ├── notion.py           # search, page, database
│   │   ├── browser.py          # linkedin, crunchbase, pappers, indeed, g2, google, sncf, vivatech
│   │   ├── reddit.py           # Reddit JSON API (subreddit, search, post)
│   │   ├── fr.py               # données entreprise FR (fr_*) : recherche, bilans INPI, BODACC + sirene stock
│   │   ├── dvf.py              # valeurs foncières (immobilier) : stats/comparables €/m² par commune ou adresse
│   │   ├── culture.py          # Min. Culture open data (Opendatasoft) — sub-namespace `spectacle` (LES)
│   │   ├── search.py           # facade: dispatches to serper or browser via config
│   │   ├── serper.py           # direct Serper API (web, news, scrape, suggestions)
│   │   ├── enrichment.py       # kaspr, hunter, lemlist
│   │   ├── pennylane.py        # accounting
│   │   ├── gocardless.py       # GoCardless direct-debit (read-only; MCP `gocardless_*` masqué par défaut)
│   │   ├── anthropic.py        # usage, cost, summary
│   │   ├── folk.py             # Folk CRM
│   │   ├── zoho.py             # Zoho CRM
│   │   ├── zohodesk.py         # Zoho Desk (tickets/support)
│   │   ├── company.py          # SIREN lookup multi-source
│   │   ├── whatsapp.py         # WhatsApp messaging
│   │   ├── slack.py            # Slack — send/read/list-channels/dm (bot+user tokens)
│   │   ├── audio.py            # audio recording, transcription
│   │   ├── gemini.py           # Gemini image generation (gemini-3-pro-image)
│   │   ├── openai.py           # OpenAI image generation (gpt-image-2)
│   │   ├── pdf.py              # markdown → PDF via pandoc + weasyprint (bundled template)
│   │   ├── data.py             # Datastore (per-user Google Sheets via mcp.oto.ninja, OTO_API_KEY)
│   │   ├── ninja.py            # façade mcp.oto.ninja: secrets per-user (LinkedIn/Crunchbase/API keys), OTO_API_KEY
│   │   └── config.py           # config & secrets management
│   └── (PLUS de tools/ ni config.py ici — split 2026-06-11) :
│        les clients API + la résolution de secrets vivent dans **oto-core**
│        (namespace `oto.tools.*` + `oto.config`). Les commands/ les importent.
└── pyproject.toml              # entry point oto = "oto.cli:main" ; dépend d'oto-core
```

Chaque `commands/*.py` importe son client depuis `oto.tools.<svc>` (fourni par oto-core, namespace partagé).

Pour les agents Claude Code, le guidage vit dans le **plugin `oto`** (`otomata-tech/oto-plugin`) : un skill universel + le connecteur MCP. La CLI elle-même est auto-documentée via `--help` ; elle ne ship plus de SKILL.md.

## Adding a new connector

A **core** connector = 2 fichiers, dans **deux repos** depuis le split (otomata#13) :

1. **client** — `oto/tools/myservice/` dans **oto-core** (la lib, public).
2. **command** — `oto/commands/myservice.py` dans **oto-cli** (façade Typer, importe `oto.tools.myservice`).

(Côté serveur, le wrapper `tools/myservice.py` vit dans **oto-mcp** et importe aussi le client d'oto-core.)

⚠️ Connecteur **custom/client-sensible** (auth reverse-engineerée, infra client,
endpoint confidentiel) → **jamais dans ces repos publics** : package privé + bridge
(connecteur remote, ADR 0003). Ex. un bridge back-office client (repo privé).

See `docs/create-connector.md` for details.

## Command pattern

Each `commands/*.py` file:
```python
import typer
import json
from typing import Optional

app = typer.Typer(help="My service description")

@app.command("do-thing")
def do_thing(
    query: str = typer.Argument(..., help="What to do"),
    max_results: int = typer.Option(20, "--max-results", "-n"),
):
    """Do a thing."""
    from oto.tools.myservice.client import MyServiceClient
    client = MyServiceClient()
    results = client.do_thing(query=query, max_results=max_results)
    print(json.dumps(results, indent=2))
```

Key rules:
- `app = typer.Typer()` exported, auto-discovered by `cli.py`
- Tool imports **inside functions** (lazy) so the CLI stays fast
- Always `print(json.dumps(..., indent=2))` for output
- Missing secrets raise `ValueError`, caught by `main()` → clean stderr message

## Secrets & Config

Provider-based resolution (`oto config provider secrets <sops|file|scaleway>`) :
1. Env vars (always, highest priority)
2. Configured provider:
   - **sops** (default) — SOPS+age. `sops_dir` (multi-file, walks `*.yaml`
     recursively, merges flat with warning on duplicate keys) or `sops_file`
     (mono-file legacy). Default dir: `~/.otomata/secrets/`.
   - **file** — `.otomata/secrets.env` project → user
   - **scaleway** — Secret Manager
3. Default value

**Mode serveur** : `OTO_CONFIG_DISABLE_SOPS=1` → `get_secret` résout l'env du
process UNIQUEMENT (ni SOPS ni `secrets.env`), `require_secret` échoue fort.
Posé par l'unit oto-mcp (les credentials serveur vivent dans son coffre DB et
sont injectés dans les clients — jamais d'auto-résolution, cf. oto-mcp#12).

```bash
oto config                        # show providers + secrets status
oto config provider secrets sops  # switch to SOPS (default)
oto config provider search serper # switch search to serper (default) or browser
oto config secrets-push           # upload local secrets.env → Scaleway
oto config secrets-pull           # download Scaleway → local secrets.env
```

## Search

Facade `oto search` dispatches to backend based on `search_provider` config:

| Command | Backend | Notes |
|---------|---------|-------|
| `oto search web -q "..."` | config-based | serper (default) or browser |
| `oto search news -q "..."` | serper only | no browser equivalent |
| `oto serper web/news/scrape/suggestions` | Serper API | direct access |
| `oto browser google -q "..."` | Chrome | needs `--profile` to avoid bot detection |

## Google OAuth

Tokens stored in `~/.otomata/google-oauth-token-{name}.json`.

Add an account: `oto google auth <name>` — opens browser for OAuth flow.
List accounts: `oto google auth --list`.

## Claude Code

La CLI ne ship plus de skills. Le guidage agent vit dans le **plugin `oto`** (`otomata-tech/oto-plugin`) : un skill universel (doctrine d'amorçage + « découvre via `oto --help` ») + le connecteur MCP auto-configuré. Les doctrines non-évidentes par outil vont dans les help strings des commandes (`--help`), pas dans un skill.

## Deploy

Push main déclenche `.github/workflows/deploy.yml` qui SSH la **box dédiée `151.115.148.128`** (plus tuls.me), `git reset --hard origin/main` + **`pip install -e .`** (réinstall façade) + `systemctl restart oto-mcp` dans `/opt/deploy/oto-cli.sh`. NB : oto-mcp importe les clients depuis **oto-core**, pas oto-cli — un changement de *client* se propage via oto-core ; oto-cli ne propage que les *commandes* CLI.

## Release PyPI (rare)

Pour publier sur PyPI (autres utilisateurs hors infra Otomata). PyPI token in SOPS (`PYPI_TOKEN`).

`hatch build/publish` ne marche pas sur cette machine (pas de `python`, hatchling non bootstrappé).
Passer par `build` + `twine` dans un venv dédié, et builder depuis `git archive HEAD` pour exclure
le WIP non commité de la release.

```bash
# Bump version dans oto/__init__.py, commit + push, puis :
python3 -m venv /tmp/buildenv && /tmp/buildenv/bin/pip install build twine
rm -rf /tmp/rel && git archive HEAD | tar -x -C /tmp/rel && cd /tmp/rel
/tmp/buildenv/bin/python -m build
TWINE_USERNAME=__token__ \
TWINE_PASSWORD="$(sops --decrypt --extract '["PYPI_TOKEN"]' ~/.otomata/secrets/secrets.yaml)" \
  /tmp/buildenv/bin/twine upload dist/*
gh release create vX.Y.Z --generate-notes dist/*
```

## Docs

Detailed docs in `docs/`:
- `concepts.md` — architecture, connector types (API/browser/SDK), secrets, output contract
- `create-connector.md` — step-by-step guide to add a connector (command + client)
- `installation.md` — setup and dependencies
- `gmail-oauth-setup.md` — OAuth multi-account setup for Gmail
- `gmail.md` — body format flags (markdown / html / plain) for send/reply/draft
- `google-docs.md` — markdown import via Drive HTML importer + .otomata CSS convention
- `google-service-account-setup.md` — Google service account setup
