"""Configuration and secrets management."""

import typer

app = typer.Typer(help="Configuration and secrets management")


TRACKED_SECRETS = [
    "GOOGLE_SERVICE_ACCOUNT",
    "GOOGLE_OAUTH_CLIENT",
    "NOTION_API_KEY",
    "LINKEDIN_COOKIE",
    "SIRENE_API_KEY",
    "SERPER_API_KEY",
    "KASPR_API_KEY",
    "HUNTER_API_KEY",
    "LEMLIST_API_KEY",
    "PENNYLANE_API_KEY",
    "GROQ_API_KEY",
    "ANTHROPIC_ADMIN_API_KEY",
    "FOLK_API_KEY",
    "ATTIO_API_KEY",
    "TULS_API_TOKEN",
    "OTO_API_KEY",
]


@app.callback(invoke_without_command=True)
def show(ctx: typer.Context):
    """Show current configuration and detected secrets."""
    if ctx.invoked_subcommand is not None:
        return

    # ⚠️ Ces deux helpers ont déménagé dans oto.secrets.file au split oto-core
    # (2026-06-11) ; les importer depuis oto.config faisait planter `oto config`
    # (ImportError) pour QUICONQUE, quel que soit le provider — pas seulement
    # 'sops' (oto-core#63).
    from oto.config import get_secret, get_provider, get_search_provider
    from oto.secrets.file import _find_project_secrets, _user_secrets

    provider = get_provider()
    search_provider = get_search_provider()
    print(f"Secret provider: {provider}")
    print(f"Search provider: {search_provider}")
    print()

    if provider == "file":
        project_secrets = _find_project_secrets()
        user_secrets = _user_secrets()
        print("Secrets files:")
        print(f"  Project: {project_secrets or '.otomata/secrets.env (not found)'}")
        print(f"  User:    {user_secrets}{' (exists)' if user_secrets.exists() else ' (not found)'}")
    elif provider == "sops":
        from oto.secrets.sops import _autodetect_dir
        root = _autodetect_dir()
        print(f"Source: SOPS store ({root if root else '~/.otomata/secrets/ (not found)'})")
    else:
        print("Source: Scaleway Secret Manager (otomata-secrets)")

    print()
    print("Secrets status:")
    for name in TRACKED_SECRETS:
        status = "+" if get_secret(name) else "-"
        print(f"  {status} {name}")


provider_app = typer.Typer(help="Manage providers (secrets, search)")
app.add_typer(provider_app, name="provider")


@provider_app.command("secrets")
def provider_secrets(
    provider: str = typer.Argument(..., help="Provider: 'sops', 'file', or 'scaleway'"),
):
    """Switch secret provider.

    'sops' is oto.config.get_provider()'s own default — refusing it here left
    require_secret's error message recommend a value this setter rejected
    (oto-core#63).
    """
    if provider not in ("sops", "file", "scaleway"):
        raise typer.BadParameter("Must be 'sops', 'file', or 'scaleway'")

    if provider == "scaleway":
        from oto.secrets.scaleway import _load_scw_credentials
        _load_scw_credentials()

    from oto.config import _get_oto_config, write_oto_config
    config = _get_oto_config().copy()
    config["secret_provider"] = provider
    write_oto_config(config)
    print(f"Secret provider set to: {provider}")


@provider_app.command("search")
def provider_search(
    provider: str = typer.Argument(..., help="Provider: 'serper' or 'browser'"),
):
    """Switch search provider."""
    if provider not in ("serper", "browser"):
        raise typer.BadParameter("Must be 'serper' or 'browser'")

    from oto.config import _get_oto_config, write_oto_config
    config = _get_oto_config().copy()
    config["search_provider"] = provider
    write_oto_config(config)
    print(f"Search provider set to: {provider}")


@app.command("secrets-push")
def secrets_push():
    """Upload local secrets.env to Scaleway Secret Manager."""
    from oto.secrets.file import _user_secrets as _get_user_secrets, _parse_env_file
    from oto.secrets.scaleway import push_secrets

    secrets_file = _get_user_secrets()
    if not secrets_file.exists():
        print(f"No secrets file at {secrets_file}")
        raise typer.Exit(1)

    secrets = _parse_env_file(secrets_file)
    if not secrets:
        print("No secrets found in file")
        raise typer.Exit(1)

    print(f"Pushing {len(secrets)} secrets to Scaleway...")
    typer.confirm("Continue?", abort=True)

    revision = push_secrets(secrets)
    print(f"Pushed {len(secrets)} secrets (revision {revision})")


@app.command("secrets-pull")
def secrets_pull():
    """Download secrets from Scaleway to local secrets.env."""
    from oto.secrets.file import _user_secrets as _get_user_secrets
    from oto.secrets.scaleway import fetch_secrets

    secrets = fetch_secrets()
    if not secrets:
        print("No secrets found in Scaleway")
        raise typer.Exit(1)

    secrets_file = _get_user_secrets()
    print(f"Pulling {len(secrets)} secrets to {secrets_file}")
    typer.confirm("This will overwrite the local file. Continue?", abort=True)

    with open(secrets_file, "w") as f:
        for key, value in sorted(secrets.items()):
            f.write(f"{key}={value}\n")

    secrets_file.chmod(0o600)
    print(f"Wrote {len(secrets)} secrets to {secrets_file}")
