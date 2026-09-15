# oto-cli

**Façade CLI d'Oto** — commandes Typer `oto <cmd>` au-dessus de la lib **oto-core**. Repo public
`otomata-tech/oto-cli`, commande `oto`. Tout est open source.

⚠️ **La CLI n'est pas le produit principal.** Le produit central est **oto-backend** (serveur MCP déployable
SaaS/on-premise). La CLI est **basse priorité**, surtout utile comme **fallback local pour LinkedIn browser**
(qui ne marche qu'en local).

## Philosophie

- **Façade mince** : les clients vivent dans **oto-core** ; ici il n'y a que `oto/cli.py` (discovery) et
  `oto/commands/` — **1 fichier = 1 sous-commande Typer**, auto-découverte. `ls oto/commands/` donne la liste ;
  `oto --help` et `oto <cmd> --help` font foi.
- **Pour des agents IA** : JSON sur stdout, erreurs sur stderr, composable au pipe.
- **Local-first** : exécution locale, secrets résolus localement. Pour le serveur, le multi-utilisateur et le
  chiffrement, c'est oto-backend.

## Stack

Python 3.10+, Typer, setuptools (namespace package `oto`, ex-hatchling). Dépend d'**oto-core** (`oto.tools` +
`oto.config`) + typer. Extras re-exportés d'oto-core : `google`, `browser`, `vivatech`, `anthropic`, `stock`, `all`.

⚠️ **Namespace partagé** : oto-core fournit `oto.tools`/`oto.config`, oto-cli fournit `oto.cli`/`oto.commands`, et les
deux cohabitent dans le même paquet `oto`. Changer le pyproject de l'un ⇒ **réinstaller editable** les deux.

## Écrire une commande

```python
app = typer.Typer(help="My service description")     # exporté, auto-découvert par cli.py

@app.command("do-thing")
def do_thing(query: str = typer.Argument(...), max_results: int = typer.Option(20, "-n")):
    from oto.tools.myservice.client import MyServiceClient   # import DANS la fonction
    print(json.dumps(MyServiceClient().do_thing(query=query, max_results=max_results), indent=2))
```

- **Imports d'outils à l'intérieur des fonctions** (lazy) : c'est ce qui garde la CLI rapide au démarrage.
  ⚠️ Corollaire : le smoke `--help` du CI ne les exerce **jamais** — une commande peut rester cassée en silence.
- Toujours `print(json.dumps(..., indent=2))`. Un secret manquant lève `ValueError`, rattrapé par `main()` qui en
  fait un message propre sur stderr.

**Ajouter un connecteur = 2 fichiers dans 2 repos** : le **client** dans `oto/tools/<svc>/` d'**oto-core**, la
**commande** dans `oto/commands/<svc>.py` ici. (Côté serveur, le wrapper vit dans oto-backend et importe le même
client.) ⚠️ Connecteur **client-sensible** (back-office propre d'un client, son infra, ses accès) → **jamais dans ces
repos publics** : package privé + bridge (ADR 0003). Détail : `docs/create-connector.md`.

## Secrets & config

Résolution par provider (`oto config provider secrets <sops|file|scaleway>`) :

1. **Variables d'env** — toujours, priorité haute.
2. **Le provider configuré** — défaut **`sops`** (SOPS+age, `~/.otomata/secrets/`), sinon `file`
   (`.otomata/secrets.env`, projet puis user) ou `scaleway` (Secret Manager).
3. Repli fichier local quand le magasin du provider est absent, puis la valeur par défaut.

⚠️ **`sops` reste le défaut du CODE** (`oto.config.get_provider()`), alors que **SOPS est déprécié comme coffre** :
lecture seule, aucune écriture nouvelle — le coffre de référence est 1Password, et le boot serveur lit Scaleway. Les
deux affirmations sont vraies en même temps : la doctrine 1P n'est pas encore branchée dans `oto` (un provider reste à
écrire). Voir `/data/infra/docs/secrets.md`.

⚠️ **Mode serveur** : `OTO_CONFIG_DISABLE_SOPS=1` ⇒ `get_secret` ne résout **que** l'env du process (ni SOPS ni
`secrets.env`) et `require_secret` échoue fort. Posé par l'unit d'oto-backend : ses credentials vivent dans son coffre
DB et sont **injectés** dans les clients — jamais d'auto-résolution.

```bash
oto config                        # providers + état des secrets
oto config provider secrets sops  # bascule de provider
oto config provider search serper # serper (défaut) ou browser
oto config secrets-push/-pull     # secrets.env local ↔ Scaleway
```

**Google OAuth** : jetons dans `~/.otomata/google-oauth-token-{name}.json`. Ajouter un compte =
`oto google auth <name>` (ouvre le navigateur) ; lister = `oto google auth --list`.

## Déploiement & release

**Un push sur `main` ne déploie rien sur un serveur**, et il ne faut pas le rétablir : l'ancien `deploy.yml`
réinstallait oto-cli dans le venv de la prod puis redémarrait `oto-mcp` — depuis le bleu/vert du backend, ce nom
désigne l'unité simple d'avant, désactivée, que chaque push réveillait sur un port déjà tenu, en boucle de crash.

oto-backend importe ses clients depuis **oto-core**, pas depuis oto-cli : un changement de *client* passe par oto-core,
un changement de *commande* n'a rien à déployer. La CLI se distribue par PyPI, à la main → `docs/release.md`.

## Claude Code

La CLI ne ship plus de skills. Le guidage agent vit dans le **plugin `oto`** (`otomata-tech/oto-plugin`) : un skill
universel (doctrine d'amorçage + « découvre via `oto --help` ») + le connecteur MCP auto-configuré. Les doctrines non
évidentes par outil vont dans les **help strings** des commandes, pas dans un skill.

## Docs

`concepts.md` (architecture, types de connecteurs, secrets, contrat de sortie) · `create-connector.md` ·
`installation.md` · `release.md` · `gmail-oauth-setup.md` · `gmail.md` · `google-docs.md` ·
`google-service-account-setup.md` · `zoho-desk-oauth-setup.md`
