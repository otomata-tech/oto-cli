---
title: Gmail OAuth Setup
type: how-to
description: >-
  Procédure pour configurer l'OAuth2 user flow Gmail (Desktop app, GCP consent screen External,
  mode Testing) : activation de l'API Gmail, création d'un OAuth Client ID, placement du JSON
  dans `~/.otomata/google-oauth-client.json`, premier lancement `otomata google auth` et gestion
  multi-compte via `-a <name>`. Inclut le tableau des fichiers générés (`google-oauth-token*.json`),
  les commandes Gmail disponibles (`gmail-list`, `gmail-send`, `gmail-draft`…) et un tableau
  de troubleshooting (`access_denied`, `Token expired`, `Multiple accounts`).
  Charger pour brancher Gmail OAuth sur une machine ou ajouter un compte supplémentaire.
---

# Gmail OAuth Setup

Gmail nécessite un **OAuth2 user flow** (pas un service account) car il accède aux données personnelles de l'utilisateur.

## Prérequis

Un projet Google Cloud existant (celui utilisé pour le service account, ou un nouveau).

## 1. Activer l'API Gmail

1. [Google Cloud Console](https://console.cloud.google.com) → votre projet
2. **APIs & Services** → **Library**
3. Chercher "Gmail API" → **Enable**

## 2. Configurer l'écran de consentement

Si pas déjà fait :

1. **APIs & Services** → **OAuth consent screen**
2. Type : **External**
3. Remplir le nom de l'app (ex: `otomata`)
4. **Test users** : ajouter votre adresse Gmail
5. Publier en mode **Testing** (suffisant pour usage personnel)

## 3. Créer un OAuth Client ID

1. **APIs & Services** → **Credentials**
2. **Create Credentials** → **OAuth client ID**
3. Type : **Desktop app**
4. Nom : `otomata-cli` (ou autre)
5. **Download JSON**

## 4. Configurer otomata

Placer le JSON téléchargé :

```bash
cp ~/Téléchargements/client_secret_*.json ~/.otomata/google-oauth-client.json
```

Alternative : mettre le contenu JSON dans `secrets.env` :

```bash
GOOGLE_OAUTH_CLIENT='{"installed":{"client_id":"...","client_secret":"..."}}'
```

## 5. Premier lancement

```bash
otomata google auth
```

Un browser s'ouvre pour le consentement OAuth. Accepter les permissions Gmail. Le token est sauvegardé automatiquement.

## Multi-compte

Pour connecter plusieurs comptes Google (ex: perso + pro) :

```bash
# Ajouter un compte nommé
otomata google auth gmail       # ouvre le consent → se connecter avec le compte voulu
otomata google auth work        # idem avec un autre compte

# Lister les comptes configurés
otomata google auth --list

# Utiliser un compte spécifique
otomata google gmail-list -a gmail -n 5
otomata google gmail-send -a work --to ... --subject ...
otomata google gmail-draft -a gmail --to ... --subject ... -f doc.pdf
```

Si un seul compte est configuré, `-a` est optionnel. Si plusieurs, il est obligatoire.

## Commandes Gmail

```bash
otomata google gmail-list [--query ...] [-n 10] [-a acct]    # Lister les messages
otomata google gmail-search <QUERY> [-n 10] [-a acct]        # Rechercher
otomata google gmail-get <MESSAGE_ID> [-a acct]              # Lire un message
otomata google gmail-attachments <ID> [-o dir] [-a acct]     # Télécharger les PJ
otomata google gmail-draft --to ... --subject ... [-f ...]   # Créer un brouillon
otomata google gmail-send --to ... --subject ... [-f ...]    # Envoyer
```

Options communes à `gmail-send` et `gmail-draft` :
- `--to`, `--subject`, `--body` : destinataire, objet, corps
- `--cc`, `--bcc` : copies
- `-f / --attach` : pièces jointes (répétable)
- `-a / --account` : compte Google

## Fichiers générés

| Fichier | Contenu |
|---------|---------|
| `~/.otomata/google-oauth-client.json` | Client ID + secret (à poser manuellement) |
| `~/.otomata/google-oauth-token.json` | Token du compte "default" |
| `~/.otomata/google-oauth-token-{name}.json` | Token d'un compte nommé |

## Mode librairie

```python
from otomata.tools.google.gmail.lib.gmail_client import GmailClient

# CLI : résout les credentials automatiquement
client = GmailClient()

# Compte spécifique
client = GmailClient(account="gmail")

# Librairie : l'appelant injecte ses credentials
from google.oauth2.credentials import Credentials
creds = Credentials(token="...", refresh_token="...", ...)
client = GmailClient(credentials=creds)
```

## Troubleshooting

| Erreur | Cause | Solution |
|--------|-------|----------|
| `OAuth client config not found` | JSON client absent | Placer le fichier dans `~/.otomata/` |
| `Multiple Google accounts configured` | Plusieurs comptes, pas de `-a` | Ajouter `--account <name>` |
| `Access blocked` | Mauvais compte Google | Vérifier que le bon compte est connecté dans le browser |
| `access_denied` | User pas dans les test users | Ajouter l'email dans l'écran de consentement GCP |
| `Token expired` | Refresh token invalide | Relancer `otomata google auth <name>` |
