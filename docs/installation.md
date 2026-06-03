# Installation

`oto` is a CLI toolkit. Install it once with `pipx`, then every connector is a
sub-command (`oto google`, `oto linkedin`, …). Each connector also ships a
`SKILL.md` so your AI agent (Claude Code, Cursor, …) knows how to drive it.

## Prerequisites

- **Python 3.10+**
- **pipx** (recommended) — isolates the CLI in its own venv
- **Google Chrome** — required only for the `browser` connectors (LinkedIn,
  Crunchbase, Indeed, …). `oto` drives your installed Chrome; if Chrome is
  absent see [Troubleshooting](#browser-no-chromechromium-found).

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
oto linkedin login --profile ~/.config/browser/linkedin
```

> `login` opens a visible (headed) browser, so it needs a graphical session
> (a desktop, or VNC on a headless server). Log in fully (including 2FA), confirm
> you land on your feed, then close the window — the session is saved in the
> profile directory.

Afterwards, pass that profile to every LinkedIn command:

```bash
oto linkedin search-people "head of finance" --profile ~/.config/browser/linkedin
oto linkedin connect "https://www.linkedin.com/in/john-doe/" --note "Bonjour …" \
  --profile ~/.config/browser/linkedin
```

No API key or secret is required for LinkedIn when you use a logged-in profile.
See the `oto-browser` skill for the full command set (`oto skills show oto-browser`).

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

## Skills (for AI agents)

Each connector's `SKILL.md` is an instruction manual for your agent. Symlink them
into Claude Code:

```bash
oto skills enable --all      # or: oto skills enable oto-browser
oto skills list
```

## Update / uninstall

```bash
pipx upgrade oto-cli
pipx uninstall oto-cli
```

## Troubleshooting

### `oto: command not found`
Run `pipx ensurepath` and restart the terminal.

### Browser: no Chrome/Chromium found
`oto` prefers your installed Google Chrome. If you don't have Chrome, install a
Chromium for Patchright inside the CLI's venv:

```bash
~/.local/share/pipx/venvs/oto-cli/bin/patchright install chromium
```

(On macOS/Windows the path under `pipx environment --value PIPX_LOCAL_VENVS` is
the equivalent.)

### LinkedIn: "session expired — cookie li_at is no longer valid"
The profile's session lapsed. Re-run the login:

```bash
oto linkedin login --profile ~/.config/browser/linkedin
```

### Python version error
Ensure Python 3.10+: `python3 --version`.
