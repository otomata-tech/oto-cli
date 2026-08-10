---
title: Zoho Desk — OAuth setup
type: how-to
description: >-
  Procédure pour obtenir les quatre secrets nécessaires à `oto zohodesk` : création d'une org
  Zoho Desk (plan free, récupération de `ZOHO_DESK_ORG_ID`), enregistrement d'un OAuth Self Client
  sur `api-console.zoho.com` (`ZOHO_DESK_CLIENT_ID` + `ZOHO_DESK_CLIENT_SECRET`), génération
  du `ZOHO_DESK_REFRESH_TOKEN` via échange `authorization_code` curl avec les scopes
  `Desk.tickets.ALL,Desk.contacts.READ,Desk.basic.READ,Desk.settings.READ`, et configuration
  dans `~/.otomata/secrets.env` avec gestion multi-datacenter (US/EU/IN/AU).
  Charger pour brancher le connecteur Zoho Desk sur un nouveau compte ou datacenter.
---

# Zoho Desk — OAuth setup

Steps to obtain the secrets needed by `oto zohodesk`.

## 1. Create a Zoho Desk org (free)

1. Go to https://www.zoho.com/desk/ and sign up. Free plan: 3 agents, unlimited tickets.
2. Note your data center: **US** (`.com`), **EU** (`.eu`), **IN** (`.in`), **AU** (`.com.au`). All URLs below must match.

## 2. Find your org ID

In Zoho Desk: **Setup → Developer Space → API → Organizations**. The number on screen is `ZOHO_DESK_ORG_ID`.

## 3. Register a Zoho OAuth client

Go to https://api-console.zoho.com/ (use `.eu` / `.in` if you're on those data centers).

- **Client Type**: *Self Client* (simplest — no redirect URI).
- **Client Name**: `oto-zohodesk` (free choice).
- **Client Domain** / **Authorized Redirect URI**: not needed for Self Client.

After creation you get **Client ID** and **Client Secret** → these are `ZOHO_DESK_CLIENT_ID` and `ZOHO_DESK_CLIENT_SECRET`.

## 4. Generate a refresh token

In the Self Client console, click **Generate Code**:

- **Scope** (paste this exact string):
  ```
  Desk.tickets.ALL,Desk.contacts.READ,Desk.basic.READ,Desk.settings.READ
  ```
- **Time duration**: 10 minutes is enough.
- **Scope description**: `oto desk integration` (free text).

You receive a **grant code** valid 10 min. Exchange it for a refresh token:

```bash
# Adjust accounts URL for your data center
ACCOUNTS_URL="https://accounts.zoho.com"   # or .eu / .in / .com.au

curl -s -X POST "$ACCOUNTS_URL/oauth/v2/token" \
  -d "grant_type=authorization_code" \
  -d "client_id=YOUR_CLIENT_ID" \
  -d "client_secret=YOUR_CLIENT_SECRET" \
  -d "code=THE_GRANT_CODE_FROM_CONSOLE"
```

Response contains `refresh_token` (long-lived) and `access_token` (1h). Keep `refresh_token` → that's `ZOHO_DESK_REFRESH_TOKEN`.

## 5. Store secrets

In `~/.otomata/secrets.env`:
```
ZOHO_DESK_CLIENT_ID=1000.xxxxxxxxx
ZOHO_DESK_CLIENT_SECRET=xxxxxxxx
ZOHO_DESK_REFRESH_TOKEN=1000.yyyyyyyyy.zzzzzzzz
ZOHO_DESK_ORG_ID=123456789
# Override only if not on US data center:
# ZOHO_DESK_API_DOMAIN=https://desk.zoho.eu
# ZOHO_DESK_ACCOUNTS_URL=https://accounts.zoho.eu
```

## 6. Sanity check

```bash
oto zohodesk departments
oto zohodesk tickets -n 5
```

If you get `INVALID_OAUTH` → scope mismatch. Re-generate the grant code with the full scope string above.

If you get `UNAUTHORIZED` (401) repeatedly → org ID is wrong, or refresh token is from another data center.

## Common pitfalls

- **Data center mismatch**: refresh tokens are bound to one data center. EU token cannot hit `.com` and vice-versa. Check `ZOHO_DESK_API_DOMAIN` and `ZOHO_DESK_ACCOUNTS_URL` consistency.
- **Self Client expiry**: the *grant code* is one-shot, 10 min. If the curl exchange fails, regenerate from the console.
- **Scope changes**: scopes are baked into the refresh token. Need a new scope? Regenerate the whole flow.
