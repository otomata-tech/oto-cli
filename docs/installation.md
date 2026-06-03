# Installation

`oto` is a CLI toolkit. Install it once with `pipx`, then every connector is a
sub-command (`oto google`, `oto linkedin`, …). The CLI is self-documenting via
`--help`, so your AI agent (Claude Code, Cursor, …) discovers how to drive it.

## Prerequisites

- **Python 3.10+**
- **pipx** (recommended) — isolates the CLI in its own venv
- **Google Chrome** — required for the `browser` connectors (LinkedIn,
  Crunchbase, Indeed, …). `oto` drives your installed Chrome. For LinkedIn it
  **must** be real Google Chrome, not Chromium — LinkedIn flags the Chromium
  fingerprint. If Chrome is absent, install it (don't `patchright install chromium`).

## Install pipx

```bash
# Debian/Ubuntu
sudo apt install pipx && pipx ensurepath
# Fedora
sudo dnf install pipx && pipx ensurepath
# macOS
brew install pipx && pipx ensurepath
# Windows (PowerShell)
pip install --user pipx && python -m pipx ensurepath
```

Restart your terminal after `ensurepath`.

## Install oto

```bash
# Base CLI (API connectors that only need HTTP)
pipx install oto-cli

# With the browser connectors (LinkedIn, Crunchbase, …)
pipx install "oto-cli[browser]"

# With Google (Gmail, Drive, Sheets, …)
pipx install "oto-cli[google,browser]"

# Everything
pipx install "oto-cli[all]"
```

Verify:

```bash
oto --help
```

## LinkedIn setup

LinkedIn no longer accepts an injected `li_at` cookie (its TLS fingerprinting
rejects a session that wasn't created by the same browser). The reliable method
is a **persistent browser profile** you log into once.

```bash
# One-time: opens a real Chrome window — log in by hand, then CLOSE the window.
oto linkedin login
```

> `login` opens a visible (headed) browser, so it needs a graphical session
> (a desktop, or VNC on a headless server). Log in fully (including 2FA), confirm
> you land on your feed, then close the window — the session is saved.

The session lives in a **default profile** (`~/.config/browser/linkedin`) that
every LinkedIn command reuses automatically — no flag needed:

```bash
oto linkedin search-people "head of finance"
oto linkedin connect "https://www.linkedin.com/in/john-doe/" --note "Bonjour …"
```

`--profile <dir>` is only for juggling **multiple LinkedIn accounts**. No API key
or secret is required for LinkedIn — the logged-in profile is the credential.
Run `oto browser linkedin --help` for the full command set.

## Configuration & secrets

Connectors that hit third-party APIs (Serper, Hunter, Attio, Pennylane, …) need
credentials. `oto` resolves a secret in this order: **environment variable →
configured provider → default**. The simplest provider is a flat file:

```bash
mkdir -p ~/.otomata
printf 'SERPER_API_KEY=xxx\nHUNTER_API_KEY=yyy\n' >> ~/.otomata/secrets.env
oto config provider secrets file   # use the file provider
oto config                         # show providers + which secrets are set
```

LinkedIn-via-profile needs none of this.

## Claude Code

The CLI is self-documenting (`oto --help`, `oto <namespace> --help`). For Claude
Code, install the **`oto` plugin** — it bundles a universal skill + the Oto MCP
connector:

```bash
claude plugin marketplace add otomata-tech/oto-plugin
claude plugin install oto@otomata-oto
```

## Update / uninstall

```bash
pipx upgrade oto-cli
pipx uninstall oto-cli
```

## Troubleshooting

### `oto: command not found`
Run `pipx ensurepath` and restart the terminal.

### Browser: no Chrome found
Install **Google Chrome**. `oto` drives it via the `chrome` channel. For LinkedIn
do not substitute Chromium (`patchright install chromium`) — LinkedIn detects and
flags the Chromium fingerprint. Real Chrome is the requirement.

### LinkedIn: "session expired — cookie li_at is no longer valid"
The profile's session lapsed. Re-run the login:

```bash
oto linkedin login
```

### Python version error
Ensure Python 3.10+: `python3 --version`.
