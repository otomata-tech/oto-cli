# Concepts

## Why oto exists

LLMs are good at using CLI tools — they were trained on billions of terminal interactions. For popular tools (`gh`, `aws`, `gcloud`, `docker`), the LLM already knows the commands.

But most SaaS products don't have a CLI. When an AI agent needs to interact with Notion, Pennylane, LinkedIn, or SIRENE, it has two options:
1. **MCP** — a protocol that puts the full API schema in the LLM's context window (expensive: 4-32x more tokens, 72% reliability)
2. **CLI** — a command-line tool the LLM calls via Bash (cheap: ~80 tokens, 100% reliability)

**oto is option 2.** One CLI, many connectors, self-documenting via `--help`.

## Architecture

### Auto-discovery

`cli.py` scans `oto/commands/` at startup. Any `.py` file that exports `app = typer.Typer()` becomes a sub-command:

```
commands/google.py   → oto google ...
commands/search.py   → oto search ...
commands/stripe.py   → oto stripe ...   (you add this)
```

No registry, no config. Drop a file, it works.

### Connector anatomy

A connector is 2 parts:

```
commands/myservice.py          # CLI layer (Typer commands)
tools/myservice/client.py      # API client (business logic)
```

**Commands** define the CLI surface — arguments, options, help text. They import the tool client lazily (inside the function body) so the CLI starts fast. Clear `--help` strings are how agents discover the connector.

**Tool clients** talk to the API. They use `get_secret()` for auth and return plain Python dicts/lists.

### Connector types

There are 3 types of connectors. They differ in how the tool client talks to the service, but the CLI contract is always the same: JSON on stdout, lazy imports, `get_secret()` for auth.

**API connectors** — call a REST API via `requests`. Most connectors are this type. Auth, rate limiting, and pagination depend on the provider — each client handles it as the API requires.

```
tools/serper/client.py     → requests + X-API-KEY header
tools/notion/client.py     → requests + Bearer token + cursor pagination
tools/pennylane/client.py  → requests + Bearer token + retry on 429
tools/folk/client.py       → requests + Bearer token + Retry-After header
tools/kaspr/client.py      → requests + Bearer token
tools/hunter/client.py     → requests + query param api_key
```

**Browser connectors** — automate a real browser (via [o-browser](https://github.com/AntMusic/o-browser)) for sites that don't have an API, or where the API is too limited. They inherit from `BrowserClient`, are async, and use context managers. Commands wrap them in `asyncio.run()`.

```
tools/browser/linkedin.py   → cookie auth, file-based rate limiting
tools/browser/crunchbase.py → cookie auth, session persistence
tools/browser/pappers.py    → no auth, Cloudflare handling
tools/browser/indeed.py     → no auth, multi-country
tools/browser/g2.py         → no auth, review scraping
```

Require the `browser` extra: `pip install oto-cli[browser]`.

**SDK connectors** — use an official SDK instead of raw HTTP. Currently only Google Workspace, which uses `google-api-python-client` with OAuth2 tokens stored in `~/.otomata/google-oauth-token-{name}.json`.

```
tools/google/gmail/      → google-api-python-client (OAuth2)
tools/google/drive/      → google-api-python-client (OAuth2)
tools/google/docs/       → google-api-python-client (OAuth2)
tools/google/calendar/   → google-api-python-client (OAuth2)
```

Require the `google` extra: `pip install oto-cli[google]`.

**There's no base class.** Each client implements what its API requires — the only shared contract is on the CLI side (JSON output, lazy imports, `get_secret()`).

### Secrets

3-tier resolution — first found wins:

| Priority | Location | Scope |
|----------|----------|-------|
| 1 | Environment variable | Session |
| 2 | `.otomata/secrets.env` (project dir, walks up 4 levels) | Project |
| 3 | `~/.otomata/secrets.env` | User |

```bash
# Setup
mkdir -p ~/.otomata
echo "SERPER_API_KEY=xxx" >> ~/.otomata/secrets.env

# Check
oto config
```

In code, `get_secret("SERPER_API_KEY")` resolves through all 3 tiers. If the key is missing, it raises a `ValueError` with instructions — caught by `main()` for a clean error message.

### Output contract

Every command prints JSON to stdout:

```bash
oto search web "AI agents" | jq '.[0].title'
oto sirene search "fintech" | jq '.[] | .siren'
```

Errors go to stderr. Exit code 0 = success, 1 = error. This makes oto composable with standard Unix tools.

### Claude Code

The CLI ships no skills. Agents discover connectors via `--help`; for Claude Code,
the **`oto` plugin** (`otomata-tech/oto-plugin`) provides a single universal skill
(entry-point doctrine) plus the Oto MCP connector.
