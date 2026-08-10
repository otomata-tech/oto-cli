---
title: Google Service Account Setup
type: how-to
description: >-
  Procédure complète pour créer un Service Account Google Cloud (GCP), activer les APIs
  Drive/Docs/Sheets/Slides, générer une clé JSON, partager les ressources Drive avec le
  compte de service, et configurer le credential dans otomata via variable d'environnement
  `GOOGLE_SERVICE_ACCOUNT`, `.env.local`, ou `~/.config/otomata/google_service_account`.
  Inclut un tableau de troubleshooting et un pattern d'isolation par équipe (Shared Drive dédié).
  Charger quand il faut mettre en place l'accès Google Workspace via service account.
---

# Google Service Account Setup

This guide explains how to create a Google Service Account from scratch to use with otomata tools.

## 1. Create a Google Cloud Project

1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Click the project dropdown (top left) → "New Project"
3. Enter a project name (e.g., `my-otomata-project`)
4. Click "Create"

## 2. Enable Required APIs

1. In your project, go to **APIs & Services** → **Library**
2. Search and enable each of these APIs:
   - Google Drive API
   - Google Docs API
   - Google Sheets API
   - Google Slides API

## 3. Create a Service Account

1. Go to **IAM & Admin** → **Service Accounts**
2. Click **Create Service Account**
3. Fill in:
   - Name: `otomata-drive` (or any name)
   - ID: auto-generated (e.g., `otomata-drive`)
4. Click **Create and Continue**
5. Skip the optional permissions steps → Click **Done**

This creates a service account with an email like:
```
otomata-drive@my-otomata-project.iam.gserviceaccount.com
```

## 4. Generate a JSON Key

1. Click on the service account you just created
2. Go to the **Keys** tab
3. Click **Add Key** → **Create new key**
4. Select **JSON** → Click **Create**
5. A `.json` file downloads automatically - **keep it safe!**

The JSON file contains:
```json
{
  "type": "service_account",
  "project_id": "my-otomata-project",
  "private_key_id": "abc123...",
  "private_key": "-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----\n",
  "client_email": "otomata-drive@my-otomata-project.iam.gserviceaccount.com",
  "client_id": "123456789",
  "auth_uri": "https://accounts.google.com/o/oauth2/auth",
  "token_uri": "https://oauth2.googleapis.com/token",
  ...
}
```

## 5. Share Google Drive Resources

**Important:** A service account has no access to any files by default. You must explicitly share resources with it.

### Share a file or folder

1. In Google Drive, right-click the file/folder
2. Click **Share**
3. Add the service account email (e.g., `otomata-drive@my-otomata-project.iam.gserviceaccount.com`)
4. Choose permission level (Viewer, Editor, etc.)
5. Click **Send**

### Share a Shared Drive

1. Open the Shared Drive
2. Click the dropdown arrow next to the drive name → **Manage members**
3. Add the service account email
4. Choose role (Viewer, Contributor, Content Manager, or Manager)
5. Click **Send**

## 6. Configure otomata

### Option A: Environment variable (recommended for CI/CD)

```bash
export GOOGLE_SERVICE_ACCOUNT='{"type":"service_account","project_id":"...",...}'
```

### Option B: Project `.env.local` file (recommended for local dev)

1. Compact the JSON to a single line (remove newlines)
2. Add to your project's `.env.local`:

```bash
GOOGLE_SERVICE_ACCOUNT='{"type":"service_account","project_id":"my-otomata-project","private_key_id":"abc123","private_key":"-----BEGIN PRIVATE KEY-----\nMIIE...\n-----END PRIVATE KEY-----\n","client_email":"otomata-drive@my-otomata-project.iam.gserviceaccount.com",...}'
```

**Tip:** Use `jq -c` to compact JSON:
```bash
cat your-key-file.json | jq -c
```

### Option C: User config (for personal machine)

Save the JSON to:
```
~/.config/otomata/google_service_account
```

## 7. Verify Setup

```bash
# Check if credentials are found
otomata config

# List files (requires shared access)
otomata google drive-list

# List accessible Shared Drives
otomata google drive-list --query "mimeType='application/vnd.google-apps.folder'"
```

## Troubleshooting

| Error | Cause | Solution |
|-------|-------|----------|
| `credentials not found` | JSON not configured | Check `.env.local` or env var |
| `403 Forbidden` | No access to resource | Share the file/folder with service account email |
| `404 Not Found` | Invalid file ID | Verify the ID exists and is shared |
| `API not enabled` | API disabled in GCP | Enable the API in Google Cloud Console |

## Team-Scoped Access (Shared Drive Only)

To create a service account that **only** has access to a specific Shared Drive (e.g., for a team or project):

1. **Create a dedicated GCP project** for the team (e.g., `321founded-ekinox`)
2. **Create the service account** in that project (e.g., `memento-ekinox@321founded-ekinox.iam.gserviceaccount.com`)
3. **Share only the target Shared Drive** with the service account email
4. **Do NOT share** any personal drives, folders, or other resources

The service account will only see files in the Shared Drive it was invited to. This provides natural isolation without any additional configuration.

**Example use case:**
- Team: Ekinox
- GCP Project: `321founded-ekinox`
- Service Account: `memento-ekinox@321founded-ekinox.iam.gserviceaccount.com`
- Access: Only "Ekinox" Shared Drive (shared as Content Manager)

Team members share the same `.env.local` with this service account, ensuring everyone has identical (and limited) access.

## Security Notes

- Never commit the JSON key to git (add `*.json` to `.gitignore`)
- Rotate keys periodically in Google Cloud Console
- Use minimal permissions (Viewer if read-only access is sufficient)
- For production, consider using Workload Identity Federation instead of JSON keys
